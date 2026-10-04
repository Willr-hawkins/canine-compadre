import os
import time
import logging
import threading
import zoneinfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import httplib2
import google_auth_httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings

logger = logging.getLogger(__name__)

LONDON_TZ = zoneinfo.ZoneInfo('Europe/London')

# Google takes ~1s to process each calendar write, and batch requests are
# processed one after another on Google's side — so we send calls in parallel
# instead. 10 at once turns 50 events from ~50s into ~5s.
MAX_PARALLEL_CALLS = 10

# Per-request socket timeout, so one hung Google call can't hold a worker
# until gunicorn kills it.
HTTP_TIMEOUT_SECONDS = 15

# Render mounts secret files at /etc/secrets/. Locally, point
# GOOGLE_CREDENTIALS_PATH at your own copy of the service-account JSON.
DEFAULT_CREDENTIALS_PATH = '/etc/secrets/google_credentials.json'

SCOPES = ['https://www.googleapis.com/auth/calendar']

GROUP_WALK_TIMES = {
    '09:30-11:30': ('09:30', '11:30'),
    '14:00-16:00': ('14:00', '16:00'),
    '18:00-20:00': ('18:00', '20:00'),
}


class GoogleCalendarService:
    """Service for Google Calendar integration"""

    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self._local = threading.local()
        self._credentials = self._load_credentials()
        self.service = self._get_calendar_service()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_credentials(self):
        credentials_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', DEFAULT_CREDENTIALS_PATH)
        if not os.path.exists(credentials_path):
            logger.error(f"Google credentials file not found at: {credentials_path}")
            return None
        try:
            return service_account.Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
        except Exception as e:
            logger.error(f"Error loading Google credentials: {str(e)}")
            return None

    def _build_service(self):
        """Build a Calendar client with its own HTTP connection (httplib2 isn't thread-safe)."""
        authed_http = google_auth_httplib2.AuthorizedHttp(
            self._credentials,
            http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS),
        )
        return build('calendar', 'v3', http=authed_http, cache_discovery=False)

    def _get_calendar_service(self):
        if not self._credentials:
            return None
        try:
            service = self._build_service()
            logger.info("Google Calendar service initialized successfully")
            return service
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {str(e)}")
            return None

    def _thread_service(self):
        """One Calendar client per worker thread."""
        service = getattr(self._local, 'service', None)
        if service is None:
            service = self._build_service()
            self._local.service = service
        return service

    def _ensure_fresh_token(self):
        """Refresh the access token once up front, so parallel threads don't all refresh at once."""
        if not self._credentials.valid:
            self._credentials.refresh(
                google_auth_httplib2.Request(httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS))
            )

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

    def _insert_event(self, body):
        """Runs in a worker thread. Touches only Google, never the database."""
        created = self._thread_service().events().insert(
            calendarId=self.calendar_id,
            body=body,
        ).execute(num_retries=1)
        return created['id']

    def create_group_walk_events_batch(self, bookings):
        """
        Create calendar events for many group walk bookings, several at a time in parallel.
        Returns {booking_id: event_id} for every event that was created.
        Bookings that fail are logged and left without an event ID.
        """
        results = {}
        if not bookings:
            return results
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return results

        # Build every event body here in the main thread (reads dogs from the DB),
        # so the worker threads only ever talk to Google.
        bodies = {}
        for booking in bookings:
            body = self._build_group_walk_event(booking)
            if body:
                bodies[booking.id] = body
        if not bodies:
            return results

        try:
            self._ensure_fresh_token()
        except Exception as e:
            logger.error(f"Could not refresh Google credentials: {str(e)}")
            return results

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CALLS, len(bodies))) as pool:
            futures = {
                pool.submit(self._insert_event, body): booking_id
                for booking_id, body in bodies.items()
            }
            for future in as_completed(futures):
                booking_id = futures[future]
                try:
                    results[booking_id] = future.result()
                except Exception as e:
                    logger.error(f"Calendar event failed for booking {booking_id}: {str(e)}")

        logger.info(
            f"Created {len(results)}/{len(bodies)} group walk calendar events "
            f"in {time.monotonic() - start:.1f}s"
        )
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

    def _delete_one(self, event_id):
        """Runs in a worker thread. Returns True if the event is now gone."""
        try:
            self._thread_service().events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute(num_retries=1)
            return True
        except HttpError as e:
            if e.resp.status in (404, 410):
                return True
            raise

    def delete_events_batch(self, event_ids):
        """
        Delete many calendar events, several at a time in parallel.
        Returns the set of event IDs that are now gone (deleted, or already missing).
        """
        deleted = set()
        event_ids = list({e for e in event_ids if e})
        if not event_ids:
            return deleted
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return deleted

        try:
            self._ensure_fresh_token()
        except Exception as e:
            logger.error(f"Could not refresh Google credentials: {str(e)}")
            return deleted

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CALLS, len(event_ids))) as pool:
            futures = {pool.submit(self._delete_one, event_id): event_id for event_id in event_ids}
            for future in as_completed(futures):
                event_id = futures[future]
                try:
                    if future.result():
                        deleted.add(event_id)
                except Exception as e:
                    logger.warning(f"Delete failed for calendar event {event_id}: {str(e)}")

        logger.info(
            f"Deleted {len(deleted)}/{len(event_ids)} calendar events "
            f"in {time.monotonic() - start:.1f}s"
        )
        return deleted