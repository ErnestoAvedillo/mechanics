/**
 * Calculadora de Muelles - JavaScript
 * Sistema de validación, formateo y detección automática para formularios
 * Autor: Sistema de Calculadora de Muelles
 * Fecha: 2026
 * 
 * DESCRIPCIÓN GENERAL:
 * Este script proporciona un sistema completo de validación, formateo y control de campos
 * para la calculadora de muelles helicoidales. Incluye:
 * 
 * 1. Detección y formateo automático de números
 * 2. Gestión inteligente de materiales y sus propiedades
 * 3. Control dinámico de campos según el tipo de muelle
 * 4. Sincronización automática de cálculos de diámetros
 * 5. Bloqueo inteligente de campos relacionados matemáticamente
 * 6. Validación completa del formulario antes del envío
 * 
 * Las funciones están organizadas de lo más simple (formateo) a lo más complejo (sincronización).
 */

// Detección y formateo automático para inputs numéricos
/**
 * Configura la detección y formateo automático de inputs numéricos.
 * - Convierte comas por puntos como separador decimal
 * - Valida que solo contegan números válidos
 * - Cambia el color de borde según la validez del input
 * - Al perder el foco, redondea a 3 decimales
 */
function setupFormatDetection() {
    // Detectar todos los inputs numéricos
    const numericInputs = document.querySelectorAll('input[type="number"]');

    numericInputs.forEach(input => {
        // Auto-formateo mientras se escribe
        input.addEventListener('input', function (e) {
            let value = e.target.value;

            // Detectar separador decimal (punto o coma)
            if (value.includes(',')) {
                // Convertir coma a punto para compatibilidad
                value = value.replace(',', '.');
                e.target.value = value;
            }

            // Validar formato numérico
            const isValidNumber = /^-?\d*\.?\d*$/.test(value);

            // Aplicar estilos según validación
            if (value && !isValidNumber) {
                e.target.style.borderColor = '#dc3545';
                e.target.style.backgroundColor = '#fff5f5';
            } else {
                e.target.style.borderColor = '#28a745';
                e.target.style.backgroundColor = '#f8fff8';
            }
        });

        // Formatear al perder el foco
        input.addEventListener('blur', function (e) {
            let value = parseFloat(e.target.value);
            if (!isNaN(value)) {
                // Formatear a 3 decimales si es necesario
                if (value % 1 !== 0) {
                    e.target.value = value.toFixed(3).replace(/\.?0+$/, '');
                }
            }
            // Resetear estilos
            e.target.style.borderColor = '#ced4da';
            e.target.style.backgroundColor = 'white';
        });
    });
}

// Detectar formato de material y auto-completar propiedades
/**
 * Detecta cuando se selecciona un material y auto-completa automáticamente sus propiedades:
 * - Llena el campo de módulo de corte si está vacío
 * - Muestra información de propiedades mecánicas del material
 * - Destaca visualmente el campo auto-completado
 */
function setupMaterialDetection() {
    const materialSelect = document.getElementById('material');
    const moduloInput = document.querySelector('input[name="modulo_corte"]');

    if (materialSelect && moduloInput) {
        materialSelect.addEventListener('change', function () {
            const selected = this.options[this.selectedIndex];
            const shearModulus = selected.getAttribute('data-shear-modulus');
            const elasticFactor = selected.getAttribute('data-elastic-factor');

            // Auto-completar módulo de corte si está disponible
            if (shearModulus && !moduloInput.value) {
                moduloInput.value = shearModulus;
                moduloInput.style.backgroundColor = '#e7f3ff';
                setTimeout(() => {
                    moduloInput.style.backgroundColor = 'white';
                }, 2000);
            }

            // Mostrar información del material
            showMaterialInfo(selected, shearModulus, elasticFactor);
        });
    }
}

// Mostrar información del material seleccionado
/**
 * Muestra un panel informativo con las propiedades técnicas del material seleccionado.
 * Incluye:
 * - Módulo de corte (en N/mm²)
 * - Factor límite elástico
 * - Se oculta si el material no tiene propiedades disponibles
 * @param {HTMLOptionElement} selectedOption - La opción seleccionada del select
 * @param {string} shearModulus - Módulo de corte del material
 * @param {string} elasticFactor - Factor elástico del material
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
            <strong>📊 Propiedades del Material:</strong><br>
            <span style="color: #0056b3;">• Módulo de corte: <strong>${formatNumber(shearModulus)} N/mm²</strong></span><br>
            <span style="color: #0056b3;">• Factor límite elástico: <strong>${formatNumber(elasticFactor)}</strong></span>
        `;
        materialInfo.style.display = 'block';
    } else {
        materialInfo.style.display = 'none';
    }
}

// Formatear números para mostrar
/**
 * Formatea números para presentación visual usando la configuración regional española.
 * - Si es entero: muestra sin decimales (ej: 123)
 * - Si es decimal: muestra hasta 3 decimales (ej: 123,456)
 * - Usa separador de miles (punto) y coma como separador decimal
 * @param {number|string} num - Número a formatear
 * @returns {string} Número formateado para mostrar
 */
function formatNumber(num) {
    const number = parseFloat(num);
    if (isNaN(number)) return num;

    // Detectar si es entero o decimal
    if (number % 1 === 0) {
        return number.toLocaleString('es-ES');
    } else {
        return number.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 3 });
    }
}

// Validación de formulario antes del envío
/**
 * Valida que todos los campos requeridos estén completos antes de enviar el formulario.
 * - Evita el envío si hay campos vacíos
 * - Marca visualmente los campos inválidos con color rojo
 * - Muestra una alerta indicando que complete los campos obligatorios
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
            alert('⚠️ Por favor complete todos los campos obligatorios');
        }
    });
}

/**
 * Configura el selector de tipo de muelle (compresion/tracción).
 * - Cambia dinámicamente los campos y etiquetas según el tipo seleccionado
 * - Muestra/oculta campos específicos de tracción (tensión inicial)
 * - Actualiza las etiquetas de "longitud inicial/final" según el tipo
 * - Gestiona las opciones visuales de extremos según el tipo
 * - Selecciona automáticamente un extremo válido por defecto
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
            initialLabel.textContent = isTraccion ? 'Longitud inicial estirada (mm):' : 'Longitud inicial (mm):';
        }

        if (finalLabel) {
            finalLabel.textContent = isTraccion ? 'Longitud final estirada (mm):' : 'Longitud final (mm):';
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
                'static/img/anillo_simple_aleman_entero_lateral.png',
                'static/img/anillo_simple_aleman_entero_centrado.png',
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

// Configurar selector visual de extremos de muelle
/**
 * Configura un selector visual para elegir el tipo de extremos del muelle.
 * - Permite seleccionar visualmente entre diferentes opciones de extremos
 * - Guarda el valor seleccionado en un input oculto
 * - Incluye animaciones visuales al seleccionar y pasar el ratón
 * - Solo una opción puede estar seleccionada a la vez
 */
function setupSpringEndSelector() {
    const endOptions = document.querySelectorAll('.end-option');
    const hiddenInput = document.querySelector('input[name="tipo_final"]');

    endOptions.forEach(option => {
        option.addEventListener('click', function () {
            // Remover selección anterior
            endOptions.forEach(opt => opt.classList.remove('selected'));

            // Seleccionar nueva opción
            this.classList.add('selected');

            // Actualizar valor en input oculto
            const value = this.getAttribute('data-value');
            hiddenInput.value = value;

            // Animación de confirmación
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'translateY(-2px)';
            }, 150);

            // Log para depuración
            console.log('🌀 Tipo de extremo seleccionado:', value);
        });

        // Efecto hover mejorado
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

// Configurar auto-detección de propiedades del material (compatibilidad)
/**
 * Detecta las propiedades del material seleccionado y las muestra en pantalla.
 * Es complementario a setupMaterialDetection() para asegurar compatibilidad.
 * - Se activa al cambiar el material seleccionado
 * - Muestra información técnica del material (módulo de corte, factor elástico)
 */
function setupMaterialPropertyDetection() {
    const materialSelect = document.getElementById('material');
    if (materialSelect) {
        materialSelect.addEventListener('change', function () {
            const selected = this.options[this.selectedIndex];
            const shearModulus = selected.getAttribute('data-shear-modulus');
            const elasticFactor = selected.getAttribute('data-elastic-factor');

            // Integración con el sistema de detección de formato
            showMaterialInfo(selected, shearModulus, elasticFactor);
        });
    }
}



// Inicialización del sistema cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function () {
    setupFormatDetection();
    setupMaterialDetection();
    setupFormValidation();
    setupSpringTypeSelector();
    setupSpringEndSelector();
    setupMaterialPropertyDetection();
    setupGeometryFieldControlAndDiameterSync();

    // Mostrar mensaje de carga en consola
    console.log('🔧 Sistema de detección de formato HTML activado');
    console.log('🌀 Calculadora de Muelles initialized');
});
