/**
 * Spring Calculator - JavaScript
 * Validation, formatting and automatic detection system for forms
 * Author: Spring Calculator System
 * Date: 2026
 *
 * GENERAL DESCRIPTION:
 * This script provides a complete validation, formatting and field control
 * system for the helical spring calculator. It includes:
 *
 * 1. Automatic number detection and formatting
 * 2. Smart handling of materials and their properties
 * 3. Dynamic field control based on the spring type
 * 4. Automatic synchronization of diameter calculations
 * 5. Smart locking of mathematically related fields
 * 6. Full form validation before submission
 *
 * The functions are organized from simplest (formatting) to most complex (synchronization).
 */

// Automatic detection and formatting for numeric inputs
/**
 * Sets up automatic detection and formatting of numeric inputs.
 * - Converts commas to dots as the decimal separator
 * - Validates that they only contain valid numbers
 * - Changes the border color based on the input's validity
 * - Rounds to 3 decimals when losing focus
 */
function setupFormatDetection() {
    // Detect all numeric inputs
    const numericInputs = document.querySelectorAll('input[type="number"]');

    numericInputs.forEach(input => {
        // Auto-format while typing
        input.addEventListener('input', function (e) {
            let value = e.target.value;

            // Detect decimal separator (dot or comma)
            if (value.includes(',')) {
                // Convert comma to dot for compatibility
                value = value.replace(',', '.');
                e.target.value = value;
            }

            // Validate numeric format
            const isValidNumber = /^-?\d*\.?\d*$/.test(value);

            // Apply styles based on validation
            if (value && !isValidNumber) {
                e.target.style.borderColor = '#dc3545';
                e.target.style.backgroundColor = '#fff5f5';
            } else {
                e.target.style.borderColor = '#28a745';
                e.target.style.backgroundColor = '#f8fff8';
            }
        });

        // Format when losing focus
        input.addEventListener('blur', function (e) {
            let value = parseFloat(e.target.value);
            if (!isNaN(value)) {
                // Format to 3 decimals if needed
                if (value % 1 !== 0) {
                    e.target.value = value.toFixed(3).replace(/\.?0+$/, '');
                }
            }
            // Reset styles
            e.target.style.borderColor = '#ced4da';
            e.target.style.backgroundColor = 'white';
        });
    });
}

// Detect material selection and auto-fill properties
/**
 * Detects when a material is selected and automatically fills in its properties:
 * - Fills in the shear modulus field if it is empty
 * - Shows the material's mechanical properties information
 * - Visually highlights the auto-filled field
 */
function setupMaterialDetection() {
    const materialSelect = document.getElementById('material');
    const moduloInput = document.querySelector('input[name="modulo_corte"]');

    if (materialSelect && moduloInput) {
        materialSelect.addEventListener('change', function () {
            const selected = this.options[this.selectedIndex];
            const shearModulus = selected.getAttribute('data-shear-modulus');
            const elasticFactor = selected.getAttribute('data-elastic-factor');

            // Auto-fill shear modulus if available
            if (shearModulus && !moduloInput.value) {
                moduloInput.value = shearModulus;
                moduloInput.style.backgroundColor = '#e7f3ff';
                setTimeout(() => {
                    moduloInput.style.backgroundColor = 'white';
                }, 2000);
            }

            // Show material information
            showMaterialInfo(selected, shearModulus, elasticFactor);
        });
    }
}

// Show information for the selected material
/**
 * Shows an information panel with the technical properties of the selected material.
 * Includes:
 * - Shear modulus (in N/mm²)
 * - Elastic limit factor
 * - Hidden if the material has no available properties
 * @param {HTMLOptionElement} selectedOption - The selected option from the select
 * @param {string} shearModulus - Material's shear modulus
 * @param {string} elasticFactor - Material's elastic factor
 */
function showMaterialInfo(selectedOption, shearModulus, elasticFactor) {
    let materialInfo = document.getElementById('material-info');
    if (!materialInfo) {
        materialInfo = document.createElement('div');
        materialInfo.id = 'material-info';
        materialInfo.style.cssText = `
            display: block;
            margin-top: 10px;
            padding: 8px;
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            border-radius: 4px;
            font-size: 13px;
        `;
        document.getElementById('material').parentNode.appendChild(materialInfo);
    }

    if (shearModulus && elasticFactor) {
        materialInfo.innerHTML = `
            <strong>📊 ${gettext('Propiedades del Material')}:</strong><br>
            <span style="color: #0056b3;">• ${gettext('Módulo de corte')}: <strong>${formatNumber(shearModulus)} N/mm²</strong></span><br>
            <span style="color: #0056b3;">• ${gettext('Factor límite elástico')}: <strong>${formatNumber(elasticFactor)}</strong></span>
        `;
        materialInfo.style.display = 'block';
    } else {
        materialInfo.style.display = 'none';
    }
}

// Format numbers for display
/**
 * Formats numbers for visual display using Spanish regional settings.
 * - If it's an integer: shows it without decimals (e.g. 123)
 * - If it's a decimal: shows up to 3 decimals (e.g. 123,456)
 * - Uses a thousands separator (dot) and comma as the decimal separator
 * @param {number|string} num - Number to format
 * @returns {string} Number formatted for display
 */
function formatNumber(num) {
    const number = parseFloat(num);
    if (isNaN(number)) return num;

    // Detect whether it's an integer or a decimal
    if (number % 1 === 0) {
        return number.toLocaleString('es-ES');
    } else {
        return number.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 3 });
    }
}

// Form validation before submission
/**
 * Validates that all required fields are filled in before submitting the form.
 * - Prevents submission if there are empty fields
 * - Visually marks invalid fields in red
 * - Shows an alert indicating that the required fields must be filled in
 */
function setupFormValidation() {
    const form = document.querySelector('form');
    form.addEventListener('submit', function (e) {
        const requiredInputs = form.querySelectorAll('input[required], select[required]');
        let hasErrors = false;

        requiredInputs.forEach(input => {
            const isHidden = input.offsetParent === null;
            if (isHidden) {
                return;
            }
            if (!input.value) {
                input.style.borderColor = '#dc3545';
                input.style.backgroundColor = '#fff5f5';
                hasErrors = true;
            }
        });

        if (hasErrors) {
            e.preventDefault();
            alert('⚠️ ' + gettext('Por favor complete todos los campos obligatorios'));
        }
    });
}

/**
 * Sets up the spring type selector (compression/extension).
 * - Dynamically changes fields and labels based on the selected type
 * - Shows/hides extension-specific fields (initial tension)
 * - Updates the "initial/final length" labels based on the type
 * - Manages the visual end options based on the type
 * - Automatically selects a valid default end
 */
function setupSpringTypeSelector() {
    const typeSelect = document.getElementById('tipo_muelle');
    const tensionGroup = document.getElementById('traccion_tension_group');
    const tensionInput = document.getElementById('tension_inicial');
    const initialLabel = document.querySelector('label[for="longitud_inicial"]');
    const finalLabel = document.querySelector('label[for="longitud_final"]');
    const compresionEndOptions = document.querySelectorAll('.compresion-end-option');
    const traccionEndOptions = document.querySelectorAll('.traccion-end-option');
    const endOptions = document.querySelectorAll('.end-option');
    const endHiddenInput = document.getElementById('tipo_final');

    if (!typeSelect) {
        return;
    }

    const updateByType = () => {
        const isTraccion = typeSelect.value === 'traccion';

        if (tensionGroup) {
            tensionGroup.style.display = isTraccion ? 'block' : 'none';
        }

        if (tensionInput) {
            tensionInput.required = isTraccion;
        }

        if (initialLabel) {
            initialLabel.textContent = isTraccion ? gettext('Longitud inicial estirada (mm):') : gettext('Longitud inicial (mm):');
        }

        if (finalLabel) {
            finalLabel.textContent = isTraccion ? gettext('Longitud final estirada (mm):') : gettext('Longitud final (mm):');
        }

        compresionEndOptions.forEach(option => {
            option.style.display = isTraccion ? 'none' : '';
        });

        traccionEndOptions.forEach(option => {
            option.style.display = isTraccion ? '' : 'none';
        });

        if (endHiddenInput) {
            const compresionValues = ['abierto', 'cerrado', 'semi-cerrado', 'rectificado'];
            const traccionValues = [
                'anillo_doble_aleman_entero_centrado',
                'anillo_doble_aleman_entero_lateral',
                'anillo_simple_aleman_centrado',
                'static/images/anillo_simple_aleman_entero_lateral.png',
                'static/images/anillo_simple_aleman_entero_centrado.png',
                'anillo_especial'
            ];

            const validValues = isTraccion ? traccionValues : compresionValues;
            const defaultValue = isTraccion ? 'anillo_doble_aleman_entero_centrado' : 'rectificado';

            if (!validValues.includes(endHiddenInput.value)) {
                const defaultOption = document.querySelector(`.end-option[data-value="${defaultValue}"]`);
                if (defaultOption) {
                    endOptions.forEach(option => option.classList.remove('selected'));
                    defaultOption.classList.add('selected');
                    endHiddenInput.value = defaultValue;
                }
            }
        }
    };

    typeSelect.addEventListener('change', updateByType);
    updateByType();
}

// Set up the visual selector for spring ends
/**
 * Sets up a visual selector to choose the spring's end type.
 * - Allows visually selecting between different end options
 * - Stores the selected value in a hidden input
 * - Includes visual animations on select and hover
 * - Only one option can be selected at a time
 */
function setupSpringEndSelector() {
    const endOptions = document.querySelectorAll('.end-option');
    const hiddenInput = document.querySelector('input[name="tipo_final"]');

    endOptions.forEach(option => {
        option.addEventListener('click', function () {
            // Remove previous selection
            endOptions.forEach(opt => opt.classList.remove('selected'));

            // Select the new option
            this.classList.add('selected');

            // Update the value in the hidden input
            const value = this.getAttribute('data-value');
            hiddenInput.value = value;

            // Confirmation animation
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'translateY(-2px)';
            }, 150);

            // Log for debugging
            console.log('🌀 Selected end type:', value);
        });

        // Improved hover effect
        option.addEventListener('mouseenter', function () {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(-1px)';
            }
        });

        option.addEventListener('mouseleave', function () {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'none';
            }
        });
    });
}

// Set up auto-detection of material properties (compatibility)
/**
 * Detects the properties of the selected material and displays them on screen.
 * Complements setupMaterialDetection() to ensure compatibility.
 * - Triggered when the selected material changes
 * - Shows technical material information (shear modulus, elastic factor)
 */
function setupMaterialPropertyDetection() {
    const materialSelect = document.getElementById('material');
    if (materialSelect) {
        materialSelect.addEventListener('change', function () {
            const selected = this.options[this.selectedIndex];
            const shearModulus = selected.getAttribute('data-shear-modulus');
            const elasticFactor = selected.getAttribute('data-elastic-factor');

            // Integration with the format detection system
            showMaterialInfo(selected, shearModulus, elasticFactor);
        });
    }
}



// Initialize the system once the DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    setupFormatDetection();
    setupMaterialDetection();
    setupFormValidation();
    setupSpringTypeSelector();
    setupSpringEndSelector();
    setupMaterialPropertyDetection();
    setupGeometryFieldControlAndDiameterSync();

    // Show loading message in the console
    console.log('🔧 HTML format detection system activated');
    console.log('🌀 Calculadora de Muelles initialized');
});
