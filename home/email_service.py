from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import time

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending booking confirmation and notification emails"""

    @staticmethod
    def send_email_with_retry(subject, message, from_email, recipient_list, html_content=None, max_retries=3):
        """Send email with retry logic for better reliability"""
        for attempt in range(max_retries):
            try:
                if html_content:
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=message,
                        from_email=from_email,
                        to=recipient_list,
                        reply_to=[from_email]
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                else:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=from_email,
                        recipient_list=recipient_list,
                        fail_silently=False
                    )

                logger.info(f"Email sent successfully on attempt {attempt + 1}")
                return True

            except Exception as e:
                logger.warning(f"Email sending attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                else:
                    logger.error(f"Email sending failed after {max_retries} attempts: {str(e)}")
                    return False

        return False

    @staticmethod
    def send_group_walk_confirmation(booking):
        """Send confirmation email to customer for group walk booking"""
        try:
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)

            subject = f'Group Walk Confirmed - {booking.booking_date.strftime("%B %d, %Y")}'

            context = {
                'booking': booking,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
                'confirmation_url': f"{settings.SITE_URL}/booking-confirmation/{booking.id}/group/",
            }

            try:
                html_content = render_to_string('emails/group_walk_confirmation.html', context)
                text_content = strip_tags(html_content)
            except Exception:
                html_content = None
                text_content = EmailService._create_group_walk_text_email(booking, dog_names)

            EmailService.send_email_with_retry(
                subject,
                text_content,
                settings.BUSINESS_EMAIL,
                [booking.customer_email],
                html_content=html_content
            )

            logger.info(f"Group walk confirmation email sent to {booking.customer_email} for booking {booking.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending group walk confirmation email for booking {booking.id}: {str(e)}")
            return False

    @staticmethod
    def send_individual_walk_request_confirmation(booking):
        """Send confirmation email to customer for individual walk request submission"""
        try:
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)

            subject = f'Individual Walk Request Received - #{booking.id}'

            context = {
                'booking': booking,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
            }

            try:
                html_content = render_to_string('emails/individual_walk_request_confirmation.html', context)
                text_content = strip_tags(html_content)
            except Exception:
                html_content = None
                text_content = EmailService._create_individual_walk_request_text_email(booking, dog_names)

            EmailService.send_email_with_retry(
                subject,
                text_content,
                settings.BUSINESS_EMAIL,
                [booking.customer_email],
                html_content=html_content
            )

            logger.info(f"Individual walk request confirmation email sent to {booking.customer_email} for booking {booking.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending individual walk request confirmation email for booking {booking.id}: {str(e)}")
            return False

    @staticmethod
    def send_individual_walk_response(booking):
        """Send approval/rejection email for individual walk request"""
        try:
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)

            if booking.status == 'approved':
                subject = f'Individual Walk Approved - {booking.confirmed_date.strftime("%B %d, %Y")}'
            else:
                subject = f'Individual Walk Request - Update on #{booking.id}'

            context = {
                'booking': booking,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
                'is_approved': booking.status == 'approved',
                'is_rejected': booking.status == 'rejected',
            }

            try:
                html_content = render_to_string('emails/individual_walk_response.html', context)
                text_content = strip_tags(html_content)
            except Exception:
                html_content = None
                text_content = EmailService._create_individual_walk_response_text_email(booking, dog_names)

            EmailService.send_email_with_retry(
                subject,
                text_content,
                settings.BUSINESS_EMAIL,
                [booking.customer_email],
                html_content=html_content
            )

            logger.info(f"Individual walk response email sent to {booking.customer_email} for booking {booking.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending individual walk response email for booking {booking.id}: {str(e)}")
            return False

    @staticmethod
    def send_admin_notification(booking, booking_type):
        """Send notification email to admin for new bookings"""
        try:
            admin_email = getattr(settings, 'ADMIN_EMAIL', settings.BUSINESS_EMAIL)

            if booking_type == 'group_walk':
                subject = f'New Group Walk Booking - {booking.booking_date.strftime("%B %d, %Y")}'
                dog_names = [dog.name for dog in booking.dogs.all()]
                dogs_text = ', '.join(dog_names)

                message = f"""
New Group Walk Booking Received

Booking Details:
- Booking ID: {booking.id}
- Customer: {booking.customer_name}
- Email: {booking.customer_email}
- Phone: {booking.customer_phone}
- Address: {booking.customer_address}, {booking.customer_postcode}
- Date: {booking.booking_date.strftime('%A, %B %d, %Y')}
- Time: {booking.get_time_slot_display()}
- Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
- Status: {booking.get_status_display()}

Calendar Event: {"Created" if booking.calendar_event_id else "Failed to create"}

View in admin: {settings.SITE_URL}/admin/
                """.strip()

            elif booking_type == 'individual_walk':
                subject = f'New Individual Walk Request - {booking.customer_name}'
                dog_names = [dog.name for dog in booking.dogs.all()]
                dogs_text = ', '.join(dog_names)

                message = f"""
New Individual Walk Request Received

Request Details:
- Request ID: {booking.id}
- Customer: {booking.customer_name}
- Email: {booking.customer_email}
- Phone: {booking.customer_phone}
- Address: {booking.customer_address}, {booking.customer_postcode}
- Preferred Date: {booking.preferred_date.strftime('%A, %B %d, %Y')}
- Preferred Time: {booking.preferred_time}
- Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
- Reason: {booking.reason_for_individual}
- Status: {booking.get_status_display()}

Action Required: Please review and respond to this request.

View in admin: {settings.SITE_URL}/admin/
                """.strip()

            else:
                logger.warning(f"Unknown booking type for admin notification: {booking_type}")
                return False

            EmailService.send_email_with_retry(
                subject,
                message,
                settings.BUSINESS_EMAIL,
                [admin_email]
            )

            logger.info(f"Admin notification email sent for {booking_type} booking {booking.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending admin notification email for {booking_type} booking {booking.id}: {str(e)}")
            return False

    @staticmethod
    def send_multi_booking_confirmation(bookings):
        """Send confirmation email for multiple bookings"""
        if not bookings:
            return False

        first_booking = bookings[0]
        total_bookings = len(bookings)

        try:
            sorted_bookings = sorted(bookings, key=lambda b: (b.booking_date, b.time_slot))

            dog_names = [dog.name for dog in first_booking.dogs.all()]
            dogs_text = ', '.join(dog_names)

            subject = f"Multiple Group Walk Bookings Confirmed - {total_bookings} walks for {first_booking.customer_name}"

            booking_list_text = []
            for i, booking in enumerate(sorted_bookings, 1):
                booking_list_text.append(
                    f"Walk #{i} - Booking #{booking.id}\n"
                    f"  📅 {booking.booking_date.strftime('%A, %B %d, %Y')}\n"
                    f"  ⏰ {booking.get_time_slot_display()}\n"
                    f"  🐕 {dogs_text}\n"
                )

            booking_details = '\n'.join(booking_list_text)

            context = {
                'bookings': sorted_bookings,
                'first_booking': first_booking,
                'total_bookings': total_bookings,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
                'booking_details': booking_details,
            }

            try:
                html_content = render_to_string('emails/multi_booking_confirmation.html', context)
                text_content = strip_tags(html_content)
            except Exception:
                html_content = None
                text_content = EmailService._create_multi_booking_text_email(sorted_bookings, dog_names)

            EmailService.send_email_with_retry(
                subject,
                text_content,
                settings.BUSINESS_EMAIL,
                [first_booking.customer_email],
                html_content=html_content
            )

            logger.info(f"Multi-booking confirmation email sent to {first_booking.customer_email} for {total_bookings} bookings")
            return True

        except Exception as e:
            logger.error(f"Error sending multi-booking confirmation email: {str(e)}")
            return False

    @staticmethod
    def send_admin_multi_booking_notification(bookings):
        """Send admin notification for multiple bookings"""
        if not bookings:
            return False

        first_booking = bookings[0]
        total_bookings = len(bookings)

        try:
            admin_email = getattr(settings, 'ADMIN_EMAIL', settings.BUSINESS_EMAIL)
            sorted_bookings = sorted(bookings, key=lambda b: (b.booking_date, b.time_slot))

            dog_names = [dog.name for dog in first_booking.dogs.all()]
            dogs_text = ', '.join(dog_names)

            subject = f"NEW: {total_bookings} Group Walk Bookings - {first_booking.customer_name}"

            booking_summary = ""
            for i, booking in enumerate(sorted_bookings, 1):
                booking_summary += f"""
    Walk #{i} - Booking ID #{booking.id}
    📅 Date: {booking.booking_date.strftime('%A, %B %d, %Y')}
    ⏰ Time: {booking.get_time_slot_display()}
    🐕 Dogs: {dogs_text} ({booking.number_of_dogs} dogs)
    📅 Calendar Event: {'✅ Created' if booking.calendar_event_id else '❌ Failed'}
    🆔 Batch ID: {booking.batch_id}
    """

            all_dogs = first_booking.dogs.all()
            dog_details = ""
            for dog in all_dogs:
                dog_details += f"""
    🐕 {dog.name} ({dog.breed}, {dog.age_display})
    Good with other dogs: {'Yes' if dog.good_with_other_dogs else 'No'}
    Allergies: {dog.allergies or 'None'}
    Special instructions: {dog.special_instructions or 'None'}
    Behavioral notes: {dog.behavioral_notes or 'None'}
    Vet: {dog.vet_name} - {dog.vet_phone}
    """

            message = f"""
    🐕 NEW MULTI-BOOKING ALERT 🐕

    Customer: {first_booking.customer_name}
    Email: {first_booking.customer_email}
    Phone: {first_booking.customer_phone}
    Address: {first_booking.customer_address}, {first_booking.customer_postcode}

    TOTAL BOOKINGS: {total_bookings}

    📅 BOOKING DETAILS:
    {booking_summary}

    🐾 DOG INFORMATION:
    {dog_details}

    💳 BATCH ID: {first_booking.batch_id}

    📅 Calendar Events: {sum(1 for b in bookings if b.calendar_event_id)}/{total_bookings} created successfully

    View in admin: {settings.SITE_URL}/admin/

    ---
    Canine Compadre Multi-Booking System
            """.strip()

            EmailService.send_email_with_retry(
                subject,
                message,
                settings.BUSINESS_EMAIL,
                [admin_email]
            )

            logger.info(f"Admin multi-booking notification sent for {total_bookings} bookings")
            return True

        except Exception as e:
            logger.error(f"Error sending admin multi-booking notification: {str(e)}")
            return False

    # ---------------------------
    # Fallback plain text templates
    # ---------------------------

    @staticmethod
    def _create_group_walk_text_email(booking, dog_names):
        """Create plain text confirmation email for group walk"""
        dogs_text = ', '.join(dog_names)

        return f"""
Hello {booking.customer_name},

Great news! Your group walk booking has been confirmed.

BOOKING DETAILS:
📅 Date & Time: {booking.booking_date.strftime('%A, %B %d, %Y')} at {booking.get_time_slot_display()}
🐕 Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
📍 Pickup Address: {booking.customer_address}, {booking.customer_postcode}
📧 Confirmation Email: {booking.customer_email}
📞 Contact: {booking.customer_phone}
🆔 Booking ID: #{booking.id}

WHAT TO EXPECT:
• Alex will arrive at your address at the scheduled time
• Your dog{'s' if booking.number_of_dogs > 1 else ''} will enjoy a fun group walk with other friendly dogs
• The walk typically lasts 1 hour
• We'll send updates if there are any changes to the schedule

IMPORTANT REMINDERS:
• Please ensure your dog{'s' if booking.number_of_dogs > 1 else ''} {'are' if booking.number_of_dogs > 1 else 'is'} ready for pickup at the scheduled time
• Have water available for after the walk
• Let us know immediately if there are any changes to your plans

If you have any questions or need to make changes to your booking, please contact us at {settings.BUSINESS_EMAIL}

Thank you for choosing Canine Compadre!

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
        """.strip()

    @staticmethod
    def _create_individual_walk_request_text_email(booking, dog_names):
        """Create plain text confirmation email for individual walk request"""
        dogs_text = ', '.join(dog_names)

        return f"""
Hello {booking.customer_name},

Thank you for submitting your individual walk request. We have received your request and will review it shortly.

REQUEST DETAILS:
📅 Preferred Date: {booking.preferred_date.strftime('%A, %B %d, %Y')}
⏰ Preferred Time: {booking.preferred_time}
🐕 Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
📍 Address: {booking.customer_address}, {booking.customer_postcode}
📧 Email: {booking.customer_email}
📞 Phone: {booking.customer_phone}
🆔 Request ID: #{booking.id}

REASON FOR INDIVIDUAL WALK:
{booking.reason_for_individual}

WHAT HAPPENS NEXT:
1. Alex will review your request within 24 hours
2. You'll receive an email with the decision at {booking.customer_email}
3. If approved, we'll confirm the exact date and time
4. Payment will be arranged when the walk is confirmed

If you have any questions about your request, please contact us at {settings.BUSINESS_EMAIL}

Thank you for considering Canine Compadre for your dog's individual walking needs!

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
        """.strip()

    @staticmethod
    def _create_individual_walk_response_text_email(booking, dog_names):
        """Create plain text response email for individual walk request"""
        dogs_text = ', '.join(dog_names)

        if booking.status == 'approved':
            return f"""
Hello {booking.customer_name},

Excellent news! Your individual walk request has been APPROVED.

CONFIRMED BOOKING DETAILS:
📅 Date: {booking.confirmed_date.strftime('%A, %B %d, %Y')}
⏰ Time: {booking.confirmed_time}
🐕 Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
📍 Address: {booking.customer_address}, {booking.customer_postcode}
🆔 Request ID: #{booking.id}

{f"ALEX'S MESSAGE:\n{booking.admin_response}\n" if booking.admin_response else ""}

WHAT HAPPENS NEXT:
• Alex will arrive at your address at the confirmed time
• Please have your dog{'s' if booking.number_of_dogs > 1 else ''} ready for pickup
• The walk will be tailored to your dog's specific needs
• Payment can be made on the day of the walk

If you need to make any changes or have questions, please contact us at {settings.BUSINESS_EMAIL}

Thank you for choosing Canine Compadre!

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
            """.strip()

        else:  # rejected
            return f"""
Hello {booking.customer_name},

Thank you for your individual walk request. After careful consideration, we regret to inform you that your request has been DECLINED.

REQUEST DETAILS:
📅 Preferred Date: {booking.preferred_date.strftime('%A, %B %d, %Y')}
⏰ Preferred Time: {booking.preferred_time}
🐕 Dogs: {dogs_text} ({booking.number_of_dogs} dog{'s' if booking.number_of_dogs > 1 else ''})
🆔 Request ID: #{booking.id}

{f"ALEX'S MESSAGE:\n{booking.admin_response}\n" if booking.admin_response else ""}

Please don't be discouraged — we'd love to accommodate you on another date or time. Group walks may also be a great option for your dog{'s' if booking.number_of_dogs > 1 else ''}.

For alternative arrangements, please contact us at {settings.BUSINESS_EMAIL}

Thank you for your understanding, and we hope to walk your dog{'s' if booking.number_of_dogs > 1 else ''} soon!

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
            """.strip()

    @staticmethod
    def _create_multi_booking_text_email(bookings, dog_names):
        """Create plain text confirmation email for multiple group walks"""
        first_booking = bookings[0]
        dogs_text = ', '.join(dog_names)
        total_bookings = len(bookings)

        booking_list_text = []
        for i, booking in enumerate(bookings, 1):
            booking_list_text.append(
                f"Walk #{i} - Booking #{booking.id}\n"
                f"📅 {booking.booking_date.strftime('%A, %B %d, %Y')}\n"
                f"⏰ {booking.get_time_slot_display()}\n"
                f"🐕 {dogs_text}\n"
            )

        booking_details = '\n'.join(booking_list_text)

        return f"""
Hello {first_booking.customer_name},

Great news! Your MULTIPLE group walk bookings have been confirmed.

TOTAL BOOKINGS: {total_bookings}

BOOKING DETAILS:
{booking_details}

WHAT TO EXPECT:
• Alex will arrive at your address at the scheduled times
• Your dog{'s' if first_booking.number_of_dogs > 1 else ''} will enjoy fun group walks with other friendly dogs
• Each walk typically lasts 1 hour
• We'll send updates if there are any changes to the schedule

IMPORTANT REMINDERS:
• Please ensure your dog{'s' if first_booking.number_of_dogs > 1 else ''} {'are' if first_booking.number_of_dogs > 1 else 'is'} ready for pickup at the scheduled times
• Have water available for after each walk
• Let us know immediately if there are any changes to your plans

If you have any questions or need to make changes to your bookings, please contact us at {settings.BUSINESS_EMAIL}

Thank you for choosing Canine Compadre!

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
        """.strip()
