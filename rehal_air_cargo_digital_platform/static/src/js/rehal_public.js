/** @odoo-module **/

// Public website JavaScript for Rehal Air Cargo

document.addEventListener('DOMContentLoaded', function() {
    // Spot card click handlers
    const spotCards = document.querySelectorAll('.spot-card');
    spotCards.forEach(card => {
        card.addEventListener('click', function() {
            // Add visual feedback when spot is clicked
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // Form validation
    const bookingForm = document.querySelector('.needs-validation');
    if (bookingForm) {
        bookingForm.addEventListener('submit', function(event) {
            if (!bookingForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            bookingForm.classList.add('was-validated');
        }, false);
    }
    
    // Dynamic spot capacity check
    const spotSelect = document.querySelector('select[name="spot_id"]');
    const weightInput = document.querySelector('input[name="weight"]');
    
    if (spotSelect && weightInput) {
        function validateWeight() {
            const selectedOption = spotSelect.options[spotSelect.selectedIndex];
            if (selectedOption && selectedOption.value) {
                const availableText = selectedOption.text;
                const match = availableText.match(/Available: ([\d.]+) kg/);
                if (match) {
                    const available = parseFloat(match[1]);
                    const weight = parseFloat(weightInput.value) || 0;
                    
                    if (weight > available) {
                        weightInput.setCustomValidity(`Weight cannot exceed available capacity (${available} kg)`);
                        weightInput.classList.add('is-invalid');
                    } else {
                        weightInput.setCustomValidity('');
                        weightInput.classList.remove('is-invalid');
                    }
                }
            }
        }
        
        spotSelect.addEventListener('change', validateWeight);
        weightInput.addEventListener('input', validateWeight);
    }
});

