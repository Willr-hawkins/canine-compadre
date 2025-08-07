// booking.js - Complete Booking System JavaScript with Calendar Integration
document.addEventListener('DOMContentLoaded', function() {
    
    // Global variables
    let availabilityData = [];
    let selectedDate = null;
    let selectedTimeSlot = null;
    let currentBookingType = null;
    
    // Main booking elements
    const serviceSelection = document.getElementById('booking-service-selection');
    const backToSelection = document.getElementById('back-to-selection');
    const backBtn = document.getElementById('back-btn');
    const groupForm = document.getElementById('group-booking-form');
    const individualForm = document.getElementById('individual-booking-form');
    const bookingMainContent = document.getElementById('booking-main-content');
    
    // ===========================================
    // SERVICE SELECTION HANDLERS
    // ===========================================
    
    // Handle service type selection
    document.querySelectorAll('.booking-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentBookingType = this.dataset.bookingType;
            showBookingForm(currentBookingType);
        });
    });
    
    // Back button handler
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            goBackToServiceSelection();
        });
    }
    
    function showBookingForm(type) {
        // Hide service selection
        if (serviceSelection) serviceSelection.style.display = 'none';
        if (backToSelection) backToSelection.style.display = 'block';
        
        // Show appropriate form
        if (type === 'group') {
            if (groupForm) groupForm.style.display = 'block';
            if (individualForm) individualForm.style.display = 'none';
            initializeGroupWalkForm();
        } else {
            if (individualForm) individualForm.style.display = 'block';
            if (groupForm) groupForm.style.display = 'none';
            initializeIndividualWalkForm();
        }
    }
    
    function resetBookingSection() {
        console.log('resetBookingSection called');
        
        // First, restore the original booking content by replacing the success message
        if (bookingMainContent) {
            bookingMainContent.innerHTML = `
                <!-- Service Selection Buttons (Initial State) -->
                <div id="booking-service-selection" class="text-center">
                    <div class="row justify-content-center">
                        <div class="col-12 col-md-5 mb-3">
                            <button class="btn btn-outline-primary btn-lg w-100 booking-type-btn" 
                                    data-booking-type="group" 
                                    style="min-height: 80px;">
                                <i class="bi bi-people-fill me-2 fs-4"></i><br>
                                <strong>Book Group Walk</strong><br>
                                <small class="text-muted">Immediate confirmation</small>
                            </button>
                        </div>
                        <div class="col-12 col-md-5 mb-3">
                            <button class="btn btn-outline-success btn-lg w-100 booking-type-btn" 
                                    data-booking-type="individual" 
                                    style="min-height: 80px;">
                                <i class="bi bi-person-fill me-2 fs-4"></i><br>
                                <strong>Request Individual Walk</strong><br>
                                <small class="text-muted">Requires approval</small>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Back Button (Hidden Initially) -->
                <div id="back-to-selection" class="text-center mb-3" style="display: none;">
                    <button class="btn btn-secondary" onclick="goBackToServiceSelection()">
                        <i class="bi bi-arrow-left"></i> Back to Service Selection
                    </button>
                </div>

                <!-- Group Walk Booking Form -->
                <div id="group-booking-form" class="booking-form-section" style="display: none;">
                    <div class="card">
                        <div class="card-header bg-primary text-white text-center">
                            <h4 class="mb-1"><i class="bi bi-people-fill me-2"></i>Group Walk Booking</h4>
                            <small>Select an available date and time slot. Group walks are limited to 4 dogs total per session.</small>
                        </div>
                        <div class="card-body">
                            <form id="group-walk-form">
                                <!-- Form content will be loaded here -->
                                <div id="group-form-loading" class="text-center p-4">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading form...</span>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>

                <!-- Individual Walk Request Form -->
                <div id="individual-booking-form" class="booking-form-section" style="display: none;">
                    <div class="card">
                        <div class="card-header bg-success text-white text-center">
                            <h4 class="mb-1"><i class="bi bi-person-fill me-2"></i>Individual Walk Request</h4>
                            <small>Submit a request for personalized one-on-one walking service</small>
                        </div>
                        <div class="card-body">
                            <form id="individual-walk-form">
                                <!-- Form content will be loaded here -->
                                <div id="individual-form-loading" class="text-center p-4">
                                    <div class="spinner-border text-success" role="status">
                                        <span class="visually-hidden">Loading form...</span>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            // Re-initialize event handlers after restoring content
            initializeBookingHandlers();
        }
        
        // Reset variables
        selectedDate = null;
        selectedTimeSlot = null;
        currentBookingType = null;
        availabilityData = [];
        
        console.log('Booking section reset successfully');
    }
    
    // New function to initialize booking handlers
    function initializeBookingHandlers() {
        // Re-attach service type selection handlers
        document.querySelectorAll('.booking-type-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                currentBookingType = this.dataset.bookingType;
                showBookingForm(currentBookingType);
            });
        });
        
        // Re-attach back button handler
        const backBtn = document.querySelector('[onclick="goBackToServiceSelection()"]');
        if (backBtn) {
            backBtn.addEventListener('click', function(e) {
                e.preventDefault();
                goBackToServiceSelection();
            });
        }
    }
    
    // Global function for success confirmation buttons - make sure it's properly exposed
    window.resetBookingSection = function() {
        console.log('Global resetBookingSection called');
        resetBookingSection();
    };
    
    // ===========================================
    // GROUP WALK FORM HANDLERS
    // ===========================================
    
    async function initializeGroupWalkForm() {
        // Load the group walk form content
        await loadGroupWalkFormContent();
        
        const numDogsSelector = document.getElementById('num-dogs-selector');
        
        if (numDogsSelector) {
            // Remove any existing event listeners
            numDogsSelector.removeEventListener('change', handleNumDogsChange);
            // Add event listener
            numDogsSelector.addEventListener('change', handleNumDogsChange);
        }
        
        const groupWalkForm = document.getElementById('group-walk-form');
        if (groupWalkForm) {
            // Remove any existing event listeners
            groupWalkForm.removeEventListener('submit', handleGroupFormSubmit);
            // Add event listener
            groupWalkForm.addEventListener('submit', handleGroupFormSubmit);
        }
        
        // Add real-time validation
        addRealTimeValidation();
    }
    
    async function loadGroupWalkFormContent() {
        try {
            const response = await fetch('/api/group-form/');
            if (response.ok) {
                const html = await response.text();
                const groupForm = document.getElementById('group-walk-form');
                if (groupForm) {
                    groupForm.innerHTML = html;
                }
            } else {
                // Fallback to basic form structure
                loadBasicGroupForm();
            }
        } catch (error) {
            console.error('Error loading group form:', error);
            loadBasicGroupForm();
        }
    }
    
    function loadBasicGroupForm() {
        const groupForm = document.getElementById('group-walk-form');
        if (!groupForm) return;
        
        groupForm.innerHTML = `
            <!-- Step 1: Number of Dogs -->
            <div class="booking-step" id="step-1-dogs">
                <h5 class="text-center mb-3">Step 1: How many dogs?</h5>
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <select id="num-dogs-selector" name="number_of_dogs" class="form-select form-select-lg" required>
                            <option value="">Select number of dogs...</option>
                            <option value="1">1 Dog</option>
                            <option value="2">2 Dogs</option>
                            <option value="3">3 Dogs</option>
                            <option value="4">4 Dogs</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Step 2: Calendar Selection -->
            <div class="booking-step" id="step-2-calendar" style="display: none;">
                <h5 class="text-center mb-3">Step 2: Choose Date & Time</h5>
                <div id="availability-calendar" class="availability-calendar mb-4">
                    <div class="loading text-center p-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading available slots...</p>
                    </div>
                </div>

                <!-- Selected Slot Info -->
                <div id="selection-summary" class="alert alert-info text-center" style="display: none;">
                    <strong>Selected:</strong> <span id="selected-info"></span>
                </div>
            </div>

            <!-- Step 3: Your Details -->
            <div class="booking-step" id="step-3-details" style="display: none;">
                <h5 class="text-center mb-3">Step 3: Your Details</h5>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="group_customer_name" class="form-label">Name *</label>
                        <input type="text" class="form-control" name="customer_name" id="group_customer_name" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="group_customer_email" class="form-label">Email *</label>
                        <input type="email" class="form-control" name="customer_email" id="group_customer_email" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="group_customer_phone" class="form-label">Phone *</label>
                        <input type="tel" class="form-control" name="customer_phone" id="group_customer_phone" required>
                    </div>
                    <div class="col-12 mb-3">
                        <label for="group_customer_address" class="form-label">Address *</label>
                        <textarea class="form-control" name="customer_address" id="group_customer_address" rows="3" 
                                placeholder="Your full address for pickup/dropoff" required></textarea>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="group_customer_postcode" class="form-label">Postcode *</label>
                        <input type="text" class="form-control" name="customer_postcode" id="group_customer_postcode" 
                            placeholder="EX33 1AA" style="text-transform: uppercase;" required>
                        <div class="form-text">We serve within 10 miles of Croyde, North Devon (EX33)</div>
                    </div>
                </div>

                <!-- Hidden fields for selected date/time -->
                <input type="hidden" name="booking_date" id="booking-date">
                <input type="hidden" name="time_slot" id="time-slot">
                <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
            </div>

            <!-- Step 4: Dog Details -->
            <div class="booking-step" id="step-4-dogs" style="display: none;">
                <h5 class="text-center mb-3">Step 4: Dog Details</h5>
                <div id="dog-forms-container">
                    <!-- Dog forms will be added here dynamically -->
                </div>
            </div>

            <!-- Submit Section -->
            <div class="booking-step text-center" id="step-5-submit" style="display: none;">
                <button type="submit" class="btn btn-success btn-lg">
                    <i class="bi bi-check-circle"></i> Confirm Group Walk Booking
                </button>
            </div>
        `;
    }
    
    function handleNumDogsChange() {
        const numDogs = parseInt(this.value);
        if (numDogs > 0) {
            showStep('step-2-calendar');
            loadAvailabilityCalendar(numDogs);
            generateDogForms(numDogs, 'dog-forms-container');
        }
    }
    
    function handleGroupFormSubmit(e) {
        e.preventDefault();
        
        // Show loading state
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        submitBtn.disabled = true;
        
        submitGroupWalkForm().finally(() => {
            // Reset button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }
    
    function resetGroupWalkSteps() {
        // Hide all steps except first
        document.querySelectorAll('.booking-step').forEach(step => {
            step.style.display = 'none';
        });
        const step1 = document.getElementById('step-1-dogs');
        if (step1) step1.style.display = 'block';
        
        // Reset selection summary
        const selectionSummary = document.getElementById('selection-summary');
        if (selectionSummary) selectionSummary.style.display = 'none';
        
        const availabilityCalendar = document.getElementById('availability-calendar');
        if (availabilityCalendar) {
            availabilityCalendar.innerHTML = `
                <div class="loading text-center p-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading available slots...</p>
                </div>
            `;
        }
    }
    
    function showStep(stepId) {
        const step = document.getElementById(stepId);
        if (step) step.style.display = 'block';
    }
    
    async function loadAvailabilityCalendar(numDogs) {
        try {
            const response = await fetch(`/api/availability/?days=30&num_dogs=${numDogs}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            availabilityData = data.availability || [];
            renderCalendar();
        } catch (error) {
            console.error('Error loading availability:', error);
            const calendar = document.getElementById('availability-calendar');
            if (calendar) {
                calendar.innerHTML = `
                    <div class="alert alert-danger">
                        <h6>Error Loading Availability</h6>
                        <p>Unable to load available time slots. Please refresh the page and try again.</p>
                        <button class="btn btn-outline-danger btn-sm" onclick="window.location.reload()">
                            <i class="bi bi-arrow-clockwise"></i> Refresh Page
                        </button>
                    </div>
                `;
            }
        }
    }
    
    function renderCalendar() {
        const calendar = document.getElementById('availability-calendar');
        if (!calendar) return;
        
        const numDogsSelector = document.getElementById('num-dogs-selector');
        const numDogs = numDogsSelector ? parseInt(numDogsSelector.value) : 1;
        
        if (!availabilityData || availabilityData.length === 0) {
            calendar.innerHTML = `
                <div class="alert alert-warning">
                    <h6>No Available Slots</h6>
                    <p>No available slots for ${numDogs} dog${numDogs > 1 ? 's' : ''} in the next 30 days.</p>
                    <p>Please try selecting fewer dogs or contact us directly at <strong>alex@caninecompadre.co.uk</strong></p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="calendar-grid">';
        
        availabilityData.forEach(day => {
            const hasAvailableSlots = day.slots.some(slot => slot.can_book);
            
            html += `
                <div class="day-card ${hasAvailableSlots ? 'has-availability' : 'no-availability'}" data-date="${day.date}">
                    <div class="day-header">
                        <h6 class="day-name">${day.day_name}</h6>
                        <small class="date-display">${day.date_display}</small>
                    </div>
                    <div class="time-slots">
            `;
            
            day.slots.forEach(slot => {
                const cssClass = slot.can_book ? 'available' : 'full';
                const clickable = slot.can_book ? `onclick="selectSlot('${day.date}', '${slot.time_slot}', '${slot.time_display}', '${day.date_display}')"` : '';
                const spotsText = slot.available_spots === 1 ? '1 spot' : `${slot.available_spots} spots`;
                
                html += `
                    <div class="time-slot ${cssClass}" ${clickable} data-time-slot="${slot.time_slot}">
                        <div class="time-display">${slot.time_display}</div>
                        <div class="spots-info">
                            ${slot.can_book ? `${spotsText} available` : 'Fully booked'}
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        calendar.innerHTML = html;
    }
    
    // Global function for calendar slot selection
    window.selectSlot = function(date, timeSlot, timeDisplay, dateDisplay) {
        // Remove previous selections
        document.querySelectorAll('.day-card.selected, .time-slot.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        // Add selection to clicked elements
        const dayCard = document.querySelector(`[data-date="${date}"]`);
        if (dayCard) {
            const timeSlotEl = dayCard.querySelector(`[data-time-slot="${timeSlot}"]`);
            
            dayCard.classList.add('selected');
            if (timeSlotEl) timeSlotEl.classList.add('selected');
        }
        
        // Update selected values
        selectedDate = date;
        selectedTimeSlot = timeSlot;
        
        // Update form fields
        const bookingDateField = document.getElementById('booking-date');
        const timeSlotField = document.getElementById('time-slot');
        if (bookingDateField) bookingDateField.value = date;
        if (timeSlotField) timeSlotField.value = timeSlot;
        
        // Show selection summary
        const selectedInfo = document.getElementById('selected-info');
        const selectionSummary = document.getElementById('selection-summary');
        if (selectedInfo) selectedInfo.textContent = `${dateDisplay} at ${timeDisplay}`;
        if (selectionSummary) selectionSummary.style.display = 'block';
        
        // Show next steps
        showStep('step-3-details');
        showStep('step-4-dogs');
        showStep('step-5-submit');
        
        // Scroll to next step smoothly
        setTimeout(() => {
            const detailsStep = document.getElementById('step-3-details');
            if (detailsStep) {
                detailsStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    };
    
    async function submitGroupWalkForm() {
        const formData = new FormData();
        const form = document.getElementById('group-walk-form');
        if (!form) return;
        
        // Add basic form data including postcode
        const basicFields = ['customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_postcode', 'booking_date', 'time_slot', 'number_of_dogs'];
        basicFields.forEach(field => {
            const element = form.querySelector(`[name="${field}"]`);
            if (element) {
                formData.append(field, element.value);
            }
        });
        
        // Add dog data including vet information
        const numDogsSelector = document.getElementById('num-dogs-selector');
        const numDogs = numDogsSelector ? parseInt(numDogsSelector.value) : 0;
        
        for (let i = 0; i < numDogs; i++) {
            const dogFields = ['name', 'breed', 'age', 'allergies', 'special_instructions', 'good_with_other_dogs', 'behavioral_notes', 'vet_name', 'vet_phone', 'vet_address'];
            dogFields.forEach(field => {
                const element = form.querySelector(`[name="dog_${i}_${field}"]`);
                if (element) {
                    if (element.type === 'checkbox') {
                        formData.append(`dog_${i}_${field}`, element.checked ? 'on' : '');
                    } else {
                        formData.append(`dog_${i}_${field}`, element.value);
                    }
                }
            });
        }
        
        // Add CSRF token
        const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        } else {
            // Fallback - try to get CSRF token from page
            const pageCSRF = getCSRFToken();
            if (pageCSRF) {
                formData.append('csrfmiddlewaretoken', pageCSRF);
            }
        }
        
        try {
            const response = await fetch('/book/group/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Replace booking content with success message
                if (bookingMainContent) {
                    bookingMainContent.innerHTML = result.html;
                }
                
                // Scroll to success message
                setTimeout(() => {
                    bookingMainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
                
            } else {
                // Show errors
                showFormErrors('group-walk-form', result.errors, result.message);
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            showGenericError('group-walk-form', 'An error occurred while submitting your booking. Please check your internet connection and try again.');
        }
    }
    
    // ===========================================
    // INDIVIDUAL WALK FORM HANDLERS
    // ===========================================
    
    async function initializeIndividualWalkForm() {
        // Force load the basic form instead of trying API endpoint
        // (since we don't have templates set up yet)
        loadBasicIndividualForm();
        
        const timeChoice = document.getElementById('preferred_time_choice');
        const customTimeContainer = document.getElementById('custom-time-container');
        const numDogsSelector = document.getElementById('ind_number_of_dogs');
        const preferredDate = document.getElementById('preferred_date');
        
        // Set minimum date to tomorrow
        if (preferredDate) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            preferredDate.min = tomorrow.toISOString().split('T')[0];
        }
        
        // Handle time choice selection
        if (timeChoice) {
            timeChoice.removeEventListener('change', handleTimeChoice);
            timeChoice.addEventListener('change', handleTimeChoice);
        }
        
        // Handle number of dogs change
        if (numDogsSelector) {
            numDogsSelector.removeEventListener('change', handleIndividualNumDogs);
            numDogsSelector.addEventListener('change', handleIndividualNumDogs);
        }
        
        // Handle form submission
        const individualForm = document.getElementById('individual-walk-form');
        if (individualForm) {
            individualForm.removeEventListener('submit', handleIndividualFormSubmit);
            individualForm.addEventListener('submit', handleIndividualFormSubmit);
        }
        
        // Add real-time validation
        addRealTimeValidation();
    }
    
    async function loadIndividualWalkFormContent() {
        try {
            const response = await fetch('/api/individual-form/');
            if (response.ok) {
                const html = await response.text();
                const individualForm = document.getElementById('individual-walk-form');
                if (individualForm) {
                    individualForm.innerHTML = html;
                    
                    // Remove any duplicate warning messages after loading
                    const warnings = individualForm.querySelectorAll('.alert-warning');
                    if (warnings.length > 1) {
                        // Keep only the first warning message
                        for (let i = 1; i < warnings.length; i++) {
                            warnings[i].remove();
                        }
                    }
                }
            } else {
                // Fallback to basic form structure
                loadBasicIndividualForm();
            }
        } catch (error) {
            console.error('Error loading individual form:', error);
            loadBasicIndividualForm();
        }
    }
    
    function loadBasicIndividualForm() {
        const individualForm = document.getElementById('individual-walk-form');
        if (!individualForm) return;
        
        individualForm.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
            
            <!-- Your Details -->
            <div class="mb-4">
                <h5 class="mb-3">Your Details</h5>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="ind_customer_name" class="form-label">Name *</label>
                        <input type="text" class="form-control" name="customer_name" id="ind_customer_name" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="ind_customer_email" class="form-label">Email *</label>
                        <input type="email" class="form-control" name="customer_email" id="ind_customer_email" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="ind_customer_phone" class="form-label">Phone *</label>
                        <input type="tel" class="form-control" name="customer_phone" id="ind_customer_phone" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="ind_number_of_dogs" class="form-label">Number of Dogs *</label>
                        <select class="form-control" name="number_of_dogs" id="ind_number_of_dogs" required>
                            <option value="">Select...</option>
                            <option value="1">1 Dog</option>
                            <option value="2">2 Dogs</option>
                            <option value="3">3 Dogs</option>
                            <option value="4">4 Dogs</option>
                            <option value="5">5 Dogs</option>
                            <option value="6">6 Dogs</option>
                        </select>
                    </div>
                </div>
                <div class="mb-3">
                    <label for="ind_customer_address" class="form-label">Address *</label>
                    <textarea class="form-control" name="customer_address" id="ind_customer_address" rows="3" 
                            placeholder="Your full address for pickup/dropoff" required></textarea>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="ind_customer_postcode" class="form-label">Postcode *</label>
                    <input type="text" class="form-control" name="customer_postcode" id="ind_customer_postcode" 
                        placeholder="EX33 1AA" style="text-transform: uppercase;" required>
                    <div class="form-text">We serve within 10 miles of Croyde, North Devon (EX33)</div>
                </div>
            </div>

            <!-- Walk Details -->
            <div class="mb-4">
                <h5 class="mb-3">Walk Details</h5>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="preferred_date" class="form-label">Preferred Date *</label>
                        <input type="date" class="form-control" name="preferred_date" id="preferred_date" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="preferred_time_choice" class="form-label">Preferred Time *</label>
                        <select class="form-control" name="preferred_time_choice" id="preferred_time_choice" required>
                            <option value="">Select time preference...</option>
                            <option value="early_morning">Early Morning (7:00-10:00 AM)</option>
                            <option value="late_afternoon">Late Afternoon/Evening (5:00-7:00 PM)</option>
                            <option value="flexible">Flexible - let us suggest a time</option>
                            <option value="custom">Other specific time</option>
                        </select>
                    </div>
                </div>
                
                <!-- Custom time input (hidden by default) -->
                <div class="mb-3" id="custom-time-container" style="display: none;">
                    <label for="preferred_time" class="form-label">Specify Your Preferred Time</label>
                    <input type="text" class="form-control" name="preferred_time" id="preferred_time" 
                        placeholder="e.g., 8:00 AM - 9:00 AM">
                    <div class="form-text text-danger">
                        ⚠️ Remember: 10:00 AM - 1:00 PM and 2:00 PM - 5:00 PM are not available
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="reason_for_individual" class="form-label">Why does your dog need an individual walk? *</label>
                    <textarea class="form-control" name="reason_for_individual" id="reason_for_individual" rows="4" 
                            placeholder="Please explain your dog's specific needs (e.g., anxiety around other dogs, medical requirements, behavioral concerns, in training, etc.)" required></textarea>
                </div>
            </div>

            <!-- Dog Details Section -->
            <div class="mb-4">
                <h5 class="mb-3">Dog Details</h5>
                <div id="individual-dog-forms-container">
                    <!-- Dog forms will be added here dynamically -->
                </div>
            </div>

            <!-- Submit Section -->
            <div class="text-center">
                <button type="submit" class="btn btn-success btn-lg">
                    <i class="bi bi-send"></i> Submit Individual Walk Request
                </button>
            </div>
        `;
    }
    
    function handleTimeChoice() {
        const customTimeContainer = document.getElementById('custom-time-container');
        const preferredTimeField = document.getElementById('preferred_time');
        
        if (this.value === 'custom') {
            if (customTimeContainer) customTimeContainer.style.display = 'block';
            if (preferredTimeField) preferredTimeField.required = true;
        } else {
            if (customTimeContainer) customTimeContainer.style.display = 'none';
            if (preferredTimeField) {
                preferredTimeField.required = false;
                preferredTimeField.value = '';
            }
        }
    }
    
    function handleIndividualNumDogs() {
        const numDogs = parseInt(this.value);
        if (numDogs > 0) {
            generateDogForms(numDogs, 'individual-dog-forms-container');
        }
    }
    
    function handleIndividualFormSubmit(e) {
        e.preventDefault();
        
        // Show loading state
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        submitBtn.disabled = true;
        
        submitIndividualWalkForm().finally(() => {
            // Reset button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }
    
    async function submitIndividualWalkForm() {
        const formData = new FormData();
        const form = document.getElementById('individual-walk-form');
        if (!form) return;
        
        // Add basic form data including postcode
        const basicFields = [
            'customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_postcode',
            'preferred_date', 'preferred_time_choice', 'preferred_time', 
            'reason_for_individual', 'number_of_dogs'
        ];
        
        basicFields.forEach(field => {
            const element = form.querySelector(`[name="${field}"]`);
            if (element) {
                formData.append(field, element.value);
            }
        });
        
        // Add dog data including vet information
        const numDogsSelector = document.getElementById('ind_number_of_dogs');
        const numDogs = numDogsSelector ? parseInt(numDogsSelector.value) : 0;
        
        for (let i = 0; i < numDogs; i++) {
            const dogFields = ['name', 'breed', 'age', 'allergies', 'special_instructions', 'good_with_other_dogs', 'behavioral_notes', 'vet_name', 'vet_phone', 'vet_address'];
            dogFields.forEach(field => {
                const element = form.querySelector(`[name="dog_${i}_${field}"]`);
                if (element) {
                    if (element.type === 'checkbox') {
                        formData.append(`dog_${i}_${field}`, element.checked ? 'on' : '');
                    } else {
                        formData.append(`dog_${i}_${field}`, element.value);
                    }
                }
            });
        }
        
        // Add CSRF token
        const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        } else {
            // Fallback - try to get CSRF token from page
            const pageCSRF = getCSRFToken();
            if (pageCSRF) {
                formData.append('csrfmiddlewaretoken', pageCSRF);
            }
        }
        
        try {
            const response = await fetch('/book/individual/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Replace booking content with success message
                if (bookingMainContent) {
                    bookingMainContent.innerHTML = result.html;
                }
                
                // Scroll to success message
                setTimeout(() => {
                    bookingMainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
                
            } else {
                // Show errors
                showFormErrors('individual-walk-form', result.errors, result.message);
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            showGenericError('individual-walk-form', 'An error occurred while submitting your request. Please check your internet connection and try again.');
        }
    }
    
    // ===========================================
    // DOG FORMS GENERATION
    // ===========================================
    
    function generateDogForms(numDogs, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        for (let i = 0; i < numDogs; i++) {
            const dogForm = createDogForm(i);
            if (dogForm) container.appendChild(dogForm);
        }
        
        // Re-apply real-time validation to new fields
        addRealTimeValidation();
    }
    
    function createDogForm(index) {
        const template = document.getElementById('dog-form-template');
        if (!template) {
            // Create basic dog form if template doesn't exist
            return createBasicDogForm(index);
        }
        
        const clone = template.content.cloneNode(true);
        
        // Update form field names and IDs
        clone.querySelectorAll('input, textarea, select').forEach(field => {
            if (field.name) {
                field.name = field.name.replace('{INDEX}', index);
            }
            if (field.id) {
                field.id = field.id.replace('{INDEX}', index);
            }
        });
        
        // Update labels
        clone.querySelectorAll('label').forEach(label => {
            if (label.getAttribute('for')) {
                label.setAttribute('for', label.getAttribute('for').replace('{INDEX}', index));
            }
        });
        
        // Update dog number
        const dogNumber = clone.querySelector('.dog-number');
        if (dogNumber) dogNumber.textContent = index + 1;
        
        // Show remove button for additional dogs
        if (index > 0) {
            const removeBtn = clone.querySelector('.remove-dog-btn');
            if (removeBtn) {
                removeBtn.style.display = 'block';
                removeBtn.addEventListener('click', function() {
                    this.closest('.dog-form').remove();
                });
            }
        }
        
        return clone;
    }
    
    function createBasicDogForm(index) {
        const dogFormDiv = document.createElement('div');
        dogFormDiv.className = 'dog-form card mb-3';
        dogFormDiv.innerHTML = `
            <div class="card-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Dog ${index + 1} Details</h6>
                    ${index > 0 ? '<button type="button" class="btn btn-outline-danger btn-sm remove-dog-btn"><i class="bi bi-trash"></i> Remove</button>' : ''}
                </div>
            </div>
            <div class="card-body">
                <!-- Basic Dog Info -->
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Dog's Name *</label>
                        <input type="text" class="form-control" name="dog_${index}_name" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Breed *</label>
                        <input type="text" class="form-control" name="dog_${index}_breed" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Age (years) *</label>
                        <input type="number" class="form-control" name="dog_${index}_age" min="0" max="25" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="form-check mt-4">
                            <input type="checkbox" class="form-check-input" name="dog_${index}_good_with_other_dogs" checked>
                            <label class="form-check-label">Good with other dogs</label>
                        </div>
                    </div>
                </div>

                <!-- Health & Care Info -->
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Allergies/Health Concerns</label>
                        <textarea class="form-control" name="dog_${index}_allergies" rows="2" 
                                placeholder="Any medical conditions we should know about"></textarea>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Special Instructions</label>
                        <textarea class="form-control" name="dog_${index}_special_instructions" rows="2" 
                                placeholder="Special care or handling instructions"></textarea>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Behavioral Notes</label>
                    <textarea class="form-control" name="dog_${index}_behavioral_notes" rows="2" 
                            placeholder="Any behavioral concerns, triggers, or special needs"></textarea>
                </div>

                <!-- Vet Information -->
                <hr>
                <h6 class="text-primary mb-3"><i class="bi bi-plus-circle me-2"></i>Veterinary Information</h6>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Vet Practice Name *</label>
                        <input type="text" class="form-control" name="dog_${index}_vet_name" 
                            placeholder="e.g., Croyde Veterinary Surgery" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Vet Phone Number *</label>
                        <input type="tel" class="form-control" name="dog_${index}_vet_phone" 
                            placeholder="01271 890123" required>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Vet Practice Address *</label>
                    <textarea class="form-control" name="dog_${index}_vet_address" rows="2" 
                            placeholder="Full vet practice address" required></textarea>
                </div>
            </div>
        `;
        
        // Add remove button functionality
        if (index > 0) {
            const removeBtn = dogFormDiv.querySelector('.remove-dog-btn');
            if (removeBtn) {
                removeBtn.addEventListener('click', function() {
                    dogFormDiv.remove();
                });
            }
        }
        
        return dogFormDiv;
    }
    
    // ===========================================
    // ERROR HANDLING
    // ===========================================
    
    function showFormErrors(formId, errors, message) {
        // Clear previous errors
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        
        // Show general message
        if (message) {
            const form = document.getElementById(formId);
            if (form) {
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger error-message mt-3';
                alert.innerHTML = `
                    <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Please correct the following errors:</h6>
                    <p class="mb-0">${message}</p>
                `;
                form.insertBefore(alert, form.firstChild);
            }
        }
        
        // Show field-specific errors
        if (errors) {
            Object.keys(errors).forEach(fieldName => {
                const field = document.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    field.classList.add('is-invalid');
                    
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback error-message';
                    errorDiv.textContent = Array.isArray(errors[fieldName]) ? errors[fieldName].join(', ') : errors[fieldName];
                    
                    // Insert error message after the field
                    field.parentNode.insertBefore(errorDiv, field.nextSibling);
                }
            });
        }
        
        // Scroll to first error
        const firstError = document.querySelector('.is-invalid, .alert-danger');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    function showGenericError(formId, message) {
        const form = document.getElementById(formId);
        if (form) {
            // Clear previous errors
            document.querySelectorAll('.error-message').forEach(el => el.remove());
            
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger error-message mt-3';
            alert.innerHTML = `
                <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Error</h6>
                <p class="mb-0">${message}</p>
            `;
            form.insertBefore(alert, form.firstChild);
            
            // Scroll to error
            alert.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    // ===========================================
    // UTILITY FUNCTIONS
    // ===========================================
    
    function getCSRFToken() {
        // Try to get CSRF token from various sources
        const cookieCSRF = document.querySelector('[name=csrfmiddlewaretoken]');
        if (cookieCSRF) return cookieCSRF.value;
        
        const metaCSRF = document.querySelector('meta[name="csrf-token"]');
        if (metaCSRF) return metaCSRF.getAttribute('content');
        
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        return '';
    }
    
    // Form validation helpers
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    function validatePhone(phone) {
        const re = /^[\d\s\-\+\(\)]+$/;
        return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
    }
    
    function validatePostcode(postcode) {
        // UK postcode validation for areas around Croyde, North Devon
        const re = /^(EX3[1-4])\s?[0-9][A-Z]{2}$/i;
        return re.test(postcode);
    }
    
    // Add real-time validation to forms
    function addRealTimeValidation() {
        // Email validation
        document.querySelectorAll('input[type="email"]').forEach(emailField => {
            if (!emailField.hasAttribute('data-validated')) {
                emailField.setAttribute('data-validated', 'true');
                emailField.addEventListener('blur', function() {
                    validateField(this, validateEmail(this.value), 'Please enter a valid email address');
                });
            }
        });
        
        // Phone validation
        document.querySelectorAll('input[type="tel"]').forEach(phoneField => {
            if (!phoneField.hasAttribute('data-validated')) {
                phoneField.setAttribute('data-validated', 'true');
                phoneField.addEventListener('blur', function() {
                    validateField(this, validatePhone(this.value), 'Please enter a valid phone number');
                });
            }
        });
        
        // Postcode validation and formatting
        document.querySelectorAll('input[name="customer_postcode"], input[name*="postcode"]').forEach(postcodeField => {
            if (!postcodeField.hasAttribute('data-validated')) {
                postcodeField.setAttribute('data-validated', 'true');
                
                postcodeField.addEventListener('input', function() {
                    this.value = this.value.toUpperCase();
                });
                
                postcodeField.addEventListener('blur', function() {
                    if (this.value) {
                        // Auto-format postcode (add space if missing)
                        let postcode = this.value.replace(/\s/g, '');
                        if (postcode.length >= 5) {
                            postcode = postcode.slice(0, -3) + ' ' + postcode.slice(-3);
                            this.value = postcode;
                        }
                        
                        const isValid = validatePostcode(this.value);
                        const errorMessage = isValid ? '' : 'We only serve EX31-EX34 postcode areas (within 10 miles of Croyde, North Devon)';
                        validateField(this, isValid, errorMessage);
                    }
                });
            }
        });
        
        // Required field validation
        document.querySelectorAll('input[required], textarea[required], select[required]').forEach(field => {
            if (!field.hasAttribute('data-required-validated')) {
                field.setAttribute('data-required-validated', 'true');
                field.addEventListener('blur', function() {
                    if (this.type === 'checkbox') {
                        validateField(this, this.checked, 'This field is required');
                    } else {
                        validateField(this, this.value.trim() !== '', 'This field is required');
                    }
                });
            }
        });
    }
    
    function validateField(field, isValid, errorMessage) {
        if (field.value && !isValid) {
            field.classList.add('is-invalid');
            
            // Remove existing error message
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) existingError.remove();
            
            // Add new error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = errorMessage;
            field.parentNode.insertBefore(errorDiv, field.nextSibling);
        } else {
            field.classList.remove('is-invalid');
            const errorDiv = field.parentNode.querySelector('.invalid-feedback');
            if (errorDiv) errorDiv.remove();
        }
    }
    
    // Global function to go back to service selection
    window.goBackToServiceSelection = function() {
        console.log('goBackToServiceSelection called');
        
        // Hide forms and show service selection
        const serviceSelection = document.getElementById('booking-service-selection');
        const backToSelection = document.getElementById('back-to-selection');
        const groupForm = document.getElementById('group-booking-form');
        const individualForm = document.getElementById('individual-booking-form');
        
        if (serviceSelection) serviceSelection.style.display = 'block';
        if (backToSelection) backToSelection.style.display = 'none';
        if (groupForm) groupForm.style.display = 'none';
        if (individualForm) individualForm.style.display = 'none';
        
        // Reset variables
        selectedDate = null;
        selectedTimeSlot = null;
        currentBookingType = null;
        availabilityData = [];
        
        // Clear any error messages
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        
        console.log('Back to service selection completed');
    };
    
    // Initialize real-time validation on page load
    addRealTimeValidation();
    
    console.log('Booking system JavaScript loaded successfully with calendar integration!');
});
