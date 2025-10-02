from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import date
from .models import GroupWalk, IndividualWalk, Dog, GroupWalkSlotManager, BookingSettings

@admin.register(BookingSettings)
class BookingSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Weekend Bookings', {
            'fields': ('allow_weekend_bookings',),
            'description': 'control whether customers can book walks on Saturdays and Sundays'
        }),
        ('Capacity Settings', {
            'fields': ('max_dogs_per_booking',),
            'description': 'Maximum number of dogs allowed per group walk booking'
        }),
        ('Time Slot Settings', {
            'fields': ('allow_evening_slot',),
            'description': 'Allow bookings for the 6:00 PM - 8:00 PM evening time slot'
        }),
    )

    list_display = ['__str__', 'allow_weekend_bookings', 'max_dogs_per_booking', 'allow_evening_slot', 'updated_at']

    def has_add_permission(self, request):
        # Prevent adding multiple settings instances
        return not BookingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settigns instance
        return False

@admin.register(GroupWalk)
class GroupWalkAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'booking_date', 'time_slot', 'number_of_dogs', 'status', 'created_at']
    list_filter = ['booking_date', 'time_slot', 'status']
    search_fields = ['customer_name', 'customer_email']
    readonly_fields = ['calendar_event_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_postcode')
        }),
        ('Booking Details', {
            'fields': ('booking_date', 'time_slot', 'number_of_dogs', 'status')
        }),
        ('System Information', {
            'fields': ('calendar_event_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(IndividualWalk)
class IndividualWalkAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'preferred_date', 'preferred_time', 'status', 'created_at']
    list_filter = ['status', 'preferred_date']
    search_fields = ['customer_name', 'customer_email']
    readonly_fields = ['calendar_event_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_postcode')
        }),
        ('Walk Request Details', {
            'fields': ('preferred_date', 'preferred_time', 'reason_for_individual', 'number_of_dogs', 'status')
        }),
        ('Admin Response', {
            'fields': ('admin_response', 'confirmed_date', 'confirmed_time'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('calendar_event_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ['name', 'breed', 'age', 'get_booking_customer', 'good_with_other_dogs']
    list_filter = ['breed', 'good_with_other_dogs', 'age']
    search_fields = ['name', 'breed', 'group_walk__customer_name', 'individual_walk__customer_name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'breed', 'age')
        }),
        ('Health & Behavior', {
            'fields': ('allergies', 'special_instructions', 'good_with_other_dogs', 'behavioral_notes')
        }),
        ('Veterinary Information', {
            'fields': ('vet_name', 'vet_phone', 'vet_address')
        }),
        ('Booking Association', {
            'fields': ('group_walk', 'individual_walk'),
            'classes': ('collapse',)
        })
    )
    
    def get_booking_customer(self, obj):
        if obj.group_walk:
            return f"{obj.group_walk.customer_name} (Group)"
        elif obj.individual_walk:
            return f"{obj.individual_walk.customer_name} (Individual)"
        return "No booking"
    get_booking_customer.short_description = 'Customer'

@admin.register(GroupWalkSlotManager)
class GroupWalkSlotManagerAdmin(admin.ModelAdmin):
    list_display = ['date', 'get_availability_status', 'get_bookings_count', 'get_capacity_info', 'notes_preview']
    list_filter = ['date', 'morning_slot_available', 'afternoon_slot_available', 'evening_slot_available']
    search_fields = ['date', 'notes']
    date_hierarchy = 'date'
    ordering = ['date']

    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Slot Availability', {
            'fields': (
                ('morning_slot_available', 'morning_slot_capacity'),
                ('afternoon_slot_available', 'afternoon_slot_capacity'),
                ('evening_slot_available', 'evening_slot_capacity')
            ),
            'description': 'Control which time slots are available for booking on this date.'
        }),
        ('Notes', {
            'fields': ('notes',),
            'description': 'Internal notes about why slots are unavailable (holiday, sick day, etc.)'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_availability_status(self, obj):
        """ Show availablity status with color coding """
        available_slots = []
        if obj.morning_slot_available:
            available_slots.append('Morning')
        if obj.afternoon_slot_available:
            available_slots.append('Afternoon')
        if obj.evening_slot_available:
            available_slots.append('Evening')

        if not available_slots:
                return format_html('<span style="color: red; font-weight: bold;">❌ All Unavailable</span>')
        elif len(available_slots) == 3:
            return format_html('<span style="color: green; font-weight: bold;">✅ All Available</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ Partial: {}</span>', ', '.join(available_slots))

    get_availability_status.short_description = 'Availability Status'

    def get_bookings_count(self, obj):
        """ Show current bookings for this date """
        morning_count = obj.morning_bookings_count
        afternoon_count = obj.afternoon_bookings_count
        evening_count = obj.evening_bookings_count

        total_bookings = morning_count + afternoon_count + evening_count

        if total_bookings == 0:
            return 'No bookings'
        
        return f"M:{morning_count} | A:{afternoon_count} | E:{evening_count} ({total_bookings} total)"

    get_bookings_count.short_description = 'Current Bookings'

    def get_capacity_info(self, obj):
        """ Show capacity information """
        return f"M:{obj.morning_slot_capacity} | A:{obj.afternoon_slot_capacity} | E:{obj.evening_slot_capacity}"

    get_capacity_info.short_description = 'Capacity (M|A|E)'

    def notes_preview(self, obj):
        """ Show preview of notes """
        if obj.notes:
            return obj.notes[:50] + "..." if len(obj.notes) > 50 else obj.notes
        return "-"

    notes_preview.short_description = 'Notes'

    def save_model(self, request, obj, form, change):
        """ Handle booking cancellations when slots are made unavailable """
        if change: #Only for existing objects
            # Get the original object to compare changes
            original = GroupWalkSlotManager.objects.get(pk=obj.pk)

            # check what slots were disabled
            cancelled_slots = []
            if original.morning_slot_available and not obj.morning_slot_available:
                cancelled_slots.append('10:00-12:00')
            if original.afternoon_slot_available and not obj.afternoon_slot_available:
                cancelled_slots.append('14:00-16:00')
            if original.evening_slot_available and not obj.evening_slot_available:
                cancelled_slots.append('18:00-20:00')
            
            # Cancel existing bookings for disabled slots
            if cancelled_slots:
                from django.contrib import messages
                from .utils import cancel_bookings_for_unavailable_slots

                cancelled_count = cancel_bookings_for_unavailable_slots(obj.date, cancelled_slots, obj.notes or "Date marked unavailable by admin")

                if cancelled_count > 0:
                    messages.warning(
                        request,
                        f"⚠️ {cancelled_count} existing booking(s) were automatically cancelled and customers have been notified by email."
                    )
        super().save_model(request, obj, form, change)

# Customize the admin site
admin.site.site_header = "Canine Compadre Administration"
admin.site.site_title = "Canine Compadre Admin"
admin.site.index_title = "Welcome to Canine Compadre Administartion"