/**
 * MÓDULO: Sincronización de Diámetros
 * 
 * Controla la sincronización automática y el bloqueo de campos de diámetros
 * en la calculadora de muelles.
 * 
 * Relaciones matemáticas:
 * - D.ext = D.med + D.hilo
 * - D.int = D.med - D.hilo
 * - D.ext = D.int + 2*D.hilo
 */

/**
 * Controla la disponibilidad de campos de geometría y sincroniza cálculos de diámetros.
 * Funcionalidades:
 * - Bloquea los campos de geometría hasta que se seleccione material y diámetro de hilo
 * - Muestra un mensaje cuando se intenta acceder a campos bloqueados
 * - Sincroniza automáticamente los tres diámetros (medio, exterior, interior)
 *   basándose en relaciones matemáticas (d_ext = d_med + d_hilo, etc)
 * - Previene entrada en campos deshabilitados
 */
function setupGeometryFieldControlAndDiameterSync() {
    const materialSelect = document.getElementById('material');
    const wireDiameterInput = document.getElementById('diametro_hilo');
    const diametroMedioInput = document.getElementById('diametro_medio');
    const diametroExteriorInput = document.getElementById('diametro_exterior');
    const diametroInteriorInput = document.getElementById('diametro_interior');

    if (!materialSelect || !wireDiameterInput) {
        return;
    }

    const form = materialSelect.closest('form');
    if (!form) {
        return;
    }

    const geometryFields = Array.from(
        form.querySelectorAll('input[type="number"], select')
    ).filter(field => {
        const fieldId = field.id || '';
        const fieldName = field.name || '';
        if (!fieldId && !fieldName) {
            return false;
        }
        if (field === materialSelect || field === wireDiameterInput) {
            return false;
        }
        if (fieldId === 'numero_ciclos' || fieldId === 'shot_peening') {
            return false;
        }
        if (fieldName === 'csrfmiddlewaretoken') {
            return false;
        }
        return true;
    });

    let blockedNotice = null;
    let blockedNoticeTimer = null;

    function showGeometryBlockedMessage() {
        if (!blockedNotice) {
            blockedNotice = document.createElement('div');
            blockedNotice.textContent = 'Geometría bloqueada: selecciona material y diámetro de hilo';
            blockedNotice.style.cssText = [
                'position: fixed',
                'left: 50%',
                'top: 50%',
                'transform: translate(-50%, -50%)',
                'z-index: 9999',
                'padding: 16px 20px',
                'border-radius: 8px',
                'background: #1f2937',
                'color: #fff',
                'font-size: 14px',
                'box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3)',
                'opacity: 0',
                'transition: opacity 0.2s ease'
            ].join(';');
            document.body.appendChild(blockedNotice);
        }

        if (blockedNoticeTimer) {
            clearTimeout(blockedNoticeTimer);
        }

        blockedNotice.style.opacity = '1';
        blockedNoticeTimer = setTimeout(() => {
            blockedNotice.style.opacity = '0';
        }, 1800);
    }

    function toNumber(value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        const parsed = Number(String(value).replace(',', '.'));
        return Number.isFinite(parsed) ? parsed : null;
    }

    function isGeometryEnabled() {
        const hasMaterial = Boolean(materialSelect.value);
        const wireDiameter = toNumber(wireDiameterInput.value);
        return hasMaterial && wireDiameter !== null && wireDiameter > 0;
    }

    function updateGeometryAvailability() {
        const enabled = isGeometryEnabled();
        geometryFields.forEach(field => {
            field.disabled = !enabled;
        });
    }

    function setupBlockedGeometryHandlers() {
        // Wrap each disabled field with visual layer that captures clicks
        geometryFields.forEach(field => {
            // Listener directo en pointerdown (más confiable que click para disabled)
            field.addEventListener('pointerdown', function (event) {
                console.log('🔒 Pointerdown en campo:', field.id, 'Disabled:', field.disabled);
                if (field.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('✋ Mostrando mensaje de bloqueado');
                    showGeometryBlockedMessage();
                }
            }, true);

            // También mousedown como fallback
            field.addEventListener('mousedown', function (event) {
                console.log('🔒 Mousedown en campo:', field.id, 'Disabled:', field.disabled);
                if (field.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('✋ Mostrando mensaje de bloqueado (mousedown)');
                    showGeometryBlockedMessage();
                }
            }, true);

            // Keydown para prevenir entrada por teclado
            field.addEventListener('keydown', function (event) {
                if (field.disabled) {
                    event.preventDefault();
                    showGeometryBlockedMessage();
                }
            });
        });

        // Listener global como respaldo
        document.addEventListener('pointerdown', function (event) {
            const target = event.target;
            if (target.disabled && geometryFields.includes(target)) {
                console.log('Global: Campo deshabilitado detectado');
                event.preventDefault();
                event.stopPropagation();
                showGeometryBlockedMessage();
            }
        }, true);
    }

    let isSyncing = false;

    function syncDiameterFields(changedInput) {
        if (isSyncing) {
            return;
        }
        if (!diametroMedioInput || !diametroExteriorInput || !diametroInteriorInput) {
            return;
        }

        const wireDiameter = toNumber(wireDiameterInput.value);
        if (wireDiameter === null || wireDiameter <= 0) {
            return;
        }

        const medio = toNumber(diametroMedioInput.value);
        const exterior = toNumber(diametroExteriorInput.value);
        const interior = toNumber(diametroInteriorInput.value);

        isSyncing = true;
        try {
            if (changedInput === diametroMedioInput && medio !== null) {
                diametroExteriorInput.value = formatNumber(medio + wireDiameter);
                diametroInteriorInput.value = formatNumber(medio - wireDiameter);
            } else if (changedInput === diametroExteriorInput && exterior !== null) {
                diametroMedioInput.value = formatNumber(exterior - wireDiameter);
                diametroInteriorInput.value = formatNumber(exterior - 2 * wireDiameter);
            } else if (changedInput === diametroInteriorInput && interior !== null) {
                diametroMedioInput.value = formatNumber(interior + wireDiameter);
                diametroExteriorInput.value = formatNumber(interior + 2 * wireDiameter);
            }
        } finally {
            isSyncing = false;
        }
    }

    materialSelect.addEventListener('change', updateGeometryAvailability);
    wireDiameterInput.addEventListener('input', function () {
        updateGeometryAvailability();
        // Cuando cambia el diámetro de hilo, recalcular basándose en diámetro medio si existe
        if (diametroMedioInput && diametroMedioInput.value) {
            syncDiameterFields(diametroMedioInput);
        } else if (diametroExteriorInput && diametroExteriorInput.value) {
            syncDiameterFields(diametroExteriorInput);
        } else if (diametroInteriorInput && diametroInteriorInput.value) {
            syncDiameterFields(diametroInteriorInput);
        }
    });

    if (diametroMedioInput) {
        diametroMedioInput.addEventListener('input', function () {
            syncDiameterFields(diametroMedioInput);
        });
    }
    if (diametroExteriorInput) {
        diametroExteriorInput.addEventListener('input', function () {
            syncDiameterFields(diametroExteriorInput);
        });
    }
    if (diametroInteriorInput) {
        diametroInteriorInput.addEventListener('input', function () {
            syncDiameterFields(diametroInteriorInput);
        });
    }

    setupBlockedGeometryHandlers();
    updateGeometryAvailability();
}
