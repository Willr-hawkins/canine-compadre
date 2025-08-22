from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending booking confirmation and notification emails"""
    
    @staticmethod
    def send_group_walk_confirmation(booking):
        """Send confirmation email to customer for group walk booking"""
        try:
            # Get dog names
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)
            
            subject = f'Group Walk Confirmed - {booking.booking_date.strftime("%B %d, %Y")}'
            
            # Create context for email template
            context = {
                'booking': booking,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
                'confirmation_url': f"{settings.SITE_URL}/booking-confirmation/{booking.id}/group/",
            }
            
            # Try to render HTML template, fallback to plain text
            try:
                html_content = render_to_string('emails/group_walk_confirmation.html', context)
                text_content = strip_tags(html_content)
            except:
                # Fallback to plain text email
                html_content = None
                text_content = EmailService._create_group_walk_text_email(booking, dog_names)
            
            # Send email
            if html_content:
                # Send HTML email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    to=[booking.customer_email],
                    reply_to=[settings.BUSINESS_EMAIL]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    recipient_list=[booking.customer_email],
                    fail_silently=False
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
            # Get dog names
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)
            
            subject = f'Individual Walk Request Received - #{booking.id}'
            
            # Create context for email template
            context = {
                'booking': booking,
                'dog_names': dog_names,
                'dogs_text': dogs_text,
                'business_name': 'Canine Compadre',
                'business_email': settings.BUSINESS_EMAIL,
                'business_phone': getattr(settings, 'BUSINESS_PHONE', ''),
            }
            
            # Try to render HTML template, fallback to plain text
            try:
                html_content = render_to_string('emails/individual_walk_request_confirmation.html', context)
                text_content = strip_tags(html_content)
            except:
                # Fallback to plain text email
                html_content = None
                text_content = EmailService._create_individual_walk_request_text_email(booking, dog_names)
            
            # Send email
            if html_content:
                # Send HTML email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    to=[booking.customer_email],
                    reply_to=[settings.BUSINESS_EMAIL]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    recipient_list=[booking.customer_email],
                    fail_silently=False
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
            # Get dog names
            dog_names = [dog.name for dog in booking.dogs.all()]
            dogs_text = ', '.join(dog_names)
            
            if booking.status == 'approved':
                subject = f'Individual Walk Approved - {booking.confirmed_date.strftime("%B %d, %Y")}'
            else:
                subject = f'Individual Walk Request - Update on #{booking.id}'
            
            # Create context for email template
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
            
            # Try to render HTML template, fallback to plain text
            try:
                template_name = 'emails/individual_walk_response.html'
                html_content = render_to_string(template_name, context)
                text_content = strip_tags(html_content)
            except:
                # Fallback to plain text email
                html_content = None
                text_content = EmailService._create_individual_walk_response_text_email(booking, dog_names)
            
            # Send email
            if html_content:
                # Send HTML email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    to=[booking.customer_email],
                    reply_to=[settings.BUSINESS_EMAIL]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    recipient_list=[booking.customer_email],
                    fail_silently=False
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
            
            # Send plain text email to admin
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.BUSINESS_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False
            )
            
            logger.info(f"Admin notification email sent for {booking_type} booking {booking.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending admin notification email for {booking_type} booking {booking.id}: {str(e)}")
            return False
    
    # Text email fallback methods
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

Thank you for your individual walk request. After careful consideration, we are unable to accommodate your request at this time.

REQUEST DETAILS:
📅 Requested Date: {booking.preferred_date.strftime('%A, %B %d, %Y')}
⏰ Requested Time: {booking.preferred_time}
🐕 Dogs: {dogs_text}
🆔 Request ID: #{booking.id}

{f"ALEX'S MESSAGE:\n{booking.admin_response}\n" if booking.admin_response else ""}

ALTERNATIVE OPTIONS:
• Consider booking a group walk if your dog is sociable with other dogs
• Contact us to discuss alternative dates or times
• We may be able to accommodate your request in the future

If you'd like to discuss other options or have questions, please contact us at {settings.BUSINESS_EMAIL}

Thank you for considering Canine Compadre.

Best regards,
Alex
Canine Compadre
{settings.BUSINESS_EMAIL}
            """.strip()

    @staticmethod
    def send_multi_booking_confirmation(bookings):
        """Send confirmation email for multiple bookings"""
        if not bookings:
            return False
            
        first_booking = bookings[0]
        total_bookings = len(bookings)
        
        try:
            # Sort bookings by date and time
            sorted_bookings = sorted(bookings, key=lambda b: (b.booking_date, b.time_slot))
            
            # Get dog names (same across all bookings)
            dog_names = [dog.name for dog in first_booking.dogs.all()]
            dogs_text = ', '.join(dog_names)
            
            subject = f"Multiple Group Walk Bookings Confirmed - {total_bookings} walks for {first_booking.customer_name}"
            
            # Create booking list for email
            booking_list_text = []
            for i, booking in enumerate(sorted_bookings, 1):
                booking_list_text.append(
                    f"Walk #{i} - Booking #{booking.id}\n"
                    f"  📅 {booking.booking_date.strftime('%A, %B %d, %Y')}\n"
                    f"  ⏰ {booking.get_time_slot_display()}\n"
                    f"  🐕 {dogs_text}\n"
                )
            
            booking_details = '\n'.join(booking_list_text)
            
            # Create context for email template
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
            
            # Try to render HTML template, fallback to plain text
            try:
                html_content = render_to_string('emails/multi_booking_confirmation.html', context)
                text_content = strip_tags(html_content)
            except:
                # Fallback to plain text email
                html_content = None
                text_content = EmailService._create_multi_booking_text_email(sorted_bookings, dog_names)
            
            # Send email
            if html_content:
                # Send HTML email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    to=[first_booking.customer_email],
                    reply_to=[settings.BUSINESS_EMAIL]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.BUSINESS_EMAIL,
                    recipient_list=[first_booking.customer_email],
                    fail_silently=False
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
            
            # Sort bookings by date and time
            sorted_bookings = sorted(bookings, key=lambda b: (b.booking_date, b.time_slot))
            
            # Get dog names (same across all bookings)
            dog_names = [dog.name for dog in first_booking.dogs.all()]
            dogs_text = ', '.join(dog_names)
            
            subject = f"NEW: {total_bookings} Group Walk Bookings - {first_booking.customer_name}"
            
            # Create booking summary for admin
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
            
            # Get all dogs for the first booking (since they're the same across all bookings)
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
            
            # Send plain text email to admin
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.BUSINESS_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False
            )
            
            logger.info(f"Admin multi-booking notification sent for {total_bookings} bookings")
            return True
            
        except Exception as e:
            logger.error(f"Error sending admin multi-booking notification: {str(e)}")
            return False

    # ADD this helper method as well:

    @staticmethod
    def _create_multi_booking_text_email(bookings, dog_names):
        """Create plain text confirmation email for multiple bookings"""
        first_booking = bookings[0]
        total_bookings = len(bookings)
        dogs_text = ', '.join(dog_names)
        
        # Create booking list
        booking_list = []
        for i, booking in enumerate(bookings, 1):
            booking_list.append(
                f"Walk #{i} - Booking #{booking.id}\n"
                f"  📅 {booking.booking_date.strftime('%A, %B %d, %Y')}\n"
                f"  ⏰ {booking.get_time_slot_display()}\n"
                f"  🐕 {dogs_text}"
            )
        
        booking_details = '\n\n'.join(booking_list)
        
        return f"""
    Hello {first_booking.customer_name},

    Fantastic news! Your {total_bookings} group walk bookings have been confirmed.

    YOUR CONFIRMED BOOKINGS:

    {booking_details}

    CUSTOMER DETAILS:
    📧 Email: {first_booking.customer_email}
    📞 Phone: {first_booking.customer_phone}
    📍 Pickup Address: {first_booking.customer_address}, {first_booking.customer_postcode}
    🐕 Dogs: {dogs_text} ({first_booking.number_of_dogs} dog{'s' if first_booking.number_of_dogs > 1 else ''})

    WHAT TO EXPECT:
    • Alex will arrive at your address at each scheduled time
    • Your dog{'s' if first_booking.number_of_dogs > 1 else ''} will enjoy fun group walks with other friendly dogs
    • Each walk typically lasts about 1-2 hours
    • We'll send updates if there are any changes to the schedule

    IMPORTANT REMINDERS:
    • Please ensure your dog{'s' if first_booking.number_of_dogs > 1 else ''} {'are' if first_booking.number_of_dogs > 1 else 'is'} ready for pickup at each scheduled time
    • Have water available after each walk
    • Let us know immediately if there are any changes to your plans for any of the walks

    If you have any questions or need to make changes to any of your bookings, please contact us at {settings.BUSINESS_EMAIL}

    Thank you for choosing Canine Compadre for multiple walks!

    Best regards,
    Alex
    Canine Compadre
    {settings.BUSINESS_EMAIL}
        """.strip()