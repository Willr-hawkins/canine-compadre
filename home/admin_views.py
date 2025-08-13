"""
Custom admin views for managing unavailable dates
"""

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from datetime import date, timedelta
import json

from .models import GroupWalkSlotManager, GroupWalk
from .utils import cancel_bookings_for_unavailable_slots

@staff_member_required
def manage_unavailable_dates(request):
    """
    Main view for managing unavailable dates - shows calendar interface
    """
    
    # Get upcoming unavailable dates
    today = date.today()
    upcoming_unavailable = GroupWalkSlotManager.objects.filter(
        date__gte=today,
    ).exclude(
        morning_slot_available=True,
        afternoon_slot_available=True,
        evening_slot_available=True
    ).order_by('date')[:10]
    
    # Get dates with existing bookings (next 30 days)
    dates_with_bookings = GroupWalk.objects.filter(
        booking_date__gte=today,
        booking_date__lte=today + timedelta(days=30),
        status='confirmed'
    ).values_list('booking_date', flat=True).distinct()
    
    context = {
        'upcoming_unavailable': upcoming_unavailable,
        'dates_with_bookings': list(dates_with_bookings),
        'today': today,
        'title': 'Manage Unavailable Dates',
    }
    
    return render(request, 'admin/manage_unavailable_dates.html', context)

@staff_member_required
@require_POST
def mark_date_unavailable(request):
    """
    AJAX endpoint to mark a date as unavailable
    """
    
    try:
        data = json.loads(request.body)
        selected_date = date.fromisoformat(data['date'])
        reason = data.get('reason', 'Marked unavailable by admin')
        slots_to_disable = data.get('slots', ['morning', 'afternoon', 'evening'])
        
        # Validate date is not in the past
        if selected_date <= date.today():
            return JsonResponse({
                'success': False,
                'error': 'Cannot mark past dates as unavailable'
            })
        
        # Get or create slot manager
        slot_manager, created = GroupWalkSlotManager.objects.get_or_create(
            date=selected_date,
            defaults={
                'morning_slot_available': True,
                'afternoon_slot_available': True,
                'evening_slot_available': True,
                'morning_slot_capacity': 4,
                'afternoon_slot_capacity': 4,
                'evening_slot_capacity': 4,
                'notes': reason,
            }
        )
        
        # Update notes
        if not created:
            slot_manager.notes = reason
        
        # Determine which slots to cancel
        cancelled_slots = []
        
        if 'morning' in slots_to_disable and slot_manager.morning_slot_available:
            slot_manager.morning_slot_available = False
            cancelled_slots.append('10:00-12:00')
        
        if 'afternoon' in slots_to_disable and slot_manager.afternoon_slot_available:
            slot_manager.afternoon_slot_available = False
            cancelled_slots.append('14:00-16:00')
        
        if 'evening' in slots_to_disable and slot_manager.evening_slot_available:
            slot_manager.evening_slot_available = False
            cancelled_slots.append('18:00-20:00')
        
        slot_manager.save()
        
        # Cancel existing bookings and send emails
        cancelled_count = 0
        if cancelled_slots:
            cancelled_count = cancel_bookings_for_unavailable_slots(
                selected_date, 
                cancelled_slots, 
                reason
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Date marked unavailable. {cancelled_count} existing bookings were cancelled and customers notified.',
            'cancelled_count': cancelled_count,
            'date': selected_date.isoformat(),
            'reason': reason
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@staff_member_required
@require_POST
def mark_date_available(request):
    """
    AJAX endpoint to mark a date as available again
    """
    
    try:
        data = json.loads(request.body)
        selected_date = date.fromisoformat(data['date'])
        slots_to_enable = data.get('slots', ['morning', 'afternoon', 'evening'])
        
        # Get slot manager
        try:
            slot_manager = GroupWalkSlotManager.objects.get(date=selected_date)
        except GroupWalkSlotManager.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No slot manager found for this date'
            })
        
        # Enable the specified slots
        if 'morning' in slots_to_enable:
            slot_manager.morning_slot_available = True
        
        if 'afternoon' in slots_to_enable:
            slot_manager.afternoon_slot_available = True
        
        if 'evening' in slots_to_enable:
            slot_manager.evening_slot_available = True
        
        # Clear notes if all slots are now available
        if (slot_manager.morning_slot_available and 
            slot_manager.afternoon_slot_available and 
            slot_manager.evening_slot_available):
            slot_manager.notes = ''
        
        slot_manager.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Date marked as available for booking.',
            'date': selected_date.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@staff_member_required
def get_date_info(request):
    """
    AJAX endpoint to get information about a specific date
    """
    
    try:
        selected_date = date.fromisoformat(request.GET.get('date'))
        
        # Get slot manager info
        try:
            slot_manager = GroupWalkSlotManager.objects.get(date=selected_date)
            availability = {
                'morning': slot_manager.morning_slot_available,
                'afternoon': slot_manager.afternoon_slot_available,
                'evening': slot_manager.evening_slot_available,
                'notes': slot_manager.notes or '',
            }
        except GroupWalkSlotManager.DoesNotExist:
            availability = {
                'morning': True,
                'afternoon': True,
                'evening': True,
                'notes': '',
            }
        
        # Get existing bookings
        bookings = GroupWalk.objects.filter(
            booking_date=selected_date,
            status='confirmed'
        ).select_related().prefetch_related('dogs')
        
        bookings_data = []
        for booking in bookings:
            bookings_data.append({
                'id': booking.id,
                'customer_name': booking.customer_name,
                'customer_email': booking.customer_email,
                'time_slot': booking.get_time_slot_display(),
                'number_of_dogs': booking.number_of_dogs,
                'dog_names': ', '.join([dog.name for dog in booking.dogs.all()]),
            })
        
        return JsonResponse({
            'success': True,
            'availability': availability,
            'bookings': bookings_data,
            'total_bookings': len(bookings_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })