from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, timedelta
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class BaseBooking(models.Model):
    """Abstract base model for common booking fields."""

    # Customer Details
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()
    customer_postcode = models.CharField(
        max_length=20, 
        help_text="We serve within 10 miles of Croyde, North Devon (EX31-EX34 postcodes)"
    )

    # Booking Details
    number_of_dogs = models.IntegerField(validators=[MinValueValidator(1)])

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
    
    def clean_postcode(self):
        """Validate postcode is in service area"""
        if self.customer_postcode:
            postcode = self.customer_postcode.upper().replace(' ', '')
            postcode_area = postcode[:4] if len(postcode) >= 4 else postcode[:3]
            
            allowed_areas = ['EX31', 'EX32', 'EX33', 'EX34']
            if not any(postcode_area.startswith(area) for area in allowed_areas):
                raise ValidationError(
                    f"Sorry, we don't serve the {postcode_area} area. "
                    f"Our service covers: {', '.join(allowed_areas)} (within 10 miles of Croyde, North Devon)"
                )
    
    def clean(self):
        super().clean()
        self.clean_postcode()

class BookingSettings(models.Model):
    """ Site-wide booking configuration settings """

    # Weekend settings
    allow_weekend_bookings = models.BooleanField(
        default = True,
        help_text = "Allow bookings on Saturdays and Sundays"
    )

    # Number of dogs per walk settings
    max_dogs_per_booking = models.IntegerField(
        default = 4,
        validators = [MinValueValidator(1), MaxValueValidator(6)],
        help_text = "Maximum dogs allowed per group walk booking." 
    )

    # Evening group slot settings
    allow_evening_slot = models.BooleanField(
        default = True,
        help_text = "Allow bookings for 6:00 PM - 8:00PM evening slot."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Booking Settings"
        verbose_name_plural = "Booking Settings"
    
    def __Str__(self):
        return "Booking Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """ Get or create the singleton seetings instance """
        settings, created = cls.objects.get_or_create(pk=1)
        return settings 

class GroupWalk(BaseBooking):
    # UPDATED TIME SLOT CHOICES - New times as requested
    TIME_SLOT_CHOICES = [
        ('09:30-11:30', '09:30 AM - 11:30 PM'),
        ('14:00-16:00', '2:00 PM - 4:00 PM'),
        ('18:00-20:00', '6:00 PM - 8:00 PM'),  # NEW EVENING SLOT
    ]

    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    booking_date = models.DateField()
    time_slot = models.CharField(max_length=30, choices=TIME_SLOT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')

    # Override number_of_dogs validation - individual bookings can be 1-4 dogs, group limit is 4 total
    number_of_dogs = models.IntegerField(validators=[MinValueValidator(1)])

    # Google Calendar Event ID (for integration)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    # Simple batch ID to group multiple bookings
    batch_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Groups multiple bookings made together" 
    )

    class Meta:
        ordering = ['-booking_date', 'time_slot']
        verbose_name = "Group Walk Booking"
        verbose_name_plural = "Group Walk Bookings"

    def __str__(self):
        return f"{self.customer_name} - Group Walk - {self.booking_date} {self.get_time_slot_display()}"
    
    def save(self, *args, **kwargs):
        # Get booking settings for validation
        booking_settings = BookingSettings.get_settings()

        # Validate number of dogs against settings
        if self.number_of_dogs > booking_settings.max_dogs_per_booking:
            raise ValidationError(
                f"Maximum {booking_settings.max_dogs_per_booking} dogs allowed per booking."
            )

        # Validate booking date
        if self.booking_date and self.booking_date <= date.today():
            raise ValidationError("Cannot book walks for past dates.")
        
        # Auto-confirm group walks if there's space
        if not self.pk:
            available_spots = self.get_available_spots_for_slot()
            if self.number_of_dogs <= available_spots:
                self.status = 'confirmed'
            else:
                raise ValidationError(
                    f"Not enough space available. Only {available_spots} spots remaining "
                    f"for {self.get_time_slot_display()} on {self.booking_date}. "
                    f"You're trying to book {self.number_of_dogs} dog{'s' if self.number_of_dogs > 1 else ''}."
                )
        
        super().save(*args, **kwargs)
        
        # Create calendar event after saving if this is a new confirmed booking
        #if not kwargs.get('update_fields') and self.status == 'confirmed' and not self.calendar_event_id:
        #    self.create_calendar_event()
    
    def get_available_spots_for_slot(self):
        """Get available spots for this specific date/time slot"""
        total_booked = GroupWalk.objects.filter(
            booking_date=self.booking_date,
            time_slot=self.time_slot,
            status='confirmed',
        ).exclude(pk=self.pk if self.pk else None).aggregate(
            total=models.Sum('number_of_dogs')
        )['total'] or 0

        return 4 - total_booked
    
    def create_calendar_event(self):
        """Create Google Calendar event for this booking"""
        try:
            from .calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService()
            event_id = calendar_service.create_group_walk_event(self)
            
            if event_id:
                self.calendar_event_id = event_id
                GroupWalk.objects.filter(pk=self.pk).update(calendar_event_id=event_id)
                logger.info(f"Calendar event created for group walk booking {self.pk}: {event_id}")
            else:
                logger.warning(f"Failed to create calendar event for group walk booking {self.pk}")
                
        except Exception as e:
            logger.error(f"Error creating calendar event for group walk booking {self.pk}: {str(e)}")
    
    def update_calendar_event(self):
        """Update existing calendar event"""
        if self.calendar_event_id:
            try:
                from .calendar_service import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                updated_event_id = calendar_service.update_event(self.calendar_event_id, self)
                
                if updated_event_id:
                    logger.info(f"Calendar event updated for group walk booking {self.pk}: {updated_event_id}")
                else:
                    logger.warning(f"Failed to update calendar event for group walk booking {self.pk}")
                    
            except Exception as e:
                logger.error(f"Error updating calendar event for group walk booking {self.pk}: {str(e)}")
    
    def delete_calendar_event(self):
        """Delete calendar event when booking is cancelled"""
        if self.calendar_event_id:
            try:
                from .calendar_service import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                deleted = calendar_service.delete_event(self.calendar_event_id)
                
                if deleted:
                    self.calendar_event_id = None
                    GroupWalk.objects.filter(pk=self.pk).update(calendar_event_id=None)
                    logger.info(f"Calendar event deleted for group walk booking {self.pk}")
                else:
                    logger.warning(f"Failed to delete calendar event for group walk booking {self.pk}")
                    
            except Exception as e:
                logger.error(f"Error deleting calendar event for group walk booking {self.pk}: {str(e)}")
    
    def cancel(self, reason=""):
        """Cancel the booking and remove calendar event"""
        self.status = 'cancelled'
        self.delete_calendar_event()
        self.save()
        logger.info(f"Group walk booking {self.pk} cancelled. Reason: {reason}")
    
    @classmethod
    def get_available_slots(cls, days_ahead=180, required_dogs=1):
        """Get all available slots for the next x days that can accommodate required_dogs"""
        available_slots = []
        start_date = date.today() + timedelta(days=1)  # Start from tomorrow

        # Get booking settings
        booking_settings = BookingSettings.get_settings()

        for i in range(days_ahead):
            check_date = start_date + timedelta(days=i)

            if not booking_settings.allow_weekend_bookings and check_date.weekday() >= 5:
                continue
            
            # Skip if this date has slot manager restrictions
            slot_manager = GroupWalkSlotManager.objects.filter(date=check_date).first()

            for time_slot, time_display in cls.TIME_SLOT_CHOICES:
                # Filter out evening slot if disabled in settings
                if not booking_settings.allow_evening_slot and time_slot == '18:00-20:00':
                    continue

                # Check if slot is available via slot manager
                if slot_manager:
                    if time_slot == '09:30-11:30' and not slot_manager.morning_slot_available:
                        continue
                    if time_slot == '14:00-16:00' and not slot_manager.afternoon_slot_available:
                        continue
                    if time_slot == '18:00-20:00' and not slot_manager.evening_slot_available:
                        continue
                    
                    # Use custom capacity if set
                    if time_slot == '09:30-11:30':
                        max_capacity = slot_manager.morning_slot_capacity
                    elif time_slot == '14:00-16:00':
                        max_capacity = slot_manager.afternoon_slot_capacity
                    else:  # evening slot
                        max_capacity = slot_manager.evening_slot_capacity
                else:
                    max_capacity = booking_settings.max_dogs_per_booking

                # Calculate current bookings
                total_booked = cls.objects.filter(
                    booking_date=check_date,
                    time_slot=time_slot,
                    status='confirmed'
                ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0

                available_spots = max_capacity - total_booked

                # Only include if can accommodate the required number of dogs
                if available_spots >= required_dogs:
                    available_slots.append({
                        'date': check_date,
                        'time_slot': time_slot,
                        'time_display': time_display,
                        'available_spots': available_spots,
                        'can_book': True,
                        'is_full': False,
                    })
                
        return available_slots

    @classmethod
    def get_batch_bookings(cls, batch_id):
        """ Get all bookings in the same batch """
        return cls.objects.filter(batch_id=batch_id).order_by('booking_date', 'time_slot')
    
    @property
    def is_part_of_batch(self):
        """ Check if the booking is part of multi-booking """
        return bool(self.batch_id)
    
    @property
    def batch_size(self):
        """ Get total number of bookings in this batch """
        if not self.batch_id:
            return 1
        return GroupWalk.objects.filter(batch_id=self.batch_id).count()
    
    @property
    def total_dogs_in_slot(self):
        """Get total number of dogs booked for this time slot"""
        return GroupWalk.objects.filter(
            booking_date=self.booking_date,
            time_slot=self.time_slot,
            status='confirmed'
        ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0
    
    @property
    def dog_names(self):
        """Get comma-separated list of dog names for this booking"""
        return ', '.join([dog.name for dog in self.dogs.all()])


class IndividualWalk(BaseBooking):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    # UPDATED restricted time slots for individual walks (new group walk times + 1 hour buffer)
    RESTRICTED_TIME_RANGES = [
        ('08:30-12:30', '8:30 AM - 12:30 PM (Group Walk + buffer)'),    # 9:30-11:30 + 1hr buffer each side
        ('13:00-17:00', '1:00 PM - 5:00 PM (Group Walk + buffer)'),    # 14-16 + 1hr buffer each side  
        ('17:00-21:00', '5:00 PM - 9:00 PM (Group Walk + buffer)'),    # 18-20 + 1hr buffer each side
    ]

    preferred_date = models.DateField()
    preferred_time = models.CharField(
        max_length=100,
        help_text="Preferred time (Note: 8.30AM-12.30PM, 1PM-5PM and 5PM-9PM are not available due to group walks)"
    )
    reason_for_individual = models.TextField(
        help_text="Why does your dog need to be walked alone? (In training, non-sociable, etc.)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Admin response fields
    admin_response = models.TextField(blank=True, null=True, help_text="Response to customer")
    confirmed_date = models.DateField(blank=True, null=True)
    confirmed_time = models.CharField(max_length=100, blank=True, null=True)

    # Google Calendar Event ID (for approved bookings)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Individual Walk Request'
        verbose_name_plural = 'Individual Walk Requests'
    
    def __str__(self):
        return f"{self.customer_name} - Individual Walk - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Validate preferred date
        if self.preferred_date and self.preferred_date <= date.today():
            raise ValidationError("Cannot request walks for past dates.")
        
        old_status = None
        if self.pk:
            old_instance = IndividualWalk.objects.get(pk=self.pk)
            old_status = old_instance.status
        
        super().save(*args, **kwargs)
        
        # Handle status changes
        if old_status != self.status:
            if self.status == 'approved' and not self.calendar_event_id:
                self.create_calendar_event()
            elif self.status in ['rejected', 'cancelled'] and self.calendar_event_id:
                self.delete_calendar_event()
    
    def approve(self, confirmed_date=None, confirmed_time=None, admin_response=""):
        """Approve the individual walk request."""
        self.status = 'approved'
        if confirmed_date:
            self.confirmed_date = confirmed_date
        if confirmed_time:
            self.confirmed_time = confirmed_time
        if admin_response:
            self.admin_response = admin_response
        self.save()
        
        # Send approval email
        try:
            from .email_service import EmailService
            EmailService.send_individual_walk_response(self)
        except Exception as e:
            logger.error(f"Failed to send approval email for individual walk {self.pk}: {str(e)}")

    def reject(self, admin_response=""):
        """Reject the individual walk request"""
        self.status = 'rejected'
        if admin_response:
            self.admin_response = admin_response
        self.save()
        
        # Send rejection email
        try:
            from .email_service import EmailService
            EmailService.send_individual_walk_response(self)
        except Exception as e:
            logger.error(f"Failed to send rejection email for individual walk {self.pk}: {str(e)}")
    
    def create_calendar_event(self):
        """Create Google Calendar event for approved individual walk"""
        if self.status == 'approved' and self.confirmed_date and self.confirmed_time:
            try:
                from .calendar_service import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                event_id = calendar_service.create_individual_walk_event(self)
                
                if event_id:
                    self.calendar_event_id = event_id
                    IndividualWalk.objects.filter(pk=self.pk).update(calendar_event_id=event_id)
                    logger.info(f"Calendar event created for individual walk {self.pk}: {event_id}")
                else:
                    logger.warning(f"Failed to create calendar event for individual walk {self.pk}")
                    
            except Exception as e:
                logger.error(f"Error creating calendar event for individual walk {self.pk}: {str(e)}")
    
    def update_calendar_event(self):
        """Update existing calendar event"""
        if self.calendar_event_id:
            try:
                from .calendar_service import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                updated_event_id = calendar_service.update_event(self.calendar_event_id, self)
                
                if updated_event_id:
                    logger.info(f"Calendar event updated for individual walk {self.pk}: {updated_event_id}")
                else:
                    logger.warning(f"Failed to update calendar event for individual walk {self.pk}")
                    
            except Exception as e:
                logger.error(f"Error updating calendar event for individual walk {self.pk}: {str(e)}")
    
    def delete_calendar_event(self):
        """Delete calendar event when booking is rejected/cancelled"""
        if self.calendar_event_id:
            try:
                from .calendar_service import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                deleted = calendar_service.delete_event(self.calendar_event_id)
                
                if deleted:
                    self.calendar_event_id = None
                    IndividualWalk.objects.filter(pk=self.pk).update(calendar_event_id=None)
                    logger.info(f"Calendar event deleted for individual walk {self.pk}")
                else:
                    logger.warning(f"Failed to delete calendar event for individual walk {self.pk}")
                    
            except Exception as e:
                logger.error(f"Error deleting calendar event for individual walk {self.pk}: {str(e)}")

    def clean(self):
        """Validate that individual walk doesn't conflict with group walk times."""
        super().clean()

        # Check if preferred time conflicts with restricted ranges
        if self.preferred_time:
            preferred_lower = self.preferred_time.lower()
            
            # Skip validation for predefined safe choices
            safe_choices = [
                'early morning', 'late afternoon', 'evening', 'flexible',
                'please suggest', 'let us suggest'
            ]
            
            # If it's a predefined safe choice, don't validate further
            if any(safe_choice in preferred_lower for safe_choice in safe_choices):
                return  # Skip time restriction validation for safe choices

            # Updated validation patterns for new restricted times
            morning_restricted = ['08:', '09:', '10:', '11:', '12:', '8am', '9am', '10am', '11am', '12pm', 'noon', 'midday']
            afternoon_restricted = ['13:', '14:', '15:', '16:', '1pm', '2pm', '3pm', '4pm']
            evening_restricted = ['17:', '18:', '19:', '20:', '5pm', '6pm', '7pm', '8pm']
            
            conflicts = []
            for pattern in morning_restricted:
                if pattern in preferred_lower:
                    conflicts.append("8:30 AM - 12:30 PM")
                    break
            for pattern in afternoon_restricted:
                if pattern in preferred_lower:
                    conflicts.append("1:00 PM - 5:00 PM")
                    break
            for pattern in evening_restricted:
                if pattern in preferred_lower:
                    conflicts.append("5:00 PM - 9:00 PM")
                    break
            
            if conflicts:
                raise ValidationError(
                    f"Individual walks cannot be scheduled during {', '.join(set(conflicts))} "
                    "due to group walk sessions and required buffer time. "
                    "Available times: 6:00-8:00 AM, 9:00 PM onwards, or select 'Flexible'."
                )
    
    @classmethod
    def get_available_time_suggestions(cls):
        """Get suggested available time slots for individual walks"""
        return [
            "6:00 AM - 8:00 AM (Early Morning)",
            "9:00 PM - 11:00 PM (Late Evening)", 
            "Flexible (let us suggest a time)",
            "Early morning (before 9 AM)",
            "Late evening (after 9 PM)"
        ]
    
    @property
    def dog_names(self):
        """Get comma-separated list of dog names for this booking"""
        return ', '.join([dog.name for dog in self.dogs.all()])
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'


# Updated GroupWalkSlotManager to handle the new evening slot
class GroupWalkSlotManager(models.Model):
    """Admin model to manage group walk availability - UPDATED for 3 time slots"""
    date = models.DateField(unique=True)
    morning_slot_available = models.BooleanField(
        default=True, 
        help_text="09:30 AM - 11:30 PM slot available"
    )
    afternoon_slot_available = models.BooleanField(
        default=True, 
        help_text="2:00 PM - 4:00 PM slot available"
    )
    evening_slot_available = models.BooleanField(
        default=True, 
        help_text="6:00 PM - 8:00 PM slot available"
    )

    # Override capacity for specific dates if needed
    morning_slot_capacity = models.IntegerField(
        default=4,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Maximum dogs for morning slot (0-6)"
    )
    afternoon_slot_capacity = models.IntegerField(
        default=4,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Maximum dogs for afternoon slot (0-6)"
    )
    evening_slot_capacity = models.IntegerField(
        default=4,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Maximum dogs for evening slot (0-6)"
    )

    notes = models.TextField(
        blank=True, 
        null=True, 
        help_text="Admin notes for this date (holiday, weather, etc.)"
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name = "Group Walk Slot Manager"
        verbose_name_plural = "Group Walk Slot Managers"
    
    def __str__(self):
        return f"Slots for {self.date.strftime('%A, %B %d, %Y')}"
    
    def clean(self):
        super().clean()
        
        # Validate date is not in the past
        if self.date and self.date < date.today():
            raise ValidationError("Cannot manage slots for past dates.")
        
        # Validate capacities
        if self.morning_slot_capacity < 0:
            raise ValidationError("Morning slot capacity cannot be negative.")
        if self.afternoon_slot_capacity < 0:
            raise ValidationError("Afternoon slot capacity cannot be negative.")
        if self.evening_slot_capacity < 0:
            raise ValidationError("Evening slot capacity cannot be negative.")
    
    @property
    def morning_bookings_count(self):
        """Get number of dogs booked for morning slot"""
        return GroupWalk.objects.filter(
            booking_date=self.date,
            time_slot='09:30-11:30',
            status='confirmed'
        ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0
    
    @property
    def afternoon_bookings_count(self):
        """Get number of dogs booked for afternoon slot"""
        return GroupWalk.objects.filter(
            booking_date=self.date,
            time_slot='14:00-16:00',
            status='confirmed'
        ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0
    
    @property
    def evening_bookings_count(self):
        """Get number of dogs booked for evening slot"""
        return GroupWalk.objects.filter(
            booking_date=self.date,
            time_slot='18:00-20:00',
            status='confirmed'
        ).aggregate(total=models.Sum('number_of_dogs'))['total'] or 0
    
    @property
    def morning_available_spots(self):
        """Get available spots for morning slot"""
        if not self.morning_slot_available:
            return 0
        return max(0, self.morning_slot_capacity - self.morning_bookings_count)
    
    @property
    def afternoon_available_spots(self):
        """Get available spots for afternoon slot"""
        if not self.afternoon_slot_available:
            return 0
        return max(0, self.afternoon_slot_capacity - self.afternoon_bookings_count)
    
    @property
    def evening_available_spots(self):
        """Get available spots for evening slot"""
        if not self.evening_slot_available:
            return 0
        return max(0, self.evening_slot_capacity - self.evening_bookings_count)
    
    def is_fully_booked(self):
        """Check if all slots are fully booked"""
        return (
            (not self.morning_slot_available or self.morning_available_spots == 0) and
            (not self.afternoon_slot_available or self.afternoon_available_spots == 0) and
            (not self.evening_slot_available or self.evening_available_spots == 0)
        )
    
    @classmethod
    def get_or_create_for_date(cls, check_date):
        """Get or create slot manager for a specific date"""
        slot_manager, created = cls.objects.get_or_create(
            date=check_date,
            defaults={
                'morning_slot_available': True,
                'afternoon_slot_available': True,
                'evening_slot_available': True,
                'morning_slot_capacity': 4,
                'afternoon_slot_capacity': 4,
                'evening_slot_capacity': 4,
            }
        )
        return slot_manager, created


# Rest of the models remain the same...
class Dog(models.Model):
    """Dog details - can belong to either group or individual walk"""

    # Link to either type of booking 
    group_walk = models.ForeignKey(
        GroupWalk, 
        on_delete=models.CASCADE, 
        related_name='dogs', 
        blank=True, 
        null=True
    )
    individual_walk = models.ForeignKey(
        IndividualWalk, 
        on_delete=models.CASCADE, 
        related_name='dogs', 
        blank=True, 
        null=True
    )

    # Dog details
    name = models.CharField(max_length=50)
    breed = models.CharField(max_length=100)
    age = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(30)])

    # Health and Safety
    allergies = models.TextField(
        blank=True, 
        null=True, 
        help_text="Any allergies or health concerns"
    )
    special_instructions = models.TextField(
        blank=True, 
        null=True, 
        help_text="Special care instructions"
    )

    # Behavior (especially important for group walks)
    good_with_other_dogs = models.BooleanField(
        default=True,
        help_text="Important for group walks - uncheck if your dog has issues with other dogs"
    )
    behavioral_notes = models.TextField(
        blank=True, 
        null=True, 
        help_text="Any behavioral concerns, triggers, or special handling requirements"
    )

    # Vet Information
    vet_name = models.CharField(
        max_length=100, 
        help_text="Name of your vet practice"
    )
    vet_phone = models.CharField(
        max_length=20, 
        help_text="Vet practice phone number"
    )
    vet_address = models.TextField(
        help_text="Vet practice address"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        booking = self.group_walk or self.individual_walk
        return f"{self.name} ({self.breed}) - {booking.customer_name if booking else 'No booking'}"

    def clean(self):
        # Ensure dog belongs to exactly one type of booking
        if bool(self.group_walk) == bool(self.individual_walk):
            raise ValidationError("Dog must belong to exactly one booking type.")
        
        # Validate age
        if self.age is not None and (self.age < 0 or self.age > 30):
            raise ValidationError("Dog age must be between 0 and 30 years.")
        
        # Validate required vet information
        if not self.vet_name:
            raise ValidationError("Vet practice name is required.")
        if not self.vet_phone:
            raise ValidationError("Vet phone number is required.")
        if not self.vet_address:
            raise ValidationError("Vet practice address is required.")
    
    @property
    def booking(self):
        """Get the associated booking (group or individual)"""
        return self.group_walk or self.individual_walk
    
    @property
    def booking_type(self):
        """Get the type of booking this dog belongs to"""
        if self.group_walk:
            return 'group'
        elif self.individual_walk:
            return 'individual'
        return None
    
    @property
    def age_display(self):
        """Display age with appropriate unit"""
        if self.age == 1:
            return "1 year old"
        elif self.age == 0:
            return "Under 1 year old"
        else:
            return f"{self.age} years old"


@receiver(post_delete, sender=GroupWalk)
def delete_group_walk_calendar_event(sender, instance, **kwargs):
    """Delete calendar event when GroupWalk is deleted"""
    if instance.calendar_event_id:
        try:
            from .calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService()
            deleted = calendar_service.delete_event(instance.calendar_event_id)
            if deleted:
                logger.info(f"Calendar event deleted for group walk booking {instance.id}")
            else:
                logger.warning(f"Failed to delete calendar event for group walk booking {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting calendar event for group walk booking {instance.id}: {str(e)}")

@receiver(post_delete, sender=IndividualWalk)
def delete_individual_walk_calendar_event(sender, instance, **kwargs):
    """Delete calendar event when IndividualWalk is deleted"""
    if instance.calendar_event_id:
        try:
            from .calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService()
            deleted = calendar_service.delete_event(instance.calendar_event_id)
            if deleted:
                logger.info(f"Calendar event deleted for individual walk booking {instance.id}")
            else:
                logger.warning(f"Failed to delete calendar event for individual walk booking {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting calendar event for individual walk booking {instance.id}: {str(e)}")