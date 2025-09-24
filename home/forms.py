from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import GroupWalk, IndividualWalk, Dog
from datetime import date, timedelta

# Allowed postcode areas within 10 miles of Croyde, North Devon
ALLOWED_POSTCODE_AREAS = [
    'EX33',  # Croyde area
    'EX34',  # Nearby areas
    'EX31',  # Braunton, etc.
    'EX32',  # Barnstaple area
    # Add more as needed based on your client's actual service area
]

class GroupWalkForm(forms.ModelForm):
    class Meta:
        model = GroupWalk
        fields = ['customer_name', 'customer_email', 'customer_phone', 'customer_address', 
                 'customer_postcode', 'booking_date', 'time_slot', 'number_of_dogs']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '07123 456789'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your full address for pickup/dropoff'}),
            'customer_postcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EX33 1AA', 'style': 'text-transform: uppercase;'}),
            'booking_date': forms.DateInput(attrs={'class': 'form-control', 'id': 'booking-date', 'readonly': True}),
            'time_slot': forms.Select(attrs={'class': 'form-control', 'id': 'time-slot', 'disabled': True}),
            'number_of_dogs': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4, 'id': 'num-dogs'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make date and time_slot readonly - they'll be set via JavaScript from calendar
        self.fields['booking_date'].widget.attrs['readonly'] = True
        self.fields['time_slot'].widget.attrs['disabled'] = True
        
        # Set minimum date to tomorrow
        self.fields['booking_date'].widget.attrs['min'] = (date.today() + timedelta(days=1)).isoformat()
        
        # Updated help text for new time slots
        self.fields['number_of_dogs'].help_text = "Maximum 4 dogs per individual booking (group walk session limited to 4 dogs total)"
        self.fields['booking_date'].help_text = "Select from available dates in the calendar"
        self.fields['time_slot'].help_text = "Available slots: 09:30 AM - 11:30 AM, 2:00 PM - 4:00 PM, or 6:00 PM - 8:00 PM"
        self.fields['customer_postcode'].help_text = f"We serve: {', '.join(ALLOWED_POSTCODE_AREAS)} (within 10 miles of Croyde, North Devon)"
    
    def clean_booking_date(self):
        booking_date = self.cleaned_data.get('booking_date')
        if booking_date and booking_date <= date.today():
            raise ValidationError("Cannot book walks for past dates.")
        return booking_date
    
    def clean_customer_postcode(self):
        postcode = self.cleaned_data.get('customer_postcode')
        if postcode:
            postcode = postcode.upper().replace(' ', '')
            # Add space if missing (e.g., EX331AA -> EX33 1AA)
            if len(postcode) >= 5 and ' ' not in postcode:
                postcode = postcode[:-3] + ' ' + postcode[-3:]
            
            # Extract postcode area (e.g., EX33 from EX33 1AA)
            postcode_area = postcode.split()[0] if ' ' in postcode else postcode[:4]
            
            if postcode_area not in ALLOWED_POSTCODE_AREAS:
                raise ValidationError(
                    f"Sorry, we don't currently serve the {postcode_area} area. "
                    f"Our service area covers: {', '.join(ALLOWED_POSTCODE_AREAS)} "
                    f"(within 10 miles of Croyde, North Devon). "
                    f"Please contact us if you think this is an error."
                )
        
        return postcode
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        time_slot = cleaned_data.get('time_slot')
        number_of_dogs = cleaned_data.get('number_of_dogs')
        
        if booking_date and time_slot and number_of_dogs:
            # Check if there are enough spots available
            existing_bookings = GroupWalk.objects.filter(
                booking_date=booking_date,
                time_slot=time_slot,
                status='confirmed'
            )
            
            # Exclude current instance if editing
            if self.instance and self.instance.pk:
                existing_bookings = existing_bookings.exclude(pk=self.instance.pk)
            
            total_booked = sum(booking.number_of_dogs for booking in existing_bookings)
            available_spots = 4 - total_booked
            
            if number_of_dogs > available_spots:
                raise ValidationError(
                    f"Not enough space available. Only {available_spots} spots remaining for this time slot."
                )
        
        return cleaned_data


class IndividualWalkForm(forms.ModelForm):
    # Updated choice field for new available time preferences
    preferred_time_choice = forms.ChoiceField(
        choices=[
            ('', 'Select a time preference...'),
            ('early_morning', 'Early Morning (6:00 AM - 8:30 AM)'),  # Updated to avoid 9-1 restriction
            ('late_evening', 'Late Evening (9:00 PM - 11:00 PM)'),   # New option after 9PM
            ('flexible', 'Flexible - let us suggest a time'),
            ('custom', 'Other specific time (please specify below)'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'time-choice'}),
        label="Preferred Time Slot"
    )
    
    class Meta:
        model = IndividualWalk
        fields = ['customer_name', 'customer_email', 'customer_phone', 'customer_address',
                 'customer_postcode', 'preferred_date', 'preferred_time_choice', 'preferred_time', 'reason_for_individual', 'number_of_dogs']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '07123 456789'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your full address for pickup/dropoff'}),
            'customer_postcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EX33 1AA', 'style': 'text-transform: uppercase;'}),
            'preferred_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preferred_time': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Specify your preferred time',
                'id': 'custom-time-input',
                'style': 'display: none;'  # Hidden by default
            }),
            'reason_for_individual': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Please explain why your dog needs an individual walk (e.g., anxiety around other dogs, in training, medical needs, behavioral concerns, etc.)'
            }),
            'number_of_dogs': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set minimum date to tomorrow
        self.fields['preferred_date'].widget.attrs['min'] = (date.today() + timedelta(days=1)).isoformat()
        
        # Updated help text about restricted times for new schedule
        self.fields['preferred_time'].help_text = (
            "⚠️ RESTRICTED TIMES: 8:30 AM - 12:30 PM, 1:00 PM - 5:00 PM, and 5:00 PM - 9:00 PM are not available "
            "due to group walk sessions and buffer time. Available: 7:00-9:00 AM or after 9:00 PM"
        )
        
        # Add labels and help text
        self.fields['preferred_date'].help_text = "When would you like the individual walk?"
        self.fields['number_of_dogs'].help_text = "How many dogs need individual walking?"
        self.fields['reason_for_individual'].label = "Why does your dog need an individual walk?"
        self.fields['customer_postcode'].help_text = f"We serve: {', '.join(ALLOWED_POSTCODE_AREAS)} (within 10 miles of Croyde, North Devon)"
    
    def clean_preferred_date(self):
        preferred_date = self.cleaned_data.get('preferred_date')
        if preferred_date and preferred_date <= date.today():
            raise ValidationError("Cannot request walks for past dates.")
        
        # NEW: Check if date is marked unavailable
        if preferred_date:
            from .models import GroupWalkSlotManager
            
            try:
                slot_manager = GroupWalkSlotManager.objects.get(date=preferred_date)
                # If all slots are unavailable, block the request
                if (not slot_manager.morning_slot_available and 
                    not slot_manager.afternoon_slot_available and 
                    not slot_manager.evening_slot_available):
                    raise ValidationError(
                        f"Sorry, {preferred_date.strftime('%B %d, %Y')} is not available for walks. "
                        f"Reason: {slot_manager.notes or 'Date marked unavailable'}. "
                        f"Please choose a different date."
                    )
            except GroupWalkSlotManager.DoesNotExist:
                # Date is available (no slot manager = available)
                pass
        
        return preferred_date
    
    def clean_customer_postcode(self):
        postcode = self.cleaned_data.get('customer_postcode')
        if postcode:
            postcode = postcode.upper().replace(' ', '')
            # Add space if missing (e.g., EX331AA -> EX33 1AA)
            if len(postcode) >= 5 and ' ' not in postcode:
                postcode = postcode[:-3] + ' ' + postcode[-3:]
            
            # Extract postcode area (e.g., EX33 from EX33 1AA)
            postcode_area = postcode.split()[0] if ' ' in postcode else postcode[:4]
            
            if postcode_area not in ALLOWED_POSTCODE_AREAS:
                raise ValidationError(
                    f"Sorry, we don't currently serve the {postcode_area} area. "
                    f"Our service area covers: {', '.join(ALLOWED_POSTCODE_AREAS)} "
                    f"(within 10 miles of Croyde, North Devon). "
                    f"Please contact us if you think this is an error."
                )
        
        return postcode
    
    def clean_preferred_time(self):
        preferred_time_choice = self.cleaned_data.get('preferred_time_choice')
        preferred_time = self.cleaned_data.get('preferred_time')
        
        # Map choices to actual text
        if preferred_time_choice == 'early_morning':
            return 'Early Morning (6:00 AM - 8:00 AM)'
        elif preferred_time_choice == 'late_evening':
            return 'Late Evening (9:00 PM - 11:00 PM)'
        elif preferred_time_choice == 'flexible':
            return 'Flexible - please suggest a suitable time'
        elif preferred_time_choice == 'custom':
            if not preferred_time:
                raise ValidationError("Please specify your preferred time.")
            return preferred_time
        elif preferred_time:
            return preferred_time
        
        raise ValidationError("Please select a time preference.")
    
    def clean(self):
        cleaned_data = super().clean()
        preferred_time = cleaned_data.get('preferred_time', '')
        
        # Only validate time if it's a custom time entry, not predefined choices
        if preferred_time and not any(x in preferred_time.lower() for x in [
            'early morning', 'late evening', 'flexible'
        ]):
            # Check for restricted time patterns only for custom times
            preferred_lower = preferred_time.lower()
            
            # Updated restricted patterns for new schedule
            restricted_patterns = {
                # Morning restricted period (9 AM - 1 PM)
                'morning_restricted': ['08:', '09:', '10:', '11:', '12:', '8am', '9am', '10am', '11am', '12pm', 'noon', 'midday'],
                # Afternoon restricted period (1 PM - 5 PM)  
                'afternoon_restricted': ['13:', '14:', '15:', '16:', '1pm', '2pm', '3pm', '4pm'],
                # Evening restricted period (5 PM - 9 PM)
                'evening_restricted': ['17:', '18:', '19:', '20:', '5pm', '6pm', '7pm', '8pm']
            }
            
            # Check if any restricted patterns are found
            found_restricted = []
            for period, patterns in restricted_patterns.items():
                if any(pattern in preferred_lower for pattern in patterns):
                    if period == 'morning_restricted':
                        found_restricted.append("8:30 AM - 12:30 PM")
                    elif period == 'afternoon_restricted':
                        found_restricted.append("1:00 PM - 5:00 PM")
                    elif period == 'evening_restricted':
                        found_restricted.append("5:00 PM - 9:00 PM")
            
            if found_restricted:
                raise ValidationError(
                    f"Individual walks cannot be scheduled during {', '.join(set(found_restricted))} "
                    "due to group walk sessions and buffer time. "
                    "Available times: 6:00-8:00 AM, after 8:00 PM, or select 'Flexible'."
                )
        
        return cleaned_data


class DogForm(forms.ModelForm):
    class Meta:
        model = Dog
        fields = ['name', 'breed', 'age', 'allergies', 'special_instructions', 
                 'good_with_other_dogs', 'behavioral_notes', 'vet_name', 'vet_phone', 'vet_address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Dog's name"}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Labrador, Mixed breed'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 30, 'placeholder': 'Age in years'}),
            'allergies': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Any allergies, medical conditions, or health concerns'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Special care instructions, feeding requirements, etc.'
            }),
            'good_with_other_dogs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'behavioral_notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Any behavioral concerns, triggers, or special handling notes'
            }),
            'vet_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Croyde Veterinary Surgery'}),
            'vet_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01271 890123'}),
            'vet_address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Full vet practice address'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for important fields
        self.fields['good_with_other_dogs'].help_text = "Important for group walks - uncheck if your dog has issues with other dogs"
        self.fields['behavioral_notes'].help_text = "Please mention any behavioral issues, fears, or special handling requirements"
        self.fields['age'].help_text = "Age in years (puppies under 1 year should be noted in special instructions)"
        self.fields['vet_name'].help_text = "Your dog's registered veterinary practice"
        self.fields['vet_phone'].help_text = "Emergency contact number for your vet"
        self.fields['vet_address'].help_text = "Full address of your vet practice"
    
    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age is not None and (age < 0 or age > 30):
            raise ValidationError("Dog age must be between 0 and 30 years.")
        return age
    
    def clean_vet_name(self):
        vet_name = self.cleaned_data.get('vet_name')
        if not vet_name:
            raise ValidationError("Veterinary practice name is required.")
        return vet_name
    
    def clean_vet_phone(self):
        vet_phone = self.cleaned_data.get('vet_phone')
        if not vet_phone:
            raise ValidationError("Veterinary practice phone number is required.")
        return vet_phone
    
    def clean_vet_address(self):
        vet_address = self.cleaned_data.get('vet_address')
        if not vet_address:
            raise ValidationError("Veterinary practice address is required.")
        return vet_address


# Create formsets for handling multiple dogs
GroupWalkDogFormSet = inlineformset_factory(
    GroupWalk, 
    Dog, 
    form=DogForm,
    extra=1,  # Start with 1 empty form
    can_delete=False,  # Don't allow deletion on initial booking
    min_num=1,  # At least 1 dog required
    validate_min=True,
    fields=['name', 'breed', 'age', 'allergies', 'special_instructions', 'good_with_other_dogs', 'behavioral_notes', 'vet_name', 'vet_phone', 'vet_address']
)

IndividualWalkDogFormSet = inlineformset_factory(
    IndividualWalk, 
    Dog, 
    form=DogForm,
    extra=1,  # Start with 1 empty form
    can_delete=False,  # Don't allow deletion on initial booking
    min_num=1,  # At least 1 dog required
    validate_min=True,
    fields=['name', 'breed', 'age', 'allergies', 'special_instructions', 'good_with_other_dogs', 'behavioral_notes', 'vet_name', 'vet_phone', 'vet_address']
)


# Additional utility forms for admin use
class AdminResponseForm(forms.ModelForm):
    """Form for admin to respond to individual walk requests"""
    
    class Meta:
        model = IndividualWalk
        fields = ['status', 'confirmed_date', 'confirmed_time', 'admin_response']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'confirmed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'confirmed_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8:00 AM - 9:00 AM'}),
            'admin_response': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Response to customer (optional - will be included in email if provided)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show relevant status choices for admin
        self.fields['status'].choices = [
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]
        
        # Updated help text for new available times
        self.fields['confirmed_date'].help_text = "Confirmed date for the walk (if approving)"
        self.fields['confirmed_time'].help_text = "Confirmed time slot (if approving) - Available: 6AM-8AM or after 8PM"
        self.fields['admin_response'].help_text = "Optional message to customer (will be emailed)"
    
    def clean_confirmed_date(self):
        confirmed_date = self.cleaned_data.get('confirmed_date')
        status = self.cleaned_data.get('status')
        
        if status == 'approved' and not confirmed_date:
            raise ValidationError("Confirmed date is required when approving a walk.")
        if confirmed_date and confirmed_date <= date.today():
            raise ValidationError("Cannot confirm walks for past dates.")
        return confirmed_date
    
    def clean_confirmed_time(self):
        confirmed_time = self.cleaned_data.get('confirmed_time')
        status = self.cleaned_data.get('status')
        
        if status == 'approved' and not confirmed_time:
            raise ValidationError("Confirmed time is required when approving a walk.")
        return confirmed_time


class GroupWalkSearchForm(forms.Form):
    """Form for searching/filtering group walk bookings"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="From Date"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="To Date"
    )
    time_slot = forms.ChoiceField(
        required=False,
        choices=[('', 'All Time Slots')] + GroupWalk.TIME_SLOT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Time Slot"
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + GroupWalk.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Status"
    )
    customer_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by customer name'}),
        label="Customer Name"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("From date cannot be later than to date.")
        
        return cleaned_data