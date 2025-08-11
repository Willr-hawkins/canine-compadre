from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import models
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import date, timedelta
import json
import logging

from .models import GroupWalk, IndividualWalk, Dog, GroupWalkSlotManager
from .forms import (
    GroupWalkForm, IndividualWalkForm, DogForm, 
    GroupWalkDogFormSet, IndividualWalkDogFormSet,
    AdminResponseForm
)

# Import our new services
try:
    from .calendar_service import GoogleCalendarService
    from .email_service import EmailService
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Calendar or email service not available: {e}")
    INTEGRATIONS_AVAILABLE = False

logger = logging.getLogger(__name__)

def home(request):
    """Main page with all sections including booking"""
    return render(request, 'home/home.html')

@require_http_methods(["POST"])
def group_walk_booking(request):
    """Handle group walk bookings via AJAX - return JSON response with full integration"""
    
    # Parse form data
    form = GroupWalkForm(request.POST)
    
    # Handle dog formset data manually since we're using AJAX
    dog_data = []
    num_dogs = int(request.POST.get('number_of_dogs', 0))
    
    for i in range(num_dogs):
        dog_info = {
            'name': request.POST.get(f'dog_{i}_name', ''),
            'breed': request.POST.get(f'dog_{i}_breed', ''),
            'age': request.POST.get(f'dog_{i}_age', ''),
            'allergies': request.POST.get(f'dog_{i}_allergies', ''),
            'special_instructions': request.POST.get(f'dog_{i}_special_instructions', ''),
            'good_with_other_dogs': request.POST.get(f'dog_{i}_good_with_other_dogs') == 'on',
            'behavioral_notes': request.POST.get(f'dog_{i}_behavioral_notes', ''),
            'vet_name': request.POST.get(f'dog_{i}_vet_name', ''),
            'vet_phone': request.POST.get(f'dog_{i}_vet_phone', ''),
            'vet_address': request.POST.get(f'dog_{i}_vet_address', ''),
        }
        dog_data.append(dog_info)
    
    # Validate form
    if form.is_valid() and len(dog_data) == num_dogs:
        try:
            with transaction.atomic():
                # Create the group walk booking
                booking = form.save()
                
                # Create dog records
                created_dogs = []
                for dog_info in dog_data:
                    if dog_info['name']:  # Only create if name is provided
                        # Validate required vet fields
                        if not dog_info['vet_name'] or not dog_info['vet_phone'] or not dog_info['vet_address']:
                            raise ValueError("All veterinary information fields are required")
                        
                        dog = Dog.objects.create(
                            group_walk=booking,
                            name=dog_info['name'],
                            breed=dog_info['breed'],
                            age=int(dog_info['age']) if dog_info['age'] else 0,
                            allergies=dog_info['allergies'],
                            special_instructions=dog_info['special_instructions'],
                            good_with_other_dogs=dog_info['good_with_other_dogs'],
                            behavioral_notes=dog_info['behavioral_notes'],
                            vet_name=dog_info['vet_name'],
                            vet_phone=dog_info['vet_phone'],
                            vet_address=dog_info['vet_address'],
                        )
                        created_dogs.append(dog)
                
                # Verify we have the right number of dogs
                if len(created_dogs) != booking.number_of_dogs:
                    raise ValueError(f"Expected {booking.number_of_dogs} dogs, but only {len(created_dogs)} were created")

                # Create calendar event now that dogs exist
                if not booking.calendar_event_id:
                    try:
                        from .calendar_service import GoogleCalendarService
                        calendar_service = GoogleCalendarService()
                        event_id = calendar_service.create_group_walk_event(booking)
                        if event_id:
                            booking.calendar_event_id = event_id
                            booking.save(update_fields=['calendar_event_id'])
                            logger.info(f"Calendar event created for group walk booking {booking.id}: {event_id}")
                    except Exception as e:
                        logger.error(f"Error creating calendar event for booking {booking.id}: {str(e)}")
                
                # Send confirmation email to customer
                customer_email_sent = False
                if INTEGRATIONS_AVAILABLE:
                    try:
                        customer_email_sent = EmailService.send_group_walk_confirmation(booking)
                        if customer_email_sent:
                            logger.info(f"Confirmation email sent for group walk booking {booking.id}")
                        else:
                            logger.warning(f"Failed to send confirmation email for booking {booking.id}")
                    except Exception as e:
                        logger.error(f"Error sending confirmation email for booking {booking.id}: {str(e)}")
                
                # Send admin notification
                admin_email_sent = False
                if INTEGRATIONS_AVAILABLE:
                    try:
                        admin_email_sent = EmailService.send_admin_notification(booking, 'group_walk')
                        if admin_email_sent:
                            logger.info(f"Admin notification sent for group walk booking {booking.id}")
                    except Exception as e:
                        logger.error(f"Error sending admin notification for booking {booking.id}: {str(e)}")
                
                # Success response with confirmation HTML
                dog_names = [dog.name for dog in created_dogs]
                
                # Create status indicators
                calendar_status = "✅ Added to calendar" if booking.calendar_event_id else "⚠️ Calendar sync pending"
                email_status = f"📧 Confirmation sent to {booking.customer_email}" if customer_email_sent else "⚠️ Email confirmation pending"
                
                success_html = f"""
                <div class="booking-success text-center">
                    <div class="alert alert-success">
                        <h4><i class="bi bi-check-circle-fill me-2"></i>Group Walk Booking Confirmed!</h4>
                        <hr>
                        <div class="booking-details">
                            <p><strong>Booking ID:</strong> #{booking.id}</p>
                            <p><strong>Date & Time:</strong> {booking.booking_date.strftime('%A, %B %d, %Y')} at {booking.get_time_slot_display()}</p>
                            <p><strong>Customer:</strong> {booking.customer_name}</p>
                            <p><strong>Email:</strong> {booking.customer_email}</p>
                            <p><strong>Phone:</strong> {booking.customer_phone}</p>
                            <p><strong>Address:</strong> {booking.customer_address}, {booking.customer_postcode}</p>
                            <p><strong>Dogs:</strong> {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})</p>
                        </div>
                        <hr>
                        <div class="status-updates">
                            <p class="mb-1">{calendar_status}</p>
                            <p class="mb-2">{email_status}</p>
                        </div>
                        <div class="next-steps">
                            <h6>What happens next?</h6>
                            <ul class="text-start">
                                <li>Alex will arrive at your address at the scheduled time</li>
                                <li>Your dog{'s' if len(dog_names) > 1 else ''} will enjoy a group walk with other friendly dogs</li>
                                <li>You'll receive updates if there are any changes to the schedule</li>
                            </ul>
                        </div>
                        <button class="btn btn-primary mt-3" onclick="resetBookingSection()">Book Another Walk</button>
                    </div>
                </div>
                """
                
                return JsonResponse({
                    'success': True,
                    'message': 'Group walk booking confirmed successfully!',
                    'html': success_html,
                    'booking_id': booking.id,
                    'calendar_created': bool(booking.calendar_event_id),
                    'email_sent': customer_email_sent,
                })
                
        except ValidationError as e:
            logger.error(f"Validation error in group walk booking: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': {'general': [str(e)]}
            })
        except ValueError as e:
            logger.error(f"Value error in group walk booking: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': {'general': [str(e)]}
            })
        except Exception as e:
            logger.error(f"Unexpected error in group walk booking: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while processing your booking. Please try again or contact us directly.',
                'errors': {'general': ['An unexpected error occurred']}
            })
    
    else:
        # Form validation errors
        errors = {}
        if not form.is_valid():
            errors.update(form.errors)
            logger.warning(f"Group walk form validation errors: {form.errors}")
        
        # Validate dog data
        for i, dog_info in enumerate(dog_data):
            if not dog_info['name']:
                errors[f'dog_{i}_name'] = ['Dog name is required']
            if not dog_info['breed']:
                errors[f'dog_{i}_breed'] = ['Dog breed is required']
            if not dog_info['age']:
                errors[f'dog_{i}_age'] = ['Dog age is required']
            if not dog_info['vet_name']:
                errors[f'dog_{i}_vet_name'] = ['Veterinary practice name is required']
            if not dog_info['vet_phone']:
                errors[f'dog_{i}_vet_phone'] = ['Veterinary practice phone is required']
            if not dog_info['vet_address']:
                errors[f'dog_{i}_vet_address'] = ['Veterinary practice address is required']
        
        return JsonResponse({
            'success': False,
            'message': 'Please correct the errors below',
            'errors': errors
        })

@require_http_methods(["POST"])
def individual_walk_booking(request):
    """Handle individual walk requests via AJAX - return JSON response with full integration"""
    
    # Parse form data and handle preferred_time_choice conversion
    form_data = request.POST.copy()
    
    # Handle preferred_time_choice conversion - UPDATED for new available times
    preferred_time_choice = form_data.get('preferred_time_choice')
    if preferred_time_choice == 'early_morning':
        form_data['preferred_time'] = 'Early Morning (7:00 AM - 9:00 AM)'
    elif preferred_time_choice == 'late_evening':
        form_data['preferred_time'] = 'Late Evening (9:00 PM - 11:00 PM)'
    elif preferred_time_choice == 'flexible':
        form_data['preferred_time'] = 'Flexible - please suggest a suitable time'
    # For 'custom', leave the preferred_time as is (user entered)
    
    form = IndividualWalkForm(form_data)
    
    # Handle dog formset data manually
    dog_data = []
    num_dogs = int(request.POST.get('number_of_dogs', 0))
    
    for i in range(num_dogs):
        dog_info = {
            'name': request.POST.get(f'dog_{i}_name', ''),
            'breed': request.POST.get(f'dog_{i}_breed', ''),
            'age': request.POST.get(f'dog_{i}_age', ''),
            'allergies': request.POST.get(f'dog_{i}_allergies', ''),
            'special_instructions': request.POST.get(f'dog_{i}_special_instructions', ''),
            'good_with_other_dogs': request.POST.get(f'dog_{i}_good_with_other_dogs') == 'on',
            'behavioral_notes': request.POST.get(f'dog_{i}_behavioral_notes', ''),
            'vet_name': request.POST.get(f'dog_{i}_vet_name', ''),
            'vet_phone': request.POST.get(f'dog_{i}_vet_phone', ''),
            'vet_address': request.POST.get(f'dog_{i}_vet_address', ''),
        }
        dog_data.append(dog_info)
    
    # Validate form
    if form.is_valid() and len(dog_data) == num_dogs:
        try:
            with transaction.atomic():
                # Create the individual walk request
                booking = form.save()
                
                # Create dog records
                created_dogs = []
                for dog_info in dog_data:
                    if dog_info['name']:  # Only create if name is provided
                        # Validate required vet fields
                        if not dog_info['vet_name'] or not dog_info['vet_phone'] or not dog_info['vet_address']:
                            raise ValueError("All veterinary information fields are required")
                        
                        dog = Dog.objects.create(
                            individual_walk=booking,
                            name=dog_info['name'],
                            breed=dog_info['breed'],
                            age=int(dog_info['age']) if dog_info['age'] else 0,
                            allergies=dog_info['allergies'],
                            special_instructions=dog_info['special_instructions'],
                            good_with_other_dogs=dog_info['good_with_other_dogs'],
                            behavioral_notes=dog_info['behavioral_notes'],
                            vet_name=dog_info['vet_name'],
                            vet_phone=dog_info['vet_phone'],
                            vet_address=dog_info['vet_address'],
                        )
                        created_dogs.append(dog)
                
                # Verify we have the right number of dogs
                if len(created_dogs) != booking.number_of_dogs:
                    raise ValueError(f"Expected {booking.number_of_dogs} dogs, but only {len(created_dogs)} were created")
                
                # Send confirmation email to customer
                customer_email_sent = False
                if INTEGRATIONS_AVAILABLE:
                    try:
                        customer_email_sent = EmailService.send_individual_walk_request_confirmation(booking)
                        if customer_email_sent:
                            logger.info(f"Confirmation email sent for individual walk request {booking.id}")
                        else:
                            logger.warning(f"Failed to send confirmation email for individual walk request {booking.id}")
                    except Exception as e:
                        logger.error(f"Error sending confirmation email for individual walk request {booking.id}: {str(e)}")
                
                # Send admin notification
                admin_email_sent = False
                if INTEGRATIONS_AVAILABLE:
                    try:
                        admin_email_sent = EmailService.send_admin_notification(booking, 'individual_walk')
                        if admin_email_sent:
                            logger.info(f"Admin notification sent for individual walk request {booking.id}")
                    except Exception as e:
                        logger.error(f"Error sending admin notification for individual walk request {booking.id}: {str(e)}")
                
                # Success response with confirmation HTML
                dog_names = [dog.name for dog in created_dogs]
                
                # Create status indicators
                email_status = f"📧 Confirmation sent to {booking.customer_email}" if customer_email_sent else "⚠️ Email confirmation pending"
                
                success_html = f"""
                <div class="booking-success text-center">
                    <div class="alert alert-info">
                        <h4><i class="bi bi-clock-fill me-2"></i>Individual Walk Request Submitted!</h4>
                        <hr>
                        <div class="booking-details">
                            <p><strong>Request ID:</strong> #{booking.id}</p>
                            <p><strong>Preferred Date:</strong> {booking.preferred_date.strftime('%A, %B %d, %Y')}</p>
                            <p><strong>Preferred Time:</strong> {booking.preferred_time}</p>
                            <p><strong>Customer:</strong> {booking.customer_name}</p>
                            <p><strong>Email:</strong> {booking.customer_email}</p>
                            <p><strong>Phone:</strong> {booking.customer_phone}</p>
                            <p><strong>Address:</strong> {booking.customer_address}, {booking.customer_postcode}</p>
                            <p><strong>Dogs:</strong> {', '.join(dog_names)} ({len(dog_names)} dog{'s' if len(dog_names) != 1 else ''})</p>
                            <p><strong>Reason:</strong> {booking.reason_for_individual}</p>
                        </div>
                        <hr>
                        <div class="status-updates">
                            <p class="mb-2">{email_status}</p>
                        </div>
                        <div class="next-steps">
                            <h6><strong>What happens next?</strong></h6>
                            <ol class="text-start">
                                <li>Alex will review your request within 24 hours</li>
                                <li>You'll receive an email at {booking.customer_email} with the decision</li>
                                <li>If approved, we'll confirm the exact date and time</li>
                                <li>Payment will be arranged when the walk is confirmed</li>
                            </ol>
                        </div>
                        <button class="btn btn-primary mt-3" onclick="resetBookingSection()">Submit Another Request</button>
                    </div>
                </div>
                """
                
                return JsonResponse({
                    'success': True,
                    'message': 'Individual walk request submitted successfully!',
                    'html': success_html,
                    'booking_id': booking.id,
                    'email_sent': customer_email_sent,
                })
                
        except ValidationError as e:
            logger.error(f"Validation error in individual walk request: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': {'general': [str(e)]}
            })
        except ValueError as e:
            logger.error(f"Value error in individual walk request: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': {'general': [str(e)]}
            })
        except Exception as e:
            logger.error(f"Unexpected error in individual walk request: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while processing your request. Please try again or contact us directly.',
                'errors': {'general': ['An unexpected error occurred']}
            })
    
    else:
        # Form validation errors
        errors = {}
        if not form.is_valid():
            errors.update(form.errors)
            logger.warning(f"Individual walk form validation errors: {form.errors}")
        
        # Validate dog data
        for i, dog_info in enumerate(dog_data):
            if not dog_info['name']:
                errors[f'dog_{i}_name'] = ['Dog name is required']
            if not dog_info['breed']:
                errors[f'dog_{i}_breed'] = ['Dog breed is required']
            if not dog_info['age']:
                errors[f'dog_{i}_age'] = ['Dog age is required']
            if not dog_info['vet_name']:
                errors[f'dog_{i}_vet_name'] = ['Veterinary practice name is required']
            if not dog_info['vet_phone']:
                errors[f'dog_{i}_vet_phone'] = ['Veterinary practice phone is required']
            if not dog_info['vet_address']:
                errors[f'dog_{i}_vet_address'] = ['Veterinary practice address is required']
        
        logger.warning(f"Individual walk booking validation failed: {errors}")
        
        return JsonResponse({
            'success': False,
            'message': 'Please correct the errors below',
            'errors': errors
        })

def get_availability_calendar(request):
    """AJAX endpoint to get calendar availability data for group walks with slot manager integration"""
    try:
        days_ahead = int(request.GET.get('days', 30))
        num_dogs = int(request.GET.get('num_dogs', 1))
        
        # Validate parameters
        if num_dogs < 1 or num_dogs > 4:
            return JsonResponse({'error': 'Invalid number of dogs'}, status=400)
        if days_ahead < 1 or days_ahead > 90:
            return JsonResponse({'error': 'Invalid date range'}, status=400)
        
        # Get available slots using the model method
        available_slots = GroupWalk.get_available_slots(days_ahead=days_ahead, required_dogs=num_dogs)
        
        # Group slots by date
        availability_data = []
        current_date = None
        current_day_data = None
        
        for slot in available_slots:
            if current_date != slot['date']:
                # Save previous day if exists
                if current_day_data:
                    availability_data.append(current_day_data)
                
                # Start new day
                current_date = slot['date']
                current_day_data = {
                    'date': current_date.isoformat(),
                    'date_display': current_date.strftime('%B %d, %Y'),
                    'day_name': current_date.strftime('%A'),
                    'slots': []
                }
            
            # Add slot to current day
            current_day_data['slots'].append({
                'time_slot': slot['time_slot'],
                'time_display': slot['time_display'],
                'available_spots': slot['available_spots'],
                'can_book': slot['can_book'],
                'is_full': slot['is_full'],
                'requested_dogs': num_dogs
            })
        
        # Don't forget the last day
        if current_day_data:
            availability_data.append(current_day_data)
        
        # Filter out days with no available slots
        availability_data = [
            day for day in availability_data 
            if any(slot['can_book'] for slot in day['slots'])
        ]
        
        return JsonResponse({
            'availability': availability_data,
            'total_days_with_availability': len(availability_data),
            'requested_dogs': num_dogs,
        })
        
    except ValueError as e:
        logger.error(f"Value error in get_availability_calendar: {str(e)}")
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in get_availability_calendar: {str(e)}")
        return JsonResponse({'error': 'An error occurred while loading availability'}, status=500)

def check_slot_availability(request):
    """AJAX endpoint to check specific slot availability in real-time - UPDATED for new time slots"""
    try:
        booking_date = request.GET.get('date')
        time_slot = request.GET.get('time_slot')
        num_dogs = int(request.GET.get('num_dogs', 1))
        
        if not booking_date or not time_slot:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        
        try:
            booking_date = date.fromisoformat(booking_date)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        
        # Validate date is not in the past
        if booking_date <= date.today():
            return JsonResponse({
                'available_spots': 0,
                'can_book': False,
                'requested_dogs': num_dogs,
                'message': 'Cannot book walks for past dates'
            })
        
        # Check slot manager restrictions
        slot_manager = GroupWalkSlotManager.objects.filter(date=booking_date).first()
        max_capacity = 4  # default
        
        if slot_manager:
            # UPDATED for new time slots
            if time_slot == '10:00-12:00' and not slot_manager.morning_slot_available:
                return JsonResponse({
                    'available_spots': 0,
                    'can_book': False,
                    'requested_dogs': num_dogs,
                    'message': 'This time slot is not available on this date'
                })
            elif time_slot == '14:00-16:00' and not slot_manager.afternoon_slot_available:
                return JsonResponse({
                    'available_spots': 0,
                    'can_book': False,
                    'requested_dogs': num_dogs,
                    'message': 'This time slot is not available on this date'
                })
            elif time_slot == '18:00-20:00' and not slot_manager.evening_slot_available:
                return JsonResponse({
                    'available_spots': 0,
                    'can_book': False,
                    'requested_dogs': num_dogs,
                    'message': 'This time slot is not available on this date'
                })
            
            # Use custom capacity if set - UPDATED for new time slots
            if time_slot == '10:00-12:00':
                max_capacity = slot_manager.morning_slot_capacity
            elif time_slot == '14:00-16:00':
                max_capacity = slot_manager.afternoon_slot_capacity
            elif time_slot == '18:00-20:00':
                max_capacity = slot_manager.evening_slot_capacity
        
        # Calculate available spots
        total_dogs_booked = GroupWalk.objects.filter(
            booking_date=booking_date,
            time_slot=time_slot,
            status='confirmed'
        ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0
        
        available_spots = max_capacity - total_dogs_booked
        can_book = available_spots >= num_dogs
        
        return JsonResponse({
            'available_spots': available_spots,
            'can_book': can_book,
            'requested_dogs': num_dogs,
            'max_capacity': max_capacity,
            'message': f'{"Available" if can_book else "Not enough space"} - {available_spots} spots remaining'
        })
        
    except ValueError as e:
        logger.error(f"Value error in check_slot_availability: {str(e)}")
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in check_slot_availability: {str(e)}")
        return JsonResponse({'error': 'An error occurred while checking availability'}, status=500)

# Admin views for managing bookings

def admin_dashboard(request):
    """Admin dashboard to view all bookings with enhanced functionality"""
    try:
        # Get upcoming group walk bookings (next 7 days)
        upcoming_bookings = GroupWalk.objects.filter(
            booking_date__gte=date.today(),
            booking_date__lte=date.today() + timedelta(days=7)
        ).select_related().prefetch_related('dogs').order_by('booking_date', 'time_slot')[:20]
        
        # Get pending individual walk requests
        pending_requests = IndividualWalk.objects.filter(
            status='pending'
        ).select_related().prefetch_related('dogs').order_by('-created_at')[:10]
        
        # Get today's bookings
        today_bookings = GroupWalk.objects.filter(
            booking_date=date.today(),
            status='confirmed'
        ).select_related().prefetch_related('dogs').order_by('time_slot')
        
        # Get recent approved/rejected individual walks
        recent_individual_responses = IndividualWalk.objects.filter(
            status__in=['approved', 'rejected']
        ).select_related().order_by('-updated_at')[:5]
        
        # Calculate some stats
        total_pending = pending_requests.count()
        total_today = today_bookings.count()
        total_upcoming = upcoming_bookings.count()
        
        context = {
            'upcoming_bookings': upcoming_bookings,
            'pending_requests': pending_requests,
            'today_bookings': today_bookings,
            'recent_individual_responses': recent_individual_responses,
            'stats': {
                'total_pending': total_pending,
                'total_today': total_today,
                'total_upcoming': total_upcoming,
            },
            'today': date.today(),
        }
        
        return render(request, 'bookings/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        messages.error(request, "Error loading dashboard data")
        return render(request, 'bookings/admin_dashboard.html', {'today': date.today()})

def admin_individual_request_detail(request, request_id):
    """Admin view to manage individual walk requests with full integration"""
    try:
        individual_request = get_object_or_404(IndividualWalk, id=request_id)
        dogs = individual_request.dogs.all()
        
        if request.method == 'POST':
            form = AdminResponseForm(request.POST, instance=individual_request)
            if form.is_valid():
                old_status = individual_request.status
                updated_request = form.save()
                
                # Handle status changes with integrations
                if old_status != updated_request.status:
                    if updated_request.status == 'approved':
                        messages.success(
                            request, 
                            f'Individual walk request approved for {updated_request.customer_name}. '
                            f'Confirmed for {updated_request.confirmed_date} at {updated_request.confirmed_time}.'
                        )
                        
                    elif updated_request.status == 'rejected':
                        messages.success(
                            request, 
                            f'Individual walk request rejected for {updated_request.customer_name}.'
                        )
                
                return redirect('admin_dashboard')
                
        else:
            form = AdminResponseForm(instance=individual_request)
        
        return render(request, 'bookings/admin_individual_request.html', {
            'booking_request': individual_request,
            'dogs': dogs,
            'form': form,
            'integrations_available': INTEGRATIONS_AVAILABLE,
        })
        
    except Http404:
        messages.error(request, "Individual walk request not found")
        return redirect('admin_dashboard')
    except Exception as e:
        logger.error(f"Error in admin individual request detail: {str(e)}")
        messages.error(request, "Error loading request details")
        return redirect('admin_dashboard')

def admin_group_walk_detail(request, booking_id):
    """Admin view to manage group walk bookings"""
    try:
        booking = get_object_or_404(GroupWalk, id=booking_id)
        dogs = booking.dogs.all()
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'cancel':
                booking.cancel(reason=request.POST.get('reason', 'Cancelled by admin'))
                messages.success(request, f'Group walk booking cancelled for {booking.customer_name}')
                
            elif action == 'complete':
                booking.status = 'completed'
                booking.save()
                messages.success(request, f'Group walk marked as completed for {booking.customer_name}')
            
            return redirect('admin_dashboard')
        
        return render(request, 'bookings/admin_group_walk_detail.html', {
            'booking': booking,
            'dogs': dogs,
            'integrations_available': INTEGRATIONS_AVAILABLE,
        })
        
    except Http404:
        messages.error(request, "Group walk booking not found")
        return redirect('admin_dashboard')
    except Exception as e:
        logger.error(f"Error in admin group walk detail: {str(e)}")
        messages.error(request, "Error loading booking details")
        return redirect('admin_dashboard')

@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint with integration status"""
    status_data = {
        'status': 'ok',
        'timestamp': date.today().isoformat(),
        'integrations': {
            'calendar_service': False,
            'email_service': False,
        }
    }
    
    # Check if integrations are working
    if INTEGRATIONS_AVAILABLE:
        try:
            from .calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService()
            status_data['integrations']['calendar_service'] = calendar_service.service is not None
        except Exception:
            pass
        
        try:
            from .email_service import EmailService
            status_data['integrations']['email_service'] = True
        except Exception:
            pass
    
    return JsonResponse(status_data)

# API endpoints for form templates (optional - for dynamic form loading)

@require_http_methods(["GET"])
def api_group_form_template(request):
    """Return group walk form HTML template"""
    try:
        form = GroupWalkForm()
        html = render_to_string('bookings/forms/group_walk_form_template.html', {
            'form': form,
        }, request=request)
        return JsonResponse({'html': html})
    except Exception as e:
        logger.error(f"Error rendering group form template: {str(e)}")
        return JsonResponse({'error': 'Template not available'}, status=500)

@require_http_methods(["GET"])
def api_individual_form_template(request):
    """Return individual walk form HTML template"""
    try:
        form = IndividualWalkForm()
        html = render_to_string('bookings/forms/individual_walk_form_template.html', {
            'form': form,
        }, request=request)
        return JsonResponse({'html': html})
    except Exception as e:
        logger.error(f"Error rendering individual form template: {str(e)}")
        return JsonResponse({'error': 'Template not available'}, status=500)

# Utility views

def booking_confirmation(request, booking_id, booking_type):
    """Public confirmation page for bookings (accessible via email links)"""
    try:
        if booking_type == 'group':
            booking = get_object_or_404(GroupWalk, id=booking_id)
            template = 'bookings/confirmation/group_walk_confirmation.html'
        elif booking_type == 'individual':
            booking = get_object_or_404(IndividualWalk, id=booking_id)
            template = 'bookings/confirmation/individual_walk_confirmation.html'
        else:
            raise Http404("Invalid booking type")
        
        dogs = booking.dogs.all()
        
        return render(request, template, {
            'booking': booking,
            'dogs': dogs,
            'booking_type': booking_type,
        })
        
    except Http404:
        messages.error(request, "Booking not found")
        return redirect('home')
    except Exception as e:
        logger.error(f"Error in booking confirmation: {str(e)}")
        messages.error(request, "Error loading booking details")
        return redirect('home')

# Error handling views

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)

# Development/Testing views (remove in production)

def test_calendar_integration(request):
    """Test endpoint for calendar integration (development only)"""
    if not settings.DEBUG:
        raise Http404("Not available in production")
    
    try:
        # Create a test booking for calendar integration
        test_booking = GroupWalk.objects.filter(status='confirmed').first()
        
        if not test_booking:
            return JsonResponse({'error': 'No confirmed bookings available for testing'})
        
        if INTEGRATIONS_AVAILABLE:
            from .calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService()
            
            # Test creating an event
            event_id = calendar_service.create_group_walk_event(test_booking)
            
            return JsonResponse({
                'success': True,
                'message': 'Calendar integration test successful',
                'event_id': event_id,
                'booking_id': test_booking.id,
            })
        else:
            return JsonResponse({'error': 'Calendar integration not available'})
            
    except Exception as e:
        logger.error(f"Calendar integration test failed: {str(e)}")
        return JsonResponse({'error': str(e)})

def test_email_integration(request):
    """Test endpoint for email integration (development only)"""
    if not settings.DEBUG:
        raise Http404("Not available in production")
    
    try:
        # Find a test booking
        test_booking = GroupWalk.objects.filter(status='confirmed').first()
        
        if not test_booking:
            return JsonResponse({'error': 'No confirmed bookings available for testing'})
        
        if INTEGRATIONS_AVAILABLE:
            from .email_service import EmailService
            
            # Test sending confirmation email
            email_sent = EmailService.send_group_walk_confirmation(test_booking)
            
            return JsonResponse({
                'success': email_sent,
                'message': 'Email integration test completed',
                'email_sent': email_sent,
                'booking_id': test_booking.id,
                'customer_email': test_booking.customer_email,
            })
        else:
            return JsonResponse({'error': 'Email integration not available'})
            
    except Exception as e:
        logger.error(f"Email integration test failed: {str(e)}")
        return JsonResponse({'error': str(e)})