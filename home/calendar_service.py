import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    """Service for Google Calendar integration"""
    
    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.service = self._get_calendar_service()
    
    def _get_calendar_service(self):
        """Initialize Google Calendar API service"""
        try:
            # Get credentials from environment variable (JSON string) or file
            if hasattr(settings, 'GOOGLE_SERVICE_ACCOUNT_KEY'):
                # For production (Render) - JSON as string in environment variable
                credentials_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_KEY)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
            else:
                # For development - JSON file
                credentials_path = os.path.join(settings.BASE_DIR, 'google_credentials.json')
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
            
            service = build('calendar', 'v3', credentials=credentials)
            return service
            
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {str(e)}")
            return None
    
    def create_group_walk_event(self, booking):
        """Create calendar event for group walk booking"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None
        
        try:
            # Parse time slot
            time_slot = booking.time_slot
            if time_slot == '11:00-12:00':
                start_time = '11:00:00'
                end_time = '12:00:00'
            elif time_slot == '15:00-16:00':
                start_time = '15:00:00'
                end_time = '16:00:00'
            else:
                logger.error(f"Unknown time slot: {time_slot}")
                return None
            
            # Create datetime objects
            start_datetime = datetime.combine(booking.booking_date, datetime.strptime(start_time, '%H:%M:%S').time())
            end_datetime = datetime.combine(booking.booking_date, datetime.strptime(end_time, '%H:%M:%S').time())
            
            # Convert to timezone-aware datetimes
            uk_timezone = timezone.get_current_timezone()
            start_datetime = uk_timezone.localize(start_datetime)
            end_datetime = uk_timezone.localize(end_datetime)
            
            # Get dog names
            dog_names = [dog.name for dog in booking.dogs.all()]
            
            # Create event
            event = {
                'summary': f'Group Walk - {booking.customer_name}',
                'description': f'''
Group Walk Booking Details:

Customer: {booking.customer_name}
Phone: {booking.customer_phone}
Email: {booking.customer_email}
Address: {booking.customer_address}
Postcode: {booking.customer_postcode}

Dogs: {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})

Booking ID: {booking.id}
Status: {booking.get_status_display()}
                '''.strip(),
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
                'colorId': '2',  # Green color for group walks
            }
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"Created group walk calendar event: {created_event['id']}")
            return created_event['id']
            
        except Exception as e:
            logger.error(f"Error creating group walk calendar event: {str(e)}")
            return None
    
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
            # Parse the confirmed time (this will vary based on how it's formatted)
            confirmed_date = booking.confirmed_date
            confirmed_time = booking.confirmed_time
            
            # Create start datetime (defaulting to 9 AM if time parsing fails)
            try:
                # Try to extract time from confirmed_time string
                if ':' in confirmed_time:
                    # Extract first time found (e.g., "8:00 AM - 9:00 AM" -> "8:00")
                    time_part = confirmed_time.split('-')[0].strip()
                    if 'AM' in time_part.upper() or 'PM' in time_part.upper():
                        # Parse 12-hour format
                        start_time = datetime.strptime(time_part, '%I:%M %p').time()
                    else:
                        # Parse 24-hour format
                        start_time = datetime.strptime(time_part, '%H:%M').time()
                else:
                    # Default to 9 AM if no specific time
                    start_time = datetime.strptime('09:00', '%H:%M').time()
            except:
                # Fallback to 9 AM
                start_time = datetime.strptime('09:00', '%H:%M').time()
            
            start_datetime = datetime.combine(confirmed_date, start_time)
            end_datetime = start_datetime + timedelta(hours=1)  # 1 hour walk
            
            # Convert to timezone-aware datetimes
            uk_timezone = timezone.get_current_timezone()
            start_datetime = uk_timezone.localize(start_datetime)
            end_datetime = uk_timezone.localize(end_datetime)
            
            # Get dog names
            dog_names = [dog.name for dog in booking.dogs.all()]
            
            # Create event
            event = {
                'summary': f'Individual Walk - {booking.customer_name}',
                'description': f'''
Individual Walk Details:

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
Status: {booking.get_status_display()}
                '''.strip(),
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
            ).execute()
            
            logger.info(f"Created individual walk calendar event: {created_event['id']}")
            return created_event['id']
            
        except Exception as e:
            logger.error(f"Error creating individual walk calendar event: {str(e)}")
            return None
    
    def update_event(self, event_id, booking):
        """Update existing calendar event"""
        if not self.service:
            return None
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update event details based on booking type
            if hasattr(booking, 'time_slot'):  # Group walk
                dog_names = [dog.name for dog in booking.dogs.all()]
                event['summary'] = f'Group Walk - {booking.customer_name}'
                event['description'] = f'''
Group Walk Booking Details:

Customer: {booking.customer_name}
Phone: {booking.customer_phone}
Email: {booking.customer_email}
Address: {booking.customer_address}
Postcode: {booking.customer_postcode}

Dogs: {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})

Booking ID: {booking.id}
Status: {booking.get_status_display()}
                '''.strip()
            
            # Update the event
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
        """Delete calendar event"""
        if not self.service:
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Deleted calendar event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting calendar event {event_id}: {str(e)}")
            return False