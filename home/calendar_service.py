import os
import logging
import zoneinfo
from datetime import datetime, timedelta

import httplib2
import google_auth_httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings

logger = logging.getLogger(__name__)

LONDON_TZ = zoneinfo.ZoneInfo('Europe/London')

# Google allows up to 50 calls per batch; smaller chunks are kinder to the
# Calendar API's per-second rate limits.
BATCH_SIZE = 25

# Per-request socket timeout, so one hung Google call can't hold a gunicorn
# worker until it gets killed.
HTTP_TIMEOUT_SECONDS = 20

# If more than this many calls fail inside a batch, don't retry them one by one
# (Google is probably having a bad moment) — log them and leave them for backfill.
MAX_INDIVIDUAL_RETRIES = 10

GROUP_WALK_TIMES = {
    '09:30-11:30': ('09:30', '11:30'),
    '14:00-16:00': ('14:00', '16:00'),
    '18:00-20:00': ('18:00', '20:00'),
}


class GoogleCalendarService:
    """Service for Google Calendar integration"""

    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.service = self._get_calendar_service()

    def _get_calendar_service(self):
        try:
            # Render secret files are mounted at /etc/secrets/
            credentials_path = '/etc/secrets/google_credentials.json'

            if not os.path.exists(credentials_path):
                logger.error(f"Google credentials file not found at: {credentials_path}")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            authed_http = google_auth_httplib2.AuthorizedHttp(
                credentials,
                http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS),
            )
            service = build('calendar', 'v3', http=authed_http, cache_discovery=False)
            logger.info("Google Calendar service initialized successfully")
            return service

        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {str(e)}")
            return None

    # ------------------------------------------------------------------
    # Group walks
    # ------------------------------------------------------------------

    def _build_group_walk_event(self, booking):
        """Build the event body for a group walk booking. Returns None if the slot is unknown."""
        times = GROUP_WALK_TIMES.get(booking.time_slot)
        if not times:
            logger.error(f"Unknown time slot for booking {booking.id}: {booking.time_slot}")
            return None

        start_time, end_time = times
        start_datetime = datetime.combine(
            booking.booking_date, datetime.strptime(start_time, '%H:%M').time()
        ).replace(tzinfo=LONDON_TZ)
        end_datetime = datetime.combine(
            booking.booking_date, datetime.strptime(end_time, '%H:%M').time()
        ).replace(tzinfo=LONDON_TZ)

        dog_names = [dog.name for dog in booking.dogs.all()]

        return {
            'summary': f'Group Walk - {booking.customer_name}',
            'description': f'''Group Walk Booking Details:

Customer: {booking.customer_name}
Phone: {booking.customer_phone}
Email: {booking.customer_email}
Address: {booking.customer_address}
Postcode: {booking.customer_postcode}

Dogs: {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})

Booking ID: {booking.id}
Status: {booking.get_status_display()}''',
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Europe/London',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Europe/London',
            },
            'location': f'{booking.customer_address}, {booking.customer_postcode}',
            # Note: Service accounts cannot invite attendees without Domain-Wide Delegation
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                    {'method': 'popup', 'minutes': 30},       # 30 minutes before
                ],
            },
            'colorId': '2',  # Green color for group walks
        }

    def create_group_walk_event(self, booking):
        """Create a calendar event for a single group walk booking"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None

        try:
            body = self._build_group_walk_event(booking)
            if not body:
                return None

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=body
            ).execute(num_retries=2)

            logger.info(f"Created group walk calendar event: {created_event['id']}")
            return created_event['id']

        except Exception as e:
            logger.error(f"Error creating group walk calendar event: {str(e)}")
            return None

    def create_group_walk_events_batch(self, bookings):
        """
        Create calendar events for many group walk bookings using batched requests.
        Returns {booking_id: event_id} for every event that was created.
        Bookings that fail are logged and left without an event ID.
        """
        results = {}
        if not bookings:
            return results
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return results

        bodies = {}
        for booking in bookings:
            body = self._build_group_walk_event(booking)
            if body:
                bodies[booking.id] = body

        failed = []

        def callback(request_id, response, exception):
            booking_id = int(request_id)
            if exception is not None:
                logger.warning(f"Batch insert failed for booking {booking_id}: {exception}")
                failed.append(booking_id)
            else:
                results[booking_id] = response['id']

        booking_ids = list(bodies)
        for i in range(0, len(booking_ids), BATCH_SIZE):
            chunk = booking_ids[i:i + BATCH_SIZE]
            batch = self.service.new_batch_http_request(callback=callback)
            for booking_id in chunk:
                batch.add(
                    self.service.events().insert(
                        calendarId=self.calendar_id,
                        body=bodies[booking_id],
                    ),
                    request_id=str(booking_id),
                )
            try:
                batch.execute()
            except Exception as e:
                logger.error(f"Calendar batch request failed: {str(e)}")
                failed.extend(
                    b for b in chunk if b not in results and b not in failed
                )

        # Retry stragglers individually (with Google's built-in backoff for rate limits)
        if failed and len(failed) <= MAX_INDIVIDUAL_RETRIES:
            for booking_id in failed:
                try:
                    created = self.service.events().insert(
                        calendarId=self.calendar_id,
                        body=bodies[booking_id],
                    ).execute(num_retries=2)
                    results[booking_id] = created['id']
                except Exception as e:
                    logger.error(f"Retry failed creating calendar event for booking {booking_id}: {str(e)}")
        elif failed:
            logger.error(
                f"{len(failed)} calendar events failed in batch; not retrying individually. "
                f"Booking IDs: {failed}"
            )

        logger.info(f"Created {len(results)}/{len(bodies)} group walk calendar events")
        return results

    # ------------------------------------------------------------------
    # Individual walks
    # ------------------------------------------------------------------

    def create_individual_walk_event(self, booking):
        """Create calendar event for approved individual walk"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None

        if booking.status != 'approved' or not booking.confirmed_date or not booking.confirmed_time:
            logger.warning(f"Individual walk booking {booking.id} not ready for calendar event")
            return None

        try:
            # For individual walks, we'll create a 1-hour slot
            confirmed_date = booking.confirmed_date
            confirmed_time = booking.confirmed_time

            # Create start datetime (defaulting to 9 AM if time parsing fails)
            try:
                if ':' in confirmed_time:
                    # Extract first time found (e.g., "8:00 AM - 9:00 AM" -> "8:00")
                    time_part = confirmed_time.split('-')[0].strip()
                    if 'AM' in time_part.upper() or 'PM' in time_part.upper():
                        start_time = datetime.strptime(time_part, '%I:%M %p').time()
                    else:
                        start_time = datetime.strptime(time_part, '%H:%M').time()
                else:
                    start_time = datetime.strptime('09:00', '%H:%M').time()
            except Exception:
                start_time = datetime.strptime('09:00', '%H:%M').time()

            start_datetime = datetime.combine(confirmed_date, start_time).replace(tzinfo=LONDON_TZ)
            end_datetime = start_datetime + timedelta(hours=1)  # 1 hour walk

            dog_names = [dog.name for dog in booking.dogs.all()]

            event = {
                'summary': f'Individual Walk - {booking.customer_name}',
                'description': f'''Individual Walk Details:

Customer: {booking.customer_name}
Phone: {booking.customer_phone}
Email: {booking.customer_email}
Address: {booking.customer_address}
Postcode: {booking.customer_postcode}

Dogs: {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})

Reason for Individual Walk:
{booking.reason_for_individual}

Preferred Time: {booking.preferred_time}
Confirmed Time: {booking.confirmed_time}

Booking ID: {booking.id}
Status: {booking.get_status_display()}''',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/London',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/London',
                },
                'location': f'{booking.customer_address}, {booking.customer_postcode}',
                'attendees': [
                    {'email': booking.customer_email, 'displayName': booking.customer_name}
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                        {'method': 'popup', 'minutes': 30},       # 30 minutes before
                    ],
                },
                'colorId': '1',  # Blue color for individual walks
            }

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute(num_retries=2)

            logger.info(f"Created individual walk calendar event: {created_event['id']}")
            return created_event['id']

        except Exception as e:
            logger.error(f"Error creating individual walk calendar event: {str(e)}")
            return None

    # ------------------------------------------------------------------
    # Update / delete
    # ------------------------------------------------------------------

    def update_event(self, event_id, booking):
        """Update existing calendar event"""
        if not self.service:
            return None

        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            if hasattr(booking, 'time_slot'):  # Group walk
                dog_names = [dog.name for dog in booking.dogs.all()]
                event['summary'] = f'Group Walk - {booking.customer_name}'
                event['description'] = f'''Group Walk Booking Details:

Customer: {booking.customer_name}
Phone: {booking.customer_phone}
Email: {booking.customer_email}
Address: {booking.customer_address}
Postcode: {booking.customer_postcode}

Dogs: {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})

Booking ID: {booking.id}
Status: {booking.get_status_display()}'''

            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Updated calendar event: {event_id}")
            return updated_event['id']

        except Exception as e:
            logger.error(f"Error updating calendar event {event_id}: {str(e)}")
            return None

    def delete_event(self, event_id):
        """Delete a single calendar event. An event that's already gone counts as deleted."""
        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute(num_retries=2)

            logger.info(f"Deleted calendar event: {event_id}")
            return True

        except HttpError as e:
            if e.resp.status in (404, 410):
                logger.info(f"Calendar event {event_id} was already deleted")
                return True
            logger.error(f"Error deleting calendar event {event_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting calendar event {event_id}: {str(e)}")
            return False

    def delete_events_batch(self, event_ids):
        """
        Delete many calendar events using batched requests.
        Returns the set of event IDs that are now gone (deleted, or already missing).
        """
        deleted = set()
        event_ids = list({e for e in event_ids if e})
        if not event_ids:
            return deleted
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return deleted

        def callback(request_id, response, exception):
            if exception is None:
                deleted.add(request_id)
            elif isinstance(exception, HttpError) and exception.resp.status in (404, 410):
                deleted.add(request_id)
            else:
                logger.warning(f"Batch delete failed for event {request_id}: {exception}")

        for i in range(0, len(event_ids), BATCH_SIZE):
            batch = self.service.new_batch_http_request(callback=callback)
            for event_id in event_ids[i:i + BATCH_SIZE]:
                batch.add(
                    self.service.events().delete(calendarId=self.calendar_id, eventId=event_id),
                    request_id=event_id,
                )
            try:
                batch.execute()
            except Exception as e:
                logger.error(f"Calendar batch delete failed: {str(e)}")

        logger.info(f"Deleted {len(deleted)}/{len(event_ids)} calendar events")
        return deleted