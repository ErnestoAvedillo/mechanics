/**
 * Validation and automatic calculation for the spring form
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('form_validation_compression.js loaded');
    
    const form = document.querySelector('form');
    const materialInput = document.getElementById('material');
    const diametroHiloInput = document.getElementById('diametro_hilo');
    const numeroEspirasInput = document.getElementById('numero_espiras');
    const longitud_solidaInput = document.getElementById('longitud_solida');
    const pitchInput = document.getElementById('pitch');
    const longitud_libreInput = document.getElementById('longitud_libre');
    const longitud_inicialInput = document.getElementById('longitud_inicial');
    const longitud_finalInput = document.getElementById('longitud_final');
    
    if (!form || !materialInput) {
        console.error('Could not find the form or the required inputs');
        return;
    }
    
    // Function to get the CSRF token
    function getCsrfToken() {
        // Try to get it from the hidden input
        let token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (token) return token;
        
        // Get it from the cookie as a fallback
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Debounce variables
    let timeoutLongitudSolida = null;
    let timeoutPitch = null;
    let timeoutLongitudesTrabajo = null;
    const DEBOUNCE_DELAY = 500; // wait 500ms without typing before calculating
    
    /**
     * Calculates and fills in the solid length
     */
    async function calcularLongitudSolida() {
        const material = materialInput.value.trim();
        const diametroHilo = diametroHiloInput?.value?.trim();
        const numeroEspiras = numeroEspirasInput?.value?.trim();
        
        // Only calculate if all the data is present
        if (!material || !diametroHilo || !numeroEspiras) {
            if (longitud_solidaInput) {
                longitud_solidaInput.value = '';
            }
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('material', material);
            formData.append('diametro_hilo', parseFloat(diametroHilo));
            formData.append('numero_espiras', parseFloat(numeroEspiras));
            
            const csrfToken = getCsrfToken();
            
            console.log('Calling API with:', { material, diametroHilo, numeroEspiras });
            
            const response = await fetch('/muelles/api/calculate-blocking-length/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken || ''
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Solid length obtained:', data.longitud_bloqueo);
                
                if (longitud_solidaInput && data.longitud_bloqueo) {
                    longitud_solidaInput.value = data.longitud_bloqueo.toFixed(2);
                }
            } else {
                const error = await response.json();
                console.error('Server error:', error.error);
            }
        } catch (error) {
            console.error('Error getting solid length:', error);
        }
    }

    /** Calculates and fills in the spring pitch
     * Adds validation to ensure the pitch is not less than or equal to the wire diameter, showing an error modal if this occurs
     */
    async function calculo_pitch() {
        const material = materialInput.value.trim();
        const diametroHilo = diametroHiloInput?.value?.trim();
        const numeroEspiras = numeroEspirasInput?.value?.trim();
        const longitud_libre = longitud_libreInput?.value?.trim();
        
        // Only calculate if all the data is present
        if (!material || !diametroHilo || !numeroEspiras || !longitud_libre) {
            if (pitchInput) {
                // longitud_inicialInput.disabled = true;
                // longitud_inicialInput.style.opacity = '0.5';
                // longitud_inicialInput.style.cursor = 'not-allowed';
                // longitud_finalInput.disabled = true;
                // longitud_finalInput.style.opacity = '0.5';
                // longitud_finalInput.style.cursor = 'not-allowed';
                pitchInput.value = '';
            }
            return;
        }
        try { 
            const formData = new FormData();
            formData.append('material', material);
            formData.append('diametro_hilo', parseFloat(diametroHilo));
            formData.append('numero_espiras', parseFloat(numeroEspiras));
            formData.append('longitud_libre', parseFloat(longitud_libre));
            
            const csrfToken = getCsrfToken();
            
            console.log('Calling pitch API with:', { material, diametroHilo, numeroEspiras, longitud_libre });
            
            const response = await fetch('/muelles/api/calculate-pitch/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken || ''
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Pitch obtained:', data.pitch);
                
                if (pitchInput && data.pitch) {
                    if (data.pitch <= diametroHilo) {
                        mostrarModal(gettext('Pitch no válido'), gettext('El pitch calculado es menor o igual al diámetro del hilo, lo que no es físicamente posible. Por favor, revisa los datos ingresados.'));
                        pitchInput.value = '';
                        return;
                    }
                        pitchInput.value = data.pitch.toFixed(2);
                        longitud_inicialInput.disabled = false;
                        longitud_inicialInput.style.opacity = '1';
                        longitud_inicialInput.style.cursor = 'auto';
                        longitud_finalInput.disabled = false;
                        longitud_finalInput.style.opacity = '1';
                        longitud_finalInput.style.cursor = 'auto';
                }
            } else {
                const error = await response.json();
                console.error('Server error calculating pitch:', error.error);
            }
        } catch (error) {
            console.error('Error getting pitch:', error);
        }
        
    }

    /**
     * Validates that the working lengths are not greater than the free length or less than the solid length, showing an error modal if this occurs
     * Adds validation to ensure the working length is not less than or equal to the solid length, showing an error modal if this occurs
     */
    async function validar_longitudes_trabajo() {
        const longitud_libre = parseFloat(longitud_libreInput?.value?.trim());
        const longitud_solida = parseFloat(longitud_solidaInput?.value?.trim());
        const longitud_inicial = parseFloat(document.getElementById('longitud_inicial')?.value?.trim());
        const longitud_final = parseFloat(document.getElementById('longitud_final')?.value?.trim());
        
        if (!longitud_libre || !longitud_solida) {
            return;
        }
        try {
            if (longitud_inicial) {
                if (longitud_inicial >= longitud_libre) {
                    mostrarModal(gettext('Longitud inicial no válida'), gettext('La longitud inicial no puede ser mayor o igual a la longitud libre. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_inicial').value = '';
                    return;
                }
                if (longitud_inicial <= longitud_solida) {
                    mostrarModal(gettext('Longitud inicial no válida'), gettext('La longitud inicial no puede ser menor o igual a la longitud sólida. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_inicial').value = '';
                    return;
                }
                if (longitud_inicial <= longitud_final) {
                    mostrarModal(gettext('Longitud inicial no válida'), gettext('La longitud inicial no puede ser mayor o igual a la longitud final. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_inicial').value = '';
                    return;
                }
            }
            if (longitud_final) {
                if (longitud_final >= longitud_libre) {
                    mostrarModal(gettext('Longitud final no válida'), gettext('La longitud final no puede ser mayor o igual a la longitud libre. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_final').value = '';
                    return;
                }
                if (longitud_final <= longitud_solida) {
                    mostrarModal(gettext('Longitud final no válida'), gettext('La longitud final no puede ser menor o igual a la longitud sólida. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_final').value = '';
                    return;
                }
                if (longitud_final >= longitud_inicial) {
                    mostrarModal(gettext('Longitud final no válida'), gettext('La longitud final no puede ser menor o igual a la longitud inicial. Por favor, revisa los datos ingresados.'));
                    document.getElementById('longitud_final').value = '';
                    return;
                }
            }
        } catch (error) {
            console.error('Error validating working lengths:', error);
        }

    }

    /**
     * Submit event - validate material
     */
    form.addEventListener('submit', function(e) {
        console.log('Submit event captured');
        
        const materialSeleccionado = materialInput.value.trim();
        
        if (!materialSeleccionado) {
            e.preventDefault();
            console.log('Material not selected - showing modal');
            mostrarModal(gettext('Material no seleccionado'), gettext('Debes seleccionar un material antes de calcular.'));
            return false;
        }
        
        console.log('Material: ' + materialSeleccionado + ' - allowing submit');
    });
    
    /**
     * Listeners for changes that trigger the solid length calculation
     */
    const inputsTrigger = [materialInput, diametroHiloInput, numeroEspirasInput];
    
    inputsTrigger.forEach(input => {
        if (input) {
            input.addEventListener('change', () => {
                clearTimeout(timeoutLongitudSolida);
                calcularLongitudSolida();
            });
            input.addEventListener('input', () => {
                clearTimeout(timeoutLongitudSolida);
                timeoutLongitudSolida = setTimeout(calcularLongitudSolida, DEBOUNCE_DELAY);
            });
        }
    });

    const inputsTriggerPitch = [materialInput, diametroHiloInput, numeroEspirasInput, longitud_libreInput];
    
    inputsTriggerPitch.forEach(input => {
        if (input) {
            input.addEventListener('change', () => {
                clearTimeout(timeoutPitch);
                calculo_pitch();
            });
            input.addEventListener('input', () => {
                clearTimeout(timeoutPitch);
                timeoutPitch = setTimeout(calculo_pitch, DEBOUNCE_DELAY);
            });
        }
    });

    const inputsTriggerLongitudesTrabajo = [longitud_libreInput, longitud_solidaInput, document.getElementById('longitud_inicial'), document.getElementById('longitud_final')];
    
    inputsTriggerLongitudesTrabajo.forEach(input => {
        if (input) {
            input.addEventListener('change', () => {
                clearTimeout(timeoutLongitudesTrabajo);
                validar_longitudes_trabajo();
            });
            input.addEventListener('input', () => {
                clearTimeout(timeoutLongitudesTrabajo);
                timeoutLongitudesTrabajo = setTimeout(validar_longitudes_trabajo, DEBOUNCE_DELAY);
            });
        }
    });
});

/**
 * Shows a popup modal with a message
 */
function mostrarModal(titulo, mensaje) {
    // Remove the previous modal if it exists
    const modalAnterior = document.getElementById('validation-modal');
    if (modalAnterior) {
        modalAnterior.remove();
    }
    
    // Create a dark overlay
    const overlay = document.createElement('div');
    overlay.id = 'validation-modal';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    // Create the modal box
    const caja = document.createElement('div');
    caja.style.cssText = `
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        padding: 30px;
        max-width: 400px;
        text-align: center;
        font-family: Arial, sans-serif;
    `;
    
    // Title
    const tituloEl = document.createElement('h2');
    tituloEl.textContent = titulo;
    tituloEl.style.cssText = `
        margin: 0 0 15px 0;
        color: #d32f2f;
        font-size: 18px;
    `;
    
    // Message
    const mensajeEl = document.createElement('p');
    mensajeEl.textContent = mensaje;
    mensajeEl.style.cssText = `
        margin: 0 0 20px 0;
        color: #555;
        font-size: 14px;
        line-height: 1.5;
    `;
    
    // Button
    const boton = document.createElement('button');
    boton.textContent = gettext('Entendido');
    boton.style.cssText = `
        background-color: #d32f2f;
        color: white;
        border: none;
        padding: 10px 30px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: bold;
    `;
    
    boton.onmouseover = function() {
        this.style.backgroundColor = '#b71c1c';
    };
    
    boton.onmouseout = function() {
        this.style.backgroundColor = '#d32f2f';
    };
    
    boton.onclick = function() {
        overlay.remove();
    };
    
    // Close when clicking outside the modal
    overlay.onclick = function(e) {
        if (e.target === overlay) {
            overlay.remove();
        }
    };
    
    // Assemble the modal
    caja.appendChild(tituloEl);
    caja.appendChild(mensajeEl);
    caja.appendChild(boton);
    overlay.appendChild(caja);
    document.body.appendChild(overlay);
    
    console.log('Modal shown:', titulo);
}
