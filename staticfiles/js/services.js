// services.js - Services toggle functionality
document.addEventListener('DOMContentLoaded', function () {
    const content = {
        group: `
            <div class="service-description p-4">
                <h4 style="text-decoration: underline;">Group Walks</h4>
                <p>Our primary service features socialized group walks available twice daily, seven days a week.
                These walks allow dogs to interact, exercise, and enjoy the great outdoors together.
                We also offer occasional evening walks for pet parents who work night shifts.</p>
                <p>Please be aware that all our services are only aviable to you if you are within a
                10 mile raduis Croyde, North Devon!</p>
            </div>
        `,
        individual: `
            <div class="service-description p-4">
                <h4 style="text-decoration: underline;">Individual Walks</h4>
                <p>We provide one-on-one walks for dogs that need personalized attention or don't do well with others.
                These are scheduled by appointment to match your dog's needs and your availability.</p>
                <p>Please be aware that all our services are only available to you if you are within a
                10 mile raduis Croyde, North Devon!</p>
                <p class="text-center mt-3"><strong>Please note: These walks require approval and booking confirmation.</strong></p>
            </div>
        `
    };

    const detailsPlaceholder = document.getElementById('service-details-placeholder');
    let currentType = null;
    let currentContainer = null; // tracks the DOM container holding current content

    document.querySelectorAll('.service-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const type = this.dataset.service;
            const cardCol = this.closest('.col-12');
            const screenWidth = window.innerWidth;

            // Small screen logic: if same card already has content below, toggle it off
            if (screenWidth < 768 && currentContainer === cardCol) {
                const existing = cardCol.nextElementSibling;
                if (existing && existing.classList.contains('service-description-inline')) {
                    existing.remove();
                    currentType = null;
                    currentContainer = null;
                    return;
                }
            }

            // Large screen logic: if same type already shown, toggle off
            if (screenWidth >= 768 && currentType === type) {
                detailsPlaceholder.innerHTML = '';
                currentType = null;
                currentContainer = null;
                return;
            }

            // Clear existing content
            document.querySelectorAll('.service-description-inline').forEach(el => el.remove());
            detailsPlaceholder.innerHTML = '';

            const html = content[type];

            if (screenWidth < 768) {
                // Small screen: inject after clicked card
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const inlineDiv = tempDiv.firstElementChild;
                inlineDiv.classList.add('service-description-inline', 'mt-3');
                cardCol.parentNode.insertBefore(inlineDiv, cardCol.nextSibling);
                currentContainer = cardCol;
            } else {
                // Large screen: show in placeholder
                detailsPlaceholder.innerHTML = html;
                currentContainer = detailsPlaceholder;
            }

            currentType = type;
        });
    });
});