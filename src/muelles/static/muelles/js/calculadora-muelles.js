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
        // Comma -> dot conversion for "," typed into type=number is handled
        // globally by global/js/decimal-comma.js (loaded from base.html).

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

// Pitch vs wire-diameter validation
/**
 * Live check on the pitch field(s): the coil pitch can never be smaller than
 * the wire diameter, otherwise the coils would physically overlap.
 *
 * When the value is too low it:
 *   - marks the field in red,
 *   - shows a floating pop-up message next to the field,
 *   - blocks form submission (via setCustomValidity), so the calculation is
 *     never sent to the server and no Python error can reach the screen.
 *
 * Works on every calculator: pitch, pitch_1/2/3, pitch_superior, pitch_inferior.
 */
function setupPitchValidation() {
    const form = document.querySelector('form');
    if (!form) {
        return;
    }

    const wireInput = document.getElementById('diametro_hilo')
        || form.querySelector('input[name="diametro_hilo"]');
    // Only fields the user actually types a pitch into: skip read-only /
    // calculated fields (e.g. the compression calculator shows the derived
    // pitch in a read-only box).
    const pitchInputs = Array.prototype.slice.call(
        form.querySelectorAll('input[name^="pitch"]')
    ).filter(function (input) {
        return !input.readOnly;
    });
    if (!wireInput || !pitchInputs.length) {
        return;
    }

    let popup = document.querySelector('.pitch-warning-popup');
    if (!popup) {
        popup = document.createElement('div');
        popup.className = 'pitch-warning-popup';
        popup.setAttribute('role', 'alert');
        popup.style.cssText = [
            'position: fixed',
            'z-index: 10000',
            'max-width: 260px',
            'padding: 10px 12px',
            'border-radius: 8px',
            'background: #b42318',
            'color: #fff',
            'font-size: 13px',
            'line-height: 1.35',
            'box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25)',
            'opacity: 0',
            'pointer-events: none',
            'transition: opacity 0.15s ease'
        ].join(';');
        document.body.appendChild(popup);
    }

    let hideTimer = null;

    function parseValue(raw) {
        if (raw === null || raw === undefined || raw === '') {
            return null;
        }
        const parsed = Number(String(raw).replace(',', '.'));
        return Number.isFinite(parsed) ? parsed : null;
    }

    function warningText() {
        const wire = parseValue(wireInput.value);
        let text = gettext('El paso no puede ser inferior al diámetro del hilo');
        if (wire !== null && wire > 0) {
            text += ' (' + formatNumber(wire) + ' mm)';
        }
        return '⚠️ ' + text + '.';
    }

    function showPopup(target) {
        popup.textContent = warningText();
        popup.style.opacity = '1';
        const rect = target.getBoundingClientRect();
        let left = rect.left;
        const maxLeft = window.innerWidth - popup.offsetWidth - 8;
        if (left > maxLeft) {
            left = Math.max(8, maxLeft);
        }
        let top = rect.bottom + 8;
        if (top + popup.offsetHeight > window.innerHeight - 8) {
            top = rect.top - popup.offsetHeight - 8;
        }
        popup.style.left = left + 'px';
        popup.style.top = top + 'px';
        if (hideTimer) {
            clearTimeout(hideTimer);
        }
        hideTimer = setTimeout(function () {
            popup.style.opacity = '0';
        }, 4500);
    }

    function validate(pitchInput, showMessage) {
        const wire = parseValue(wireInput.value);
        const pitch = parseValue(pitchInput.value);

        if (wire === null || wire <= 0 || pitch === null || pitch <= 0) {
            pitchInput.setCustomValidity('');
            pitchInput.style.borderColor = '';
            pitchInput.style.backgroundColor = '';
            return true;
        }

        // 1 micron tolerance so an exact pitch === wire diameter is accepted.
        const tooLow = pitch < wire - 0.001;
        if (tooLow) {
            pitchInput.setCustomValidity(
                gettext('El paso no puede ser inferior al diámetro del hilo.')
            );
            pitchInput.style.borderColor = '#dc3545';
            pitchInput.style.backgroundColor = '#fff5f5';
            if (showMessage) {
                showPopup(pitchInput);
            }
        } else {
            pitchInput.setCustomValidity('');
            pitchInput.style.borderColor = '#28a745';
            pitchInput.style.backgroundColor = '#f8fff8';
        }
        return !tooLow;
    }

    pitchInputs.forEach(function (pitchInput) {
        pitchInput.addEventListener('input', function () {
            validate(pitchInput, false);
        });
        pitchInput.addEventListener('blur', function () {
            validate(pitchInput, true);
        });
        // Fires when the form is submitted while this field is invalid.
        pitchInput.addEventListener('invalid', function (event) {
            event.preventDefault(); // replace the native bubble with our pop-up
            showPopup(pitchInput);
        });
        validate(pitchInput, false);
    });

    wireInput.addEventListener('input', function () {
        pitchInputs.forEach(function (pitchInput) {
            validate(pitchInput, false);
        });
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



// Save / load / share the current calculation
/**
 * Derives a short slug for the current calculator from the URL, e.g.
 * "/muelles/calculadora/2k/" -> "2k". Used to name the downloaded JSON file.
 * @returns {string}
 */
function calculatorSlug() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    return parts[parts.length - 1] || 'muelle';
}

/**
 * Reads every named field of the form into a plain object, skipping the
 * CSRF token. Unchecked checkboxes are recorded as false and unselected
 * radios are skipped, so the object round-trips through applyFormData().
 * @param {HTMLFormElement} form
 * @returns {Object}
 */
function collectFormData(form) {
    const data = {};
    form.querySelectorAll('input[name], select[name], textarea[name]').forEach(function (el) {
        if (el.name === 'csrfmiddlewaretoken') {
            return;
        }
        if (el.type === 'checkbox') {
            data[el.name] = el.checked;
        } else if (el.type === 'radio') {
            if (el.checked) {
                data[el.name] = el.value;
            }
        } else {
            data[el.name] = el.value;
        }
    });
    return data;
}

/**
 * Writes a plain object (as produced by collectFormData) back into the
 * form's fields, then fires input/change events so the page's own
 * listeners (material info, spring type selector, end-type selector...)
 * pick up the new values.
 * @param {HTMLFormElement} form
 * @param {Object} data
 */
function applyFormData(form, data) {
    Object.keys(data).forEach(function (name) {
        if (name === 'csrfmiddlewaretoken') {
            return;
        }
        const els = form.querySelectorAll('[name="' + name.replace(/"/g, '\\"') + '"]');
        if (!els.length) {
            return;
        }
        const first = els[0];
        if (first.type === 'checkbox') {
            first.checked = !!data[name];
        } else if (first.type === 'radio') {
            els.forEach(function (radio) {
                radio.checked = (radio.value === data[name]);
            });
        } else {
            first.value = data[name];
        }
        els.forEach(function (el) {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        });
    });

    // The end-type selector's visual state lives on CSS classes, not just
    // the hidden input the loop above already restored.
    const endHidden = form.querySelector('input[name="tipo_final"]');
    if (endHidden) {
        document.querySelectorAll('.end-option').forEach(function (opt) {
            opt.classList.toggle('selected', opt.getAttribute('data-value') === endHidden.value);
        });
    }
}

/**
 * UTF-8-safe base64 encode, so accented field values (material names,
 * labels typed with é/ñ/...) survive the round trip through a URL.
 * @param {string} text
 * @returns {string}
 */
function utf8ToBase64(text) {
    const bytes = new TextEncoder().encode(text);
    let binary = '';
    bytes.forEach(function (byte) {
        binary += String.fromCharCode(byte);
    });
    return btoa(binary);
}

/**
 * Inverse of utf8ToBase64().
 * @param {string} b64
 * @returns {string}
 */
function base64ToUtf8(b64) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return new TextDecoder().decode(bytes);
}

/**
 * Triggers a browser download of `dataObj` as a formatted JSON file.
 * @param {string} filename
 * @param {Object} dataObj
 */
function downloadJSON(filename, dataObj) {
    const blob = new Blob([JSON.stringify(dataObj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

/**
 * Wires up the "Guardar" / "Cargar" buttons shared by every spring
 * calculator:
 * - Guardar downloads the current form values as a JSON file.
 * - Cargar reads a previously saved JSON file back into the form.
 * The "Compartir por email" button is handled separately, by
 * setupCompartirModal(), since it involves a modal and a server call.
 * On load, if the page URL already carries a `datos` parameter (i.e. the
 * user followed a shared link), the form is pre-filled from it.
 */
function setupSaveLoadShare() {
    const form = document.querySelector('form');
    if (!form) {
        return;
    }

    const saveBtn = document.getElementById('guardar-btn');
    const loadBtn = document.getElementById('cargar-btn');
    const loadInput = document.getElementById('cargar-input');

    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            const data = collectFormData(form);
            const today = new Date().toISOString().slice(0, 10);
            downloadJSON('muelle-' + calculatorSlug() + '-' + today + '.json', data);
        });
    }

    if (loadBtn && loadInput) {
        loadBtn.addEventListener('click', function () {
            loadInput.click();
        });
        loadInput.addEventListener('change', function () {
            const file = loadInput.files[0];
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = function (evt) {
                try {
                    applyFormData(form, JSON.parse(evt.target.result));
                } catch (err) {
                    alert('⚠️ ' + gettext('El archivo seleccionado no es un JSON válido.'));
                }
            };
            reader.readAsText(file);
            loadInput.value = '';
        });
    }

    const sharedData = new URLSearchParams(window.location.search).get('datos');
    if (sharedData) {
        try {
            applyFormData(form, JSON.parse(base64ToUtf8(sharedData)));
        } catch (err) {
            console.warn('No se pudieron cargar los datos compartidos del enlace', err);
        }
    }
}

/**
 * Wires up the "Compartir por email" button and its modal: asks for a
 * sender and recipient address, requires a passed Google reCAPTCHA before
 * enabling the send, then POSTs the form data to the server-side
 * muelles_compartir_email endpoint, which emails a shared link from the
 * site's own account (see muelles/views/compartir_email.py). Sending never
 * happens from the visitor's own mail client.
 */
function setupCompartirModal() {
    const form = document.querySelector('form');
    const shareBtn = document.getElementById('compartir-btn');
    const overlay = document.getElementById('compartir-modal-overlay');
    if (!form || !shareBtn || !overlay) {
        return;
    }

    const shareUrl = overlay.getAttribute('data-share-url');
    const origenInput = document.getElementById('compartir-origen');
    const destinoInput = document.getElementById('compartir-destino');
    const statusBox = document.getElementById('compartir-modal-status');
    const sendBtn = document.getElementById('compartir-enviar-btn');
    const cancelBtn = document.getElementById('compartir-cancelar-btn');

    function setStatus(message, kind) {
        statusBox.textContent = message;
        statusBox.className = 'compartir-modal-status' + (kind ? ' ' + kind : '');
    }

    function closeModal() {
        overlay.style.display = 'none';
        setStatus('', null);
        if (window.grecaptcha) {
            window.grecaptcha.reset();
        }
    }

    shareBtn.addEventListener('click', function () {
        setStatus('', null);
        overlay.style.display = 'flex';
    });

    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeModal);
    }

    overlay.addEventListener('click', function (evt) {
        if (evt.target === overlay) {
            closeModal();
        }
    });

    if (sendBtn) {
        sendBtn.addEventListener('click', function () {
            const origen = origenInput.value.trim();
            const destino = destinoInput.value.trim();
            if (!origen || !destino) {
                setStatus(gettext('Completa ambos emails.'), 'error');
                return;
            }

            const recaptchaResponse = window.grecaptcha ? window.grecaptcha.getResponse() : '';
            if (!recaptchaResponse) {
                setStatus(gettext('Confirma que no eres un robot.'), 'error');
                return;
            }

            const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
            const encoded = utf8ToBase64(JSON.stringify(collectFormData(form)));
            const body = new URLSearchParams();
            body.set('origen', origen);
            body.set('destino', destino);
            body.set('pagina', window.location.pathname);
            body.set('datos', encoded);
            body.set('g-recaptcha-response', recaptchaResponse);

            sendBtn.disabled = true;
            setStatus(gettext('Enviando...'), null);

            fetch(shareUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfInput ? csrfInput.value : '',
                },
                body: body.toString(),
            })
                .then(function (resp) {
                    return resp.json().then(function (json) {
                        return { ok: resp.ok, json: json };
                    });
                })
                .then(function (result) {
                    if (result.ok && result.json.ok) {
                        setStatus('✅ ' + gettext('Enviado correctamente.'), 'success');
                        setTimeout(closeModal, 1500);
                    } else {
                        setStatus('⚠️ ' + (result.json.error || gettext('No se pudo enviar el email.')), 'error');
                        if (window.grecaptcha) {
                            window.grecaptcha.reset();
                        }
                    }
                })
                .catch(function () {
                    setStatus('⚠️ ' + gettext('Error de red al enviar el email.'), 'error');
                })
                .finally(function () {
                    sendBtn.disabled = false;
                });
        });
    }
}

// Initialize the system once the DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    setupFormatDetection();
    setupMaterialDetection();
    setupFormValidation();
    setupPitchValidation();
    setupSpringTypeSelector();
    setupSpringEndSelector();
    setupMaterialPropertyDetection();
    if (typeof setupGeometryFieldControlAndDiameterSync === 'function') {
        setupGeometryFieldControlAndDiameterSync();
    }
    setupSaveLoadShare();
    setupCompartirModal();

    // Show loading message in the console
    console.log('🔧 HTML format detection system activated');
    console.log('🌀 Calculadora de Muelles initialized');
});
