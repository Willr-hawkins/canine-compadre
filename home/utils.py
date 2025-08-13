"""
Utility functions for Canine Compadre booking system
"""

import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import GroupWalk

logger = logging.getLogger(__name__)

def cancel_bookings_for_unavailable_slots(date, cancelled_time_slots, reason="Date marked unavailable"):
    """
    Cancel all existing bookings for specific time slots on a given date
    and send notification emails to customers.
    
    Args:
        date: The date to cancel bookings for
        cancelled_time_slots: List of time slots to cancel (e.g., ['10:00-12:00', '14:00-16:00'])
        reason: Reason for cancellation to include in emails
    
    Returns:
        int: Number of bookings cancelled
    """

    # Find all confirmed bookings for the specified date and time slots
    bookings_to_cancel = GroupWalk.objects.filter(
        booking_date=date,
        time_slot__in=cancelled_time_slots,
        status='confirmed'
    )

    cancelled_count = 0

    for booking in bookings_to_cancel:
        try:
            # Cancel the booking
            booking.status = 'cancelled'
            booking.save()

            # Delete calendar event if it exists
            if booking.calendar_event_id:
                try:
                    booking.delete_calendar_event()
                except Exception as e:
                    logger.error(f"Failed to delete calendar even for booking {booking.id}: {str(e)}")
            
            # Send cancellation email to customer
            send_cancellation_email(booking, reason)

            cancelled_count += 1
            logger.info(f"Cancelled booking {booking.id} for {booking.cusomter_name} on {date}")

        except Exception as e:
            logger.error(f"Error cancelling booking {booking.id}: {str(e)}")

    return cancelled_count

def send_cancellation_email(booking, reason):
    """
    Send a professional cancellation email to the customer
    
    Args:
        booking: The GroupWalk booking that was cancelled
        reason: Reason for cancellation
    """

    try:
        # Prepare email context
        context = {
            'booking': booking,
            'reason': reason,
            'business_email': settings.BUSINESS_EMAIL,
            'site_url': settings.SITE_URL,
            'dog_names': ', '.join([dog.name for dog in booking.dogs.all()]),
        }

        # Email subject
        subject = f"Important: Your Group Walk Booking on {booking.booking_date.strftime('%B %d %Y')} has been Cancelled"

        # Email content
        message = f"""Dear {booking.customer_name},

We sincerely apologize, but we need to cancel your group walk booking due to unforeseen circumstances.

CANCELLED BOOKING DETAILS:
• Date: {booking.booking_date.strftime('%A, %B %d, %Y')}
• Time: {booking.get_time_slot_display()}
• Dogs: {context['dog_names']} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
• Booking ID: #{booking.id}

REASON FOR CANCELLATION:
{reason}

We understand this is inconvenient and apologize for any disruption to your plans. To make this right, we'd like to offer you priority booking for an alternative date.

NEXT STEPS:
1. Visit our website to see available dates: {context['site_url']}
2. Contact us directly at {context['business_email']} if you need assistance rebooking
3. We'll ensure you get priority for your preferred alternative date

Thank you for your understanding, and we look forward to providing excellent care for {context['dog_names']} on a rescheduled date.

Best regards,
Alex
Canine Compadre
{context['business_email']}

---
This is an automated message. If you have any questions, please contact us directly.
        """

        # Send the eamil
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.customer_email],
            fail_silently=False,
        )

        logger.info(f"Cancellation email sent to {booking.customer_email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send cancellation email for booking {booking.id}: {str(e)}")
        return False

def get_alternative_dates(cancelled_date, num_dogs=1, days_ahead=14):
    """
    Get suggested alternative dates for rebooking
    
    Args:
        cancelled_date: The date that was cancelled
        num_dogs: Number of dogs to accommodate
        days_ahead: How many days ahead to look for alternatives
    
    Returns:
        list: Available alternative slots
    """
    
    from datetime import timedelta
    from .models import GroupWalk
    
    # Get available slots starting from the day after cancellation
    start_date = max(cancelled_date + timedelta(days=1), date.today() + timedelta(days=1))
    
    try:
        alternative_slots = GroupWalk.get_available_slots(
            days_ahead=days_ahead, 
            required_dogs=num_dogs
        )
        
        # Filter to only show dates after the cancelled date
        filtered_slots = [
            slot for slot in alternative_slots 
            if slot['date'] >= start_date
        ]
        
        return filtered_slots[:5]  # Return top 5 alternatives
        
    except Exception as e:
        logger.error(f"Error getting alternative dates: {str(e)}")
        return []
