// booking.js - Complete Booking System JavaScript with Multi-Booking Support

// GLOBAL UTILITY FUNCTIONS (AVAILABLE EVERYWHERE)
function getCSRFToken() {
    const cookieCSRF = document.querySelector('[name=csrfmiddlewaretoken]');
    if (cookieCSRF) return cookieCSRF.value;
    
    const metaCSRF = document.querySelector('meta[name="csrf-token"]');
    if (metaCSRF) return metaCSRF.getAttribute('content');
    
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePhone(phone) {
    const re = /^[\d\s\-\+\(\)]+$/;
    return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
}

function validatePostcode(postcode) {
    const re = /^(EX3[1-4])\s?[0-9][A-Z]{2}$/i;
    return re.test(postcode);
}

// GLOBAL VARIABLES (AVAILABLE EVERYWHERE)
let availabilityData = [];
let selectedSlots = [];
let currentBookingType = null;
let isMultiBookingMode = false;

document.addEventListener('DOMContentLoaded', function() {
    
    // Main booking elements
    const bookingMainContent = document.getElementById('booking-main-content');
    
    // ===========================================
    // SERVICE SELECTION HANDLERS
    // ===========================================
    
    document.querySelectorAll('.booking-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentBookingType = this.dataset.bookingType;
            showBookingForm(currentBookingType);
        });
    });
    
    function showBookingForm(type) {
        const serviceSelection = document.getElementById('booking-service-selection');
        const backToSelection = document.getElementById('back-to-selection');
        const groupForm = document.getElementById('group-booking-form');
        const individualForm = document.getElementById('individual-booking-form');
        
        if (serviceSelection) serviceSelection.style.display = 'none';
        if (backToSelection) backToSelection.style.display = 'block';
        
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
        if (bookingMainContent) {
            bookingMainContent.innerHTML = `
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
                <div id="back-to-selection" class="text-center mb-3" style="display: none;">
                    <button class="btn btn-secondary" onclick="goBackToServiceSelection()">
                        <i class="bi bi-arrow-left"></i> Back to Service Selection
                    </button>
                </div>
                <div id="group-booking-form" class="booking-form-section" style="display: none;">
                    <div class="card">
                        <div class="card-header bg-primary text-white text-center">
                            <h4 class="mb-1"><i class="bi bi-people-fill me-2"></i>Group Walk Booking</h4>
                            <small>Select an available date and time slot. Group walks are limited to 4 dogs total per session.</small>
                        </div>
                        <div class="card-body">
                            <form id="group-walk-form">
                                <div id="group-form-loading" class="text-center p-4">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading form...</span>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                <div id="individual-booking-form" class="booking-form-section" style="display: none;">
                    <div class="card">
                        <div class="card-header bg-success text-white text-center">
                            <h4 class="mb-1"><i class="bi bi-person-fill me-2"></i>Individual Walk Request</h4>
                            <small>Submit a request for personalized one-on-one walking service</small>
                        </div>
                        <div class="card-body">
                            <form id="individual-walk-form">
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
            initializeBookingHandlers();
        }
        
        selectedSlots = [];
        currentBookingType = null;
        availabilityData = [];
        isMultiBookingMode = false;
    }
    
    function initializeBookingHandlers() {
        document.querySelectorAll('.booking-type-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                currentBookingType = this.dataset.bookingType;
                showBookingForm(currentBookingType);
            });
        });
    }
    
    window.resetBookingSection = function() {
        resetBookingSection();
    };
    
    // ===========================================
    // GROUP WALK FORM HANDLERS
    // ===========================================
    
    async function initializeGroupWalkForm() {
        await loadGroupWalkFormContent();
        
        const numDogsSelector = document.getElementById('num-dogs-selector');
        if (numDogsSelector) {
            numDogsSelector.removeEventListener('change', handleNumDogsChange);
            numDogsSelector.addEventListener('change', handleNumDogsChange);
        }
        
        const groupWalkForm = document.getElementById('group-walk-form');
        if (groupWalkForm) {
            groupWalkForm.removeEventListener('submit', handleGroupFormSubmit);
            groupWalkForm.addEventListener('submit', handleGroupFormSubmit);
        }
        
        addRealTimeValidation();
        initializeEnhancedValidation();
    }
    
    function loadGroupWalkFormContent() {
        loadBasicGroupForm();
    }
    
    function loadBasicGroupForm() {
        const groupForm = document.getElementById('group-walk-form');
        if (!groupForm) return;
        
        groupForm.innerHTML = `
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

            <div class="booking-step" id="step-2-calendar" style="display: none;">
                <h5 class="text-center mb-3">Step 2: Choose Date & Time</h5>
                
                <div class="multi-booking-toggle text-center mb-3" id="multi-booking-toggle" style="display: none;"></div>
                
                <div id="availability-calendar" class="availability-calendar mb-4">
                    <div class="loading text-center p-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading available slots...</p>
                    </div>
                </div>

                <div id="selection-summary" class="alert alert-info text-center" style="display: none;">
                    <strong>Selected:</strong> <span id="selected-info"></span>
                </div>
            </div>

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

                <input type="hidden" name="booking_date" id="booking-date">
                <input type="hidden" name="time_slot" id="time-slot">
                <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
            </div>

            <div class="booking-step" id="step-4-dogs" style="display: none;">
                <h5 class="text-center mb-3">Step 4: Dog Details</h5>
                <div id="dog-forms-container"></div>
            </div>

            <div class="booking-step text-center" id="step-5-submit" style="display: none;">
                <button type="submit" class="btn btn-success btn-lg">
                    <i class="bi bi-check-circle"></i> <span id="submit-btn-text">Confirm Group Walk Booking</span>
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
        
        if (selectedSlots.length === 0) {
            showGenericError('group-walk-form', 'Please select at least one time slot.');
            return;
        }
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        const loadingText = isMultiBookingMode && selectedSlots.length > 1 
            ? `<span class="spinner-border spinner-border-sm me-2"></span>Processing ${selectedSlots.length} bookings...`
            : '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        
        submitBtn.innerHTML = loadingText;
        submitBtn.disabled = true;
        
        submitGroupWalkForm().finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }
    
    function showStep(stepId) {
        const step = document.getElementById(stepId);
        if (step) step.style.display = 'block';
    }
    
    async function loadAvailabilityCalendar(numDogs) {
        try {
            const response = await fetch(`/api/availability/?days=180&num_dogs=${numDogs}`);
            
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
                const spotsText = slot.available_spots === 1 ? '1 spot' : `${slot.available_spots} spots`;
                
                if (slot.can_book) {
                    html += `
                        <div class="time-slot ${cssClass}" 
                             onclick="window.selectSlot('${day.date}', '${slot.time_slot}', '${slot.time_display}', '${day.date_display}')" 
                             data-time-slot="${slot.time_slot}"
                             style="cursor: pointer;">
                            <div class="time-display">${slot.time_display}</div>
                            <div class="spots-info">${spotsText} available</div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="time-slot ${cssClass}" data-time-slot="${slot.time_slot}">
                            <div class="time-display">${slot.time_display}</div>
                            <div class="spots-info">Fully booked</div>
                        </div>
                    `;
                }
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        calendar.innerHTML = html;
    }
    
    // UPDATED MULTI-BOOKING TOGGLE FUNCTION
    function showMultiBookingToggle() {
        const toggle = document.getElementById('multi-booking-toggle');
        if (toggle) {
            toggle.innerHTML = `
                <div class="alert alert-success">
                    <div class="form-check form-switch d-inline-block">
                        <input class="form-check-input" type="checkbox" id="multiBookingToggle">
                        <label class="form-check-label" for="multiBookingToggle">
                            <strong>Want to book more walks?</strong> Toggle this to select additional time slots
                        </label>
                    </div>
                    <div class="mt-2">
                        <small class="text-muted">You can book multiple walks with the same customer and dog details! 
                        Or click "Continue to Details" below when you're ready to proceed.</small>
                    </div>
                </div>
            `;
            
            toggle.style.display = 'block';
            
            const checkbox = document.getElementById('multiBookingToggle');
            if (checkbox && !checkbox.hasAttribute('data-listener-added')) {
                checkbox.setAttribute('data-listener-added', 'true');
                checkbox.addEventListener('change', function() {
                    isMultiBookingMode = this.checked;
                    if (!isMultiBookingMode) {
                        if (selectedSlots.length > 1) {
                            selectedSlots = [selectedSlots[0]];
                        }
                        updateSelectionSummary();
                    }
                    updateCalendarDisplay();
                    updateSubmitButtonText();
                    
                    // Hide continue button when in multi-booking mode
                    const continueContainer = document.getElementById('continue-to-details');
                    if (continueContainer) {
                        continueContainer.style.display = isMultiBookingMode ? 'none' : 'block';
                    }
                });
            }
        }
    }
    
    // CONTINUE BUTTON FUNCTION
    function showContinueButton() {
        const continueContainer = document.getElementById('continue-to-details');
        if (!continueContainer) {
            // Create continue button container if it doesn't exist
            const calendar = document.getElementById('availability-calendar');
            if (calendar && calendar.parentNode) {
                const continueDiv = document.createElement('div');
                continueDiv.id = 'continue-to-details';
                continueDiv.className = 'text-center mt-3';
                continueDiv.innerHTML = `
                    <button type="button" class="btn btn-success btn-lg" onclick="proceedToNextSteps()">
                        <i class="bi bi-arrow-right me-2"></i>Continue to Details
                    </button>
                `;
                
                // Insert after the selection summary
                const selectionSummary = document.getElementById('selection-summary');
                if (selectionSummary) {
                    selectionSummary.parentNode.insertBefore(continueDiv, selectionSummary.nextSibling);
                } else {
                    calendar.parentNode.insertBefore(continueDiv, calendar.nextSibling);
                }
            }
        } else {
            continueContainer.style.display = 'block';
        }
    }
    
    // FUNCTION TO PROCEED TO NEXT STEPS
    window.proceedToNextSteps = function() {
        if (selectedSlots.length > 0) {
            showStep('step-3-details');
            showStep('step-4-dogs');
            showStep('step-5-submit');
            
            // Hide the continue button
            const continueContainer = document.getElementById('continue-to-details');
            if (continueContainer) {
                continueContainer.style.display = 'none';
            }
            
            // Scroll to the details step
            setTimeout(() => {
                const detailsStep = document.getElementById('step-3-details');
                if (detailsStep) {
                    detailsStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
        }
    };
    
    function updateSubmitButtonText() {
        const submitBtnText = document.getElementById('submit-btn-text');
        if (submitBtnText) {
            if (isMultiBookingMode && selectedSlots.length > 1) {
                submitBtnText.textContent = `Confirm ${selectedSlots.length} Group Walk Bookings`;
            } else {
                submitBtnText.textContent = 'Confirm Group Walk Booking';
            }
        }
    }
    
    function updateCalendarDisplay() {
        document.querySelectorAll('.day-card.selected, .time-slot.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        selectedSlots.forEach(slot => {
            const dayCard = document.querySelector(`[data-date="${slot.date}"]`);
            if (dayCard) {
                const timeSlotEl = dayCard.querySelector(`[data-time-slot="${slot.timeSlot}"]`);
                if (timeSlotEl) {
                    timeSlotEl.classList.add('selected');
                    if (!isMultiBookingMode || selectedSlots.length === 1) {
                        dayCard.classList.add('selected');
                    }
                }
            }
        });
    }
    
    function updateSelectionSummary() {
        const selectedInfo = document.getElementById('selected-info');
        const selectionSummary = document.getElementById('selection-summary');
        
        if (selectedSlots.length === 0) {
            if (selectionSummary) selectionSummary.style.display = 'none';
            return;
        }
        
        let summaryText;
        if (selectedSlots.length === 1) {
            const slot = selectedSlots[0];
            summaryText = `${slot.dateDisplay} at ${slot.timeDisplay}`;
        } else {
            summaryText = `${selectedSlots.length} walks selected`;
            
            const detailsList = selectedSlots
                .sort((a, b) => new Date(a.date) - new Date(b.date))
                .map(slot => `• ${slot.dateDisplay} at ${slot.timeDisplay}`)
                .join('<br>');
            
            summaryText += `<br><small>${detailsList}</small>`;
        }
        
        if (selectedInfo) selectedInfo.innerHTML = summaryText;
        if (selectionSummary) {
            selectionSummary.style.display = 'block';
            selectionSummary.className = selectedSlots.length > 1 
                ? 'alert alert-success text-center'
                : 'alert alert-info text-center';
        }
        
        const bookingDateField = document.getElementById('booking-date');
        const timeSlotField = document.getElementById('time-slot');
        
        if (selectedSlots.length > 0) {
            const firstSlot = selectedSlots[0];
            if (bookingDateField) bookingDateField.value = firstSlot.date;
            if (timeSlotField) timeSlotField.value = firstSlot.timeSlot;
        }
    }
    
    async function submitGroupWalkForm() {
        if (selectedSlots.length === 0) {
            showGenericError('group-walk-form', 'Please select at least one time slot.');
            return;
        }
        
        const formData = new FormData();
        const form = document.getElementById('group-walk-form');
        if (!form) return;
        
        const basicFields = ['customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_postcode', 'number_of_dogs'];
        basicFields.forEach(field => {
            const element = form.querySelector(`[name="${field}"]`);
            if (element) {
                formData.append(field, element.value);
            }
        });
        
        formData.append('selected_slots', JSON.stringify(selectedSlots));
        formData.append('is_multi_booking', selectedSlots.length > 1 ? 'true' : 'false');
        
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
        
        const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        } else {
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

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                if (bookingMainContent) {
                    bookingMainContent.innerHTML = result.html;
                }

                setTimeout(() => {
                    bookingMainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            } else {
                showDetailedFormErrors('group-walk-form', result.errors, result.message);
            }
        } catch (error) {
            console.error('Error submitting form:', error);

            if (error.name === 'TypeError' || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                showTechnicalError('group-walk-form', 'network');
            } else if (error.message.includes('Server error: 5')) {
                showTechnicalError('group-walk-form', 'server');
            } else if (error.message.includes('timeout')) {
                showTechnicalError('group-walk-form', 'timeout');
            } else {
                showTechnicalError('group-walk-form', 'generic');
            }
        }
    }
    
    // ===========================================
    // ENHANCED DOG FORMS GENERATION WITH VET AUTO-FILL
    // ===========================================

    function generateDogForms(numDogs, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        for (let i = 0; i < numDogs; i++) {
            const dogForm = createBasicDogForm(i);
            if (dogForm) container.appendChild(dogForm);
        }

        addRealTimeValidation();
    }

    // function createDogForm(index) {
    //     const template = document.getElementById('dog-form-template');
    //     if (!template) {
    //         return createBasicDogForm(index);
    //     }

    //     const clone = template.content.cloneNode(true);
    //     const isFirstDog = index === 0;

    //     // Replace {INDEX} placeholders with actual index
    //     clone.querySelectorAll('input, textarea, select').forEach(field => {
    //         if (field.name) {
    //             field.name = field.name.replace('{INDEX}', index);
    //         }
    //         if (field.id) {
    //             field.id = field.id.replace('{INDEX}', index);
    //         }
    //     });

    //     clone.querySelectorAll('label').forEach(label => {
    //         if (label.getAttribute('for')) {
    //             label.setAttribute('for', label.getAttribute('for').replace('{INDEX}', index));
    //         }
    //     });

    //     // Update dog number
    //     const dogNumber = clone.querySelector('.dog-number');
    //     if (dogNumber) dogNumber.textContent = index + 1;

    //     // Show/hide vet auto-fill toggle based on dog index
    //     const vetNotice = clone.querySelector('.vet-autofill-notice');
    //     const vetSubtitle = clone.querySelector('.vet-subtitle');
    //     const vetDifferentNote = clone.querySelector('.vet-different-note');

    //     if (!isFirstDog) {
    //         // Show toggle and additional elements for dogs after the first
    //         if (vetNotice) vetNotice.style.display = 'block';
    //         if (vetSubtitle) vetSubtitle.style.display = 'inline';
    //         if (vetDifferentNote) vetDifferentNote.style.display = 'block';
    //     } else {
    //         // Hide toggle for first dog
    //         if (vetNotice) vetNotice.style.display = 'none';
    //         if (vetSubtitle) vetSubtitle.style.display = 'none';
    //         if (vetDifferentNote) vetDifferentNote.style.display = 'none';
    //     }

    //     // Handle remove button
    //     if (index > 0) {
    //         const removeBtn = clone.querySelector('.remove-dog-btn');
    //         if (removeBtn) {
    //             removeBtn.style.display = 'block';
    //             removeBtn.addEventListener('click', function () {
    //                 this.closest('.dog-form').remove();
    //             });
    //         }
    //     }

    //     // Convert DocumentFragment to actual DOM element
    //     const dogFormDiv = document.createElement('div');
    //     dogFormDiv.appendChild(clone);
    //     const actualDogForm = dogFormDiv.firstElementChild;

    //     // Add vet auto-fill functionality for non-first dogs
    //     if (!isFirstDog) {
    //         const sameVetCheckbox = actualDogForm.querySelector(`#sameVet_${index}`);
    //         const vetFields = actualDogForm.querySelectorAll('.vet-fields input, .vet-fields textarea');

    //         if (sameVetCheckbox) {
    //             // Initially enable vet fields since toggle is off by defualt
    //             updateVetFields(vetFields, false);

    //             sameVetCheckbox.addEventListener('change', function () {
    //                 const useSameVet = this.checked;
    //                 updateVetFields(vetFields, !useSameVet);

    //                 if (useSameVet) {
    //                     // Copy vet info from first dog
    //                     copyVetInfoFromFirstDog(index);
    //                 } else {
    //                     // Clear fields for manual entry
    //                     clearVetFields(vetFields);
    //                 }
    //             });

    //             // Auto-fill initially if same vet is checked
    //             // setTimeout(() => copyVetInfoFromFirstDog(index), 100);
    //         }
    //     }

    //     return actualDogForm;
    // }

    function createBasicDogForm(index) {
        const dogFormDiv = document.createElement('div');
        dogFormDiv.className = 'dog-form card mb-3';

        // Check if this is the first dog (index 0) or subsequent dogs
        const isFirstDog = index === 0;
        const vetSectionClass = isFirstDog ? '' : 'vet-section-autofill';

        dogFormDiv.innerHTML = `
        <div class="card-header">
            <div class="d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Dog ${index + 1} Details</h6>
                ${index > 0 ? '<button type="button" class="btn btn-outline-danger btn-sm remove-dog-btn"><i class="bi bi-trash"></i> Remove</button>' : ''}
            </div>
        </div>
        <div class="card-body">
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
            <hr>
            
            <!-- VET INFORMATION SECTION -->
            <div class="vet-info-section ${vetSectionClass}">
                ${!isFirstDog ? `
                <div class="alert alert-info vet-autofill-notice">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <i class="bi bi-info-circle me-2"></i>
                            <strong>Same vet as Dog 1?</strong> 
                            <span class="text-muted">Most customers use the same vet for all their dogs</span>
                        </div>
                        <div id="vet-control-${index}">
                            <!-- Initially show the toggle -->
                            <div class="form-check form-switch" id="toggle-container-${index}">
                                <input class="form-check-input" type="checkbox" id="sameVet_${index}">
                                <label class="form-check-label" for="sameVet_${index}">Use same vet</label>
                            </div>
                            <!-- Clear button (initially hidden) -->
                            <button type="button" class="btn btn-outline-warning btn-sm" id="clear-vet-${index}" style="display: none;">
                                <i class="bi bi-trash"></i> Clear & Enter Different Vet
                            </button>
                        </div>
                    </div>
                </div>
                ` : ''}
                
                <h6 class="text-primary mb-3">
                    <i class="bi bi-plus-circle me-2"></i>Veterinary Information
                    ${!isFirstDog ? '<span class="text-muted">(for this specific dog)</span>' : ''}
                </h6>
                
                <div class="vet-fields">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Vet Practice Name *</label>
                            <input type="text" class="form-control vet-name" name="dog_${index}_vet_name" 
                                placeholder="e.g., Croyde Veterinary Surgery" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Vet Phone Number *</label>
                            <input type="tel" class="form-control vet-phone" name="dog_${index}_vet_phone" 
                                placeholder="01271 890123" required>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Vet Practice Address *</label>
                        <textarea class="form-control vet-address" name="dog_${index}_vet_address" rows="2" 
                                placeholder="Full vet practice address" required></textarea>
                    </div>
                </div>
                
                ${!isFirstDog ? `
                <div class="text-muted small mt-2">
                    <i class="bi bi-exclamation-triangle me-1"></i>
                    <strong>Different vet?</strong> Uncheck "Use same vet" above to enter different veterinary details.
                </div>
                ` : ''}
            </div>
        </div>
    `;

        // Add event listeners for vet auto-fill functionality
        if (!isFirstDog) {
            const sameVetCheckbox = dogFormDiv.querySelector(`#sameVet_${index}`);
            const clearVetButton = dogFormDiv.querySelector(`#clear-vet-${index}`);
            const toggleContainer = dogFormDiv.querySelector(`#toggle-container-${index}`);
            const vetFields = dogFormDiv.querySelectorAll('.vet-fields input, .vet-fields textarea');

            // Initially set up fields based on checkbox state
            const isInitiallyChecked = sameVetCheckbox.checked;
            updateVetFields(vetFields, isInitiallyChecked);

            // Toggle event handler
            sameVetCheckbox.addEventListener('change', function () {
                const useSameVet = this.checked;

                if (useSameVet) {
                    updateVetFields(vetFields, true);
                    copyVetInfoFromFirstDog(index);

                    // Show clear button, hide toggle
                    setTimeout(() => {
                        toggleContainer.style.display = 'none';
                        clearVetButton.style.display = 'block';
                    }, 500);
                }
            });

            // Clear button event handler
            clearVetButton.addEventListener('click', function () {
                // Clear all fields
                vetFields.forEach(field => {
                    field.value = '';
                    field.disabled = false;
                    field.classList.remove('auto-filled');
                    field.style.backgroundColor = '';
                    field.style.color = '';
                    field.style.borderColor = '';
                });

                // Show toggle again, hide clear button
                clearVetButton.style.display = 'none';
                toggleContainer.style.display = 'block';

                // Reset toggle to unchecked state
                sameVetCheckbox.checked = false;

                // Focus first field
                setTimeout(() => {
                    if (vetFields[0]) {
                        vetFields[0].focus();
                    }
                }, 100);
            });

            // Auto-fill initially if checkbox is checked
            if (isInitiallyChecked) {
                setTimeout(() => {
                    copyVetInfoFromFirstDog(index);
                    // Show clear button after initial auto-fill
                    setTimeout(() => {
                        toggleContainer.style.display = 'none';
                        clearVetButton.style.display = 'block';
                    }, 500);
                }, 100);
            } else {
                // If checkbox is unchecked initially, make sure fields are properly enabled.
                updateVetFields(vetFields, false)
            }
        }


        // Remove button functionality
        if (index > 0) {
            const removeBtn = dogFormDiv.querySelector('.remove-dog-btn');
            if (removeBtn) {
                removeBtn.addEventListener('click', function () {
                    dogFormDiv.remove();
                });
            }
        }

        return dogFormDiv;
    }

    function updateVetFields(vetFields, disable) {
        let focusApplied = false;

        vetFields.forEach(field => {
            field.disabled = disable;
            if (disable) {
                // Auto-filled state - add blue highlighting
                field.style.backgroundColor = '#e3f2fd';
                field.style.color = '#1565c0';
                field.style.borderColor = '#2196f3';
                field.classList.add('auto-filled');
            } else {
                // Manual entry state - remove highlighting
                field.style.backgroundColor = '';
                field.style.color = '';
                field.style.borderColor = '';
                field.classList.remove('auto-filled');
                
                if (!focusApplied) {
                    setTimeout(() => field.focus(), 100);
                    focusApplied = true;
                }
            }
        });
    }

    function copyVetInfoFromFirstDog(targetIndex) {
        // Get vet info from first dog (index 0)
        const firstDogVetName = document.querySelector('[name="dog_0_vet_name"]');
        const firstDogVetPhone = document.querySelector('[name="dog_0_vet_phone"]');
        const firstDogVetAddress = document.querySelector('[name="dog_0_vet_address"]');

        if (!firstDogVetName || !firstDogVetPhone || !firstDogVetAddress) {
            return;
        }

        // Set vet info for target dog
        const targetVetName = document.querySelector(`[name="dog_${targetIndex}_vet_name"]`);
        const targetVetPhone = document.querySelector(`[name="dog_${targetIndex}_vet_phone"]`);
        const targetVetAddress = document.querySelector(`[name="dog_${targetIndex}_vet_address"]`);

        if (targetVetName && targetVetPhone && targetVetAddress) {
            targetVetName.value = firstDogVetName.value;
            targetVetPhone.value = firstDogVetPhone.value;
            targetVetAddress.value = firstDogVetAddress.value;

            // Add blue highlighting to show these are auto-filled
            [targetVetName, targetVetPhone, targetVetAddress].forEach(field => {
                field.classList.add('auto-filled');
                field.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }
    }

    function clearVetFields(vetFields) {
        vetFields.forEach(field => {
            field.value = '';
            field.dispatchEvent(new Event('change', { bubbles: true }));
        });
    }

    // // Listen for changes to first dog's vet info to auto-update other dogs
    // document.addEventListener('change', function (e) {
    //     if (e.target.name && e.target.name.startsWith('dog_0_vet_')) {
    //         // First dog's vet info changed, update all other dogs using same vet
    //         updateAllDogsWithSameVet();
    //     }
    // });

    function updateAllDogsWithSameVet() {
        const sameVetCheckboxes = document.querySelectorAll('[id^="sameVet_"]');

        sameVetCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                const dogIndex = checkbox.id.split('_')[1];
                copyVetInfoFromFirstDog(dogIndex);
            }
        });
    }

    // ===========================================
    // ENHANCED VALIDATION FOR "SAME" ENTRIES
    // ===========================================

    function validateDogForms() {
        let hasErrors = false;
        const problemFields = [];

        // Get all dog forms
        const dogForms = document.querySelectorAll('.dog-form');

        dogForms.forEach((dogForm, index) => {
            const vetFields = {
                name: dogForm.querySelector('[name^="dog_"][name$="_vet_name"]'),
                phone: dogForm.querySelector('[name^="dog_"][name$="_vet_phone"]'),
                address: dogForm.querySelector('[name^="dog_"][name$="_vet_address"]')
            };

            // Check for "same" entries in vet fields
            Object.entries(vetFields).forEach(([fieldType, field]) => {
                if (field && field.value) {
                    const value = field.value.toLowerCase().trim();

                    // Check for variations of "same"
                    const sameVariations = [
                        'same', 'same as above', 'same as before', 'same as first',
                        'same as dog 1', 'same vet', 'as above', 'ditto', '"',
                        'see above', 'as before', 'identical', '^^', '^',
                        'same practice', 'same clinic', 'duplicate'
                    ];

                    if (sameVariations.some(variation => value === variation || value.includes(variation))) {
                        // Mark field as invalid
                        field.classList.add('invalid-same-entry');
                        field.classList.remove('is-invalid'); // Remove standard invalid class

                        // Remove existing warning
                        const existingWarning = field.parentNode.querySelector('.same-entry-warning');
                        if (existingWarning) existingWarning.remove();

                        // Add custom warning message
                        const warningDiv = document.createElement('div');
                        warningDiv.className = 'same-entry-warning';
                        warningDiv.innerHTML = `Please enter the actual ${fieldType === 'name' ? 'vet practice name' : fieldType === 'phone' ? 'phone number' : 'address'} - we need complete information for emergencies`;

                        field.parentNode.insertBefore(warningDiv, field.nextSibling);

                        hasErrors = true;
                        problemFields.push(`Dog ${index + 1} - Vet ${fieldType}`);
                    } else {
                        // Remove warning if field is now valid
                        field.classList.remove('invalid-same-entry');
                        const existingWarning = field.parentNode.querySelector('.same-entry-warning');
                        if (existingWarning) existingWarning.remove();
                    }
                }
            });
        });

        return { valid: !hasErrors, problemFields };
    }

    // Enhanced form submission validation
    function validateAllDogFormsBeforeSubmit() {
        const validation = validateDogForms();

        if (!validation.valid) {
            // Show comprehensive error message
            const errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-warning error-message';
            errorAlert.innerHTML = `
            <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Please Complete Vet Information</h6>
            <p class="mb-2">We found some fields marked as "same" - please enter the actual veterinary details:</p>
            <ul class="mb-2">
                ${validation.problemFields.map(field => `<li>${field}</li>`).join('')}
            </ul>
            <div class="alert alert-info mt-3 mb-0">
                <strong>Tip:</strong> If all your dogs use the same vet, use the toggle switch to auto-fill the information instead of typing "same"!
            </div>
        `;

            // Insert at top of form
            const form = document.getElementById('group-walk-form') || document.getElementById('individual-walk-form');
            if (form) {
                // Remove any existing error alerts
                const existingAlerts = form.querySelectorAll('.alert.error-message');
                existingAlerts.forEach(alert => alert.remove());

                form.insertBefore(errorAlert, form.firstChild);

                // Scroll to error
                errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Remove alert after 15 seconds
                setTimeout(() => {
                    if (errorAlert.parentNode) {
                        errorAlert.remove();
                    }
                }, 15000);
            }

            return false;
        }

        return true;
    }

    // Real-time validation as user types
    function addRealTimeVetValidation() {
        document.addEventListener('input', function (e) {
            if (e.target.name && e.target.name.includes('_vet_')) {
                const value = e.target.value.toLowerCase().trim();
                const sameVariations = [
                    'same', 'as above', 'ditto', '"', 'see above',
                    'as before', 'identical', '^^', '^'
                ];

                if (sameVariations.some(variation => value.includes(variation))) {
                    // Show immediate feedback
                    e.target.classList.add('invalid-same-entry');
                    e.target.classList.remove('is-invalid');

                    // Remove existing hint
                    const existingHint = e.target.parentNode.querySelector('.same-entry-hint');
                    if (existingHint) existingHint.remove();

                    // Show tooltip or inline message
                    const hint = document.createElement('div');
                    hint.className = 'same-entry-hint text-muted small mt-1';
                    hint.innerHTML = '<i class="bi bi-lightbulb me-1"></i>Tip: Use the "Same vet" toggle above to auto-fill this information!';
                    e.target.parentNode.insertBefore(hint, e.target.nextSibling);

                    // Remove hint after 8 seconds
                    setTimeout(() => {
                        if (hint.parentNode) hint.remove();
                    }, 8000);
                } else {
                    e.target.classList.remove('invalid-same-entry');
                    const hint = e.target.parentNode.querySelector('.same-entry-hint');
                    if (hint) hint.remove();
                }
            }
        });
    }

    // Enhanced form submission handlers with validation
    function enhancedHandleGroupFormSubmit(e) {
        e.preventDefault();

        // First validate for "same" entries
        if (!validateAllDogFormsBeforeSubmit()) {
            return; // Stop submission if validation fails
        }

        // Continue with existing validation...
        if (selectedSlots.length === 0) {
            showGenericError('group-walk-form', 'Please select at least one time slot.');
            return;
        }

        // Rest of existing submission logic...
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        const loadingText = isMultiBookingMode && selectedSlots.length > 1
            ? `<span class="spinner-border spinner-border-sm me-2"></span>Processing ${selectedSlots.length} bookings...`
            : '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

        submitBtn.innerHTML = loadingText;
        submitBtn.disabled = true;

        submitGroupWalkForm().finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }

    function enhancedHandleIndividualFormSubmit(e) {
        e.preventDefault();

        // First validate for "same" entries
        if (!validateAllDogFormsBeforeSubmit()) {
            return; // Stop submission if validation fails
        }

        // Continue with existing individual form submission logic...
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        submitBtn.disabled = true;

        submitIndividualWalkForm().finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }

    // Function to manually trigger validation (useful for testing)
    function triggerVetValidation() {
        const validation = validateDogForms();
        console.log('Validation results:', validation);
        return validation;
    }

    // Initialize enhanced validation when forms are loaded
    function initializeEnhancedValidation() {
        // Add real-time validation
        addRealTimeVetValidation();

        // Replace existing form submission handlers with enhanced versions
        const groupForm = document.getElementById('group-walk-form');
        if (groupForm) {
            // Remove existing listener
            groupForm.removeEventListener('submit', handleGroupFormSubmit);
            // Add enhanced listener
            groupForm.addEventListener('submit', enhancedHandleGroupFormSubmit);
        }

        const individualForm = document.getElementById('individual-walk-form');
        if (individualForm) {
            // Remove existing listener  
            individualForm.removeEventListener('submit', handleIndividualFormSubmit);
            // Add enhanced listener
            individualForm.addEventListener('submit', enhancedHandleIndividualFormSubmit);
        }
    }

    // Validation for specific common problematic entries
    function detectProblematicEntries(value) {
        const problematicPatterns = [
            /^same$/i,
            /^"$/,
            /^ditto$/i,
            /^as above$/i,
            /^see above$/i,
            /^same as/i,
            /^identical$/i,
            /^\^+$/,
            /same vet/i,
            /same clinic/i,
            /same practice/i
        ];

        return problematicPatterns.some(pattern => pattern.test(value.trim()));
    }

    // Export validation functions for external use
    window.bookingValidation = {
        validateDogForms,
        validateAllDogFormsBeforeSubmit,
        triggerVetValidation,
        detectProblematicEntries
    };
    
    // ===========================================
    // INDIVIDUAL WALK FORM HANDLERS
    // ===========================================
    
    async function initializeIndividualWalkForm() {
        loadBasicIndividualForm();
        
        const timeChoice = document.getElementById('preferred_time_choice');
        const numDogsSelector = document.getElementById('ind_number_of_dogs');
        const preferredDate = document.getElementById('preferred_date');
        
        if (preferredDate) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            preferredDate.min = tomorrow.toISOString().split('T')[0];
        }
        
        if (timeChoice) {
            timeChoice.removeEventListener('change', handleTimeChoice);
            timeChoice.addEventListener('change', handleTimeChoice);
        }
        
        if (numDogsSelector) {
            numDogsSelector.removeEventListener('change', handleIndividualNumDogs);
            numDogsSelector.addEventListener('change', handleIndividualNumDogs);
        }
        
        const individualForm = document.getElementById('individual-walk-form');
        if (individualForm) {
            individualForm.removeEventListener('submit', handleIndividualFormSubmit);
            individualForm.addEventListener('submit', handleIndividualFormSubmit);
        }
        
        addRealTimeValidation();
        initializeEnhancedValidation();
    }
    
    function loadBasicIndividualForm() {
        const individualForm = document.getElementById('individual-walk-form');
        if (!individualForm) return;
        
        individualForm.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
            
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
                            <option value="early_morning">Early Morning (6:00-8:00 AM)</option>
                            <option value="late_evening">Late Evening (9:00-11:00 PM)</option>
                            <option value="flexible">Flexible - let us suggest a time</option>
                            <option value="custom">Other specific time</option>
                        </select>
                    </div>
                </div>
                
                <div class="mb-3" id="custom-time-container" style="display: none;">
                    <label for="preferred_time" class="form-label">Specify Your Preferred Time</label>
                    <input type="text" class="form-control" name="preferred_time" id="preferred_time" 
                        placeholder="e.g., 8:00 AM - 9:00 AM">
                    <div class="form-text text-danger">
                        ⚠️ Remember: 8:30 AM - 12:30 PM, 1:00 PM - 5:00 PM, and 5:00 PM - 9:00 PM are not available
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="reason_for_individual" class="form-label">Why does your dog need an individual walk? *</label>
                    <textarea class="form-control" name="reason_for_individual" id="reason_for_individual" rows="4" 
                            placeholder="Please explain your dog's specific needs (e.g., anxiety around other dogs, medical requirements, behavioral concerns, in training, etc.)" required></textarea>
                </div>
            </div>

            <div class="mb-4">
                <h5 class="mb-3">Dog Details</h5>
                <div id="individual-dog-forms-container"></div>
            </div>

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
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        submitBtn.disabled = true;
        
        submitIndividualWalkForm().finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    }
    
    async function submitIndividualWalkForm() {
        const formData = new FormData();
        const form = document.getElementById('individual-walk-form');
        if (!form) return;

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

        const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        } else {
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

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                if (bookingMainContent) {
                    bookingMainContent.innerHTML = result.html;
                }
                
                setTimeout(() => {
                    bookingMainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
                
            } else {
                showDetailedFormErrors('individual-walk-form', result.errors, result.message);
            }
        } catch (error) {
            console.error('Error submitting form:', error);

            if (error.name === 'TypeError' || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                showTechnicalError('individual-walk-form', 'network');
            } else if (error.message.includes('Server error: 5')) {
                showTechnicalError('individual-walk-form', 'server');
            } else if (error.message.includes('timeout')) {
                showTechnicalError('individual-walk-form', 'timeout');
            } else {
                showTechnicalError('individual-walk-form', 'generic');
            }
        }
    }
    
    // ===========================================
    // ERROR HANDLING AND VALIDATION
    // ===========================================

    function showDetailedFormErrors(formId, errors, message) {
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

        const form = document.getElementById(formId);
        if (!form) return;

        let hasFieldErrors = false;
        let errorSummary = [];

        if (errors && typeof errors === 'object') {
            Object.keys(errors).forEach(fieldName => {
                let fieldErrors = errors[fieldName];

                // Convert to string and clean up the messy formatting
                let errorText = '';
                if (Array.isArray(fieldErrors)) {
                    errorText = fieldErrors.join(' ').toString();
                } else {
                    errorText = fieldErrors.toString();
                }

                // Remove all the messy brackets and quotes
                errorText = errorText.replace(/^\["|"\]$/g, '');
                errorText = errorText.replace(/^\[|\]$/g, '');
                errorText = errorText.replace(/^"|"$/g, '');

                // If the error contains the field name already, extract just the message
                if (errorText.includes(':')) {
                    const parts = errorText.split(':');
                    if (parts.length > 1) {
                        errorText = parts.slice(1).join(':').trim();
                    }
                }

                let field = null;
                let displayFieldName = fieldName;

                if (fieldName === 'general') {
                    errorSummary.push(errorText);
                    return;
                } else if (fieldName.startsWith('dog_')) {
                    field = form.querySelector(`[name="${fieldName}"]`);
                    const parts = fieldName.split('_');
                    if (parts.length >= 3) {
                        const dogNum = parseInt(parts[1]) + 1;
                        const fieldType = parts.slice(2).join('_').replace(/_/g, ' ');
                        displayFieldName = `Dog ${dogNum} ${fieldType}`;
                    }
                } else {
                    field = form.querySelector(`[name="${fieldName}"]`);
                    displayFieldName = fieldName.replace('customer_', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                }

                if (field) {
                    field.classList.add('is-invalid');
                    hasFieldErrors = true;

                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback error-message';
                    errorDiv.textContent = errorText;
                    field.parentNode.insertBefore(errorDiv, field.nextSibling);
                }

                errorSummary.push(`${displayFieldName}: ${errorText}`);
            });
        }

        const alert = document.createElement('div');
        alert.className = 'alert alert-danger error-message mt-3';

        let alertContent = '<div class="d-flex align-items-start">';
        alertContent += '<i class="bi bi-exclamation-triangle-fill me-2 text-danger" style="font-size: 1.2em; margin-top: 2px;"></i>';
        alertContent += '<div>';

        if (hasFieldErrors) {
            alertContent += '<h6 class="mb-2">Please correct the following issues:</h6>';
            alertContent += '<ul class="mb-0 ps-3">';
            errorSummary.forEach(error => {
                alertContent += `<li>${error}</li>`;
            });
            alertContent += '</ul>';
        } else if (message) {
            alertContent += `<h6 class="mb-1">Booking Error</h6><p class="mb-0">${message}</p>`;
        } else {
            alertContent += '<h6 class="mb-1">Validation Error</h6><p class="mb-0">Please check your information and try again.</p>';
        }

        alertContent += '</div></div>';
        alert.innerHTML = alertContent;

        form.insertBefore(alert, form.firstChild);

        const firstError = document.querySelector('.is-invalid') || alert;
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function showTechnicalError(formId, errorType) {
        const form = document.getElementById(formId);
        if (!form) return;

        document.querySelectorAll('.error-message').forEach(el => el.remove());

        const alert = document.createElement('div');
        alert.className = 'alert alert-warning error-message mt-3';

        let alertContent = '<div class="d-flex align-items-start">';
        alertContent += '<i class="bi bi-exclamation-triangle-fill me-2 text-warning" style="font-size: 1.2em; margin-top: 2px;"></i>';
        alertContent += '<div>';

        switch (errorType) {
            case 'network':
                alertContent += '<h6 class="mb-1">Connection Problem</h6>';
                alertContent += '<p class="mb-2">Unable to connect to our booking system. This could be due to:</p>';
                alertContent += '<ul class="mb-2 ps-3"><li>Poor internet connection</li><li>Temporary network issues</li><li>Browser blocking the request</li></ul>';
                alertContent += '<p class="mb-0"><strong>What to try:</strong> Check your internet connection and try again, or contact us directly at <a href="mailto:alex@caninecompadre.co.uk">alex@caninecompadre.co.uk</a></p>';
                break;
            case 'server':
                alertContent += '<h6 class="mb-1">Server Technical Difficulties</h6>';
                alertContent += '<p class="mb-2">Our booking system is experiencing technical difficulties. This is temporary and not related to your booking information.</p>';
                alertContent += '<p class="mb-0"><strong>What to try:</strong> Please wait a few minutes and try again, or contact us directly at <a href="mailto:alex@caninecompadre.co.uk">alex@caninecompadre.co.uk</a></p>';
                break;
            case 'timeout':
                alertContent += '<h6 class="mb-1">Request Timeout</h6>';
                alertContent += '<p class="mb-2">Your booking request took too long to process. This could be due to high demand or slow connection.</p>';
                alertContent += '<p class="mb-0"><strong>What to try:</strong> Please try again with a stable internet connection, or contact us directly at <a href="mailto:alex@caninecompadre.co.uk">alex@caninecompadre.co.uk</a></p>';
                break;
            default:
                alertContent += '<h6 class="mb-1">Technical Difficulties</h6>';
                alertContent += '<p class="mb-2">We\'re experiencing unexpected technical issues that are preventing your booking from being processed.</p>';
                alertContent += '<p class="mb-0"><strong>What to try:</strong> Please refresh the page and try again, or contact us directly at <a href="mailto:alex@caninecompadre.co.uk">alex@caninecompadre.co.uk</a></p>';
        }

        alertContent += '<div class="mt-3">';
        alertContent += '<button class="btn btn-outline-primary btn-sm me-2" onclick="window.location.reload()"><i class="bi bi-arrow-clockwise me-1"></i>Refresh Page</button>';
        alertContent += '<a href="mailto:alex@caninecompadre.co.uk" class="btn btn-outline-success btn-sm"><i class="bi bi-envelope me-1"></i>Email Us Instead</a>';
        alertContent += '</div></div></div>';
        alert.innerHTML = alertContent;

        form.insertBefore(alert, form.firstChild);
        alert.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function showFormErrors(formId, errors, message) {
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        
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
        
        if (errors) {
            Object.keys(errors).forEach(fieldName => {
                const field = document.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    field.classList.add('is-invalid');
                    
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback error-message';
                    errorDiv.textContent = Array.isArray(errors[fieldName]) ? errors[fieldName].join(', ') : errors[fieldName];
                    
                    field.parentNode.insertBefore(errorDiv, field.nextSibling);
                }
            });
        }
        
        const firstError = document.querySelector('.is-invalid, .alert-danger');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    function showGenericError(formId, message) {
        const form = document.getElementById(formId);
        if (form) {
            document.querySelectorAll('.error-message').forEach(el => el.remove());
            
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger error-message mt-3';
            alert.innerHTML = `
                <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Error</h6>
                <p class="mb-0">${message}</p>
            `;
            form.insertBefore(alert, form.firstChild);
            
            alert.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    function addRealTimeValidation() {
        document.querySelectorAll('input[type="email"]').forEach(emailField => {
            if (!emailField.hasAttribute('data-validated')) {
                emailField.setAttribute('data-validated', 'true');
                emailField.addEventListener('blur', function() {
                    validateField(this, validateEmail(this.value), 'Please enter a valid email address');
                });
            }
        });
        
        document.querySelectorAll('input[type="tel"]').forEach(phoneField => {
            if (!phoneField.hasAttribute('data-validated')) {
                phoneField.setAttribute('data-validated', 'true');
                phoneField.addEventListener('blur', function() {
                    validateField(this, validatePhone(this.value), 'Please enter a valid phone number');
                });
            }
        });
        
        document.querySelectorAll('input[name="customer_postcode"], input[name*="postcode"]').forEach(postcodeField => {
            if (!postcodeField.hasAttribute('data-validated')) {
                postcodeField.setAttribute('data-validated', 'true');
                
                postcodeField.addEventListener('input', function() {
                    this.value = this.value.toUpperCase();
                });
                
                postcodeField.addEventListener('blur', function() {
                    if (this.value) {
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
            
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) existingError.remove();
            
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
        const serviceSelection = document.getElementById('booking-service-selection');
        const backToSelection = document.getElementById('back-to-selection');
        const groupForm = document.getElementById('group-booking-form');
        const individualForm = document.getElementById('individual-booking-form');
        
        if (serviceSelection) serviceSelection.style.display = 'block';
        if (backToSelection) backToSelection.style.display = 'none';
        if (groupForm) groupForm.style.display = 'none';
        if (individualForm) individualForm.style.display = 'none';
        
        selectedSlots = [];
        currentBookingType = null;
        availabilityData = [];
        isMultiBookingMode = false;
        
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    };
    
    // SLOT SELECTION FUNCTION (UPDATED VERSION)
    window.selectSlot = function(date, timeSlot, timeDisplay, dateDisplay) {
        console.log('selectSlot called:', date, timeSlot, timeDisplay, dateDisplay);
        
        const slotData = { date, timeSlot, timeDisplay, dateDisplay };
        
        if (isMultiBookingMode) {
            // Multi-slot selection
            const existingIndex = selectedSlots.findIndex(slot => 
                slot.date === slotData.date && slot.timeSlot === slotData.timeSlot
            );
            
            if (existingIndex >= 0) {
                selectedSlots.splice(existingIndex, 1);
            } else {
                selectedSlots.push(slotData);
            }
            
            updateCalendarDisplay();
            updateSelectionSummary();
            updateSubmitButtonText();
            
            // Only show next steps if we have selections
            if (selectedSlots.length > 0) {
                showStep('step-3-details');
                showStep('step-4-dogs');
                showStep('step-5-submit');
            }
        } else {
            // Single slot selection - UPDATED LOGIC
            selectedSlots = [slotData];
            
            // Visual selection
            document.querySelectorAll('.day-card.selected, .time-slot.selected').forEach(el => {
                el.classList.remove('selected');
            });
            
            const dayCard = document.querySelector(`[data-date="${date}"]`);
            if (dayCard) {
                const timeSlotEl = dayCard.querySelector(`[data-time-slot="${timeSlot}"]`);
                
                dayCard.classList.add('selected');
                if (timeSlotEl) timeSlotEl.classList.add('selected');
            }
            
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
            
            // Show multi-booking toggle after first selection
            showMultiBookingToggle();
            
            // Show continue button instead of automatically proceeding
            showContinueButton();
        }
    };
    
    addRealTimeValidation();
    
    console.log('Booking system JavaScript loaded successfully with multi-booking support!');
});