/**
 * MODULE: Diameter Synchronization
 * 
 * Controls the automatic synchronization and locking of diameter fields
 * in the spring calculator.
 * 
 * Mathematical relationships:
 * - D.ext = D.med + D.hilo
 * - D.int = D.med - D.hilo
 * - D.ext = D.int + 2*D.hilo
 */

/**
 * Controls the availability of geometry fields and synchronizes diameter calculations.
 * Features:
 * - Locks the geometry fields until material and wire diameter are selected
 * - Shows a message when trying to access locked fields
 * - Automatically synchronizes the three diameters (mean, outer, inner)
 *   based on mathematical relationships (d_ext = d_med + d_hilo, etc)
 * - Prevents input in disabled fields
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
            blockedNotice.textContent = gettext('Geometría bloqueada: selecciona material y diámetro de hilo');
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

    // Number inputs only accept "." as the decimal separator, so values
    // written to their .value must not use formatNumber's es-ES formatting
    // (comma decimals), or the browser silently blanks the field.
    function formatForInput(value) {
        return String(Number(value.toFixed(3)));
    }

    // <input type="number"> silently rejects "," as you type it (it's not a
    // valid character for the field), so "2,5" ends up typed as "25" with
    // no error. Intercept the comma keystroke and insert "." instead.
    function allowCommaAsDecimal(input) {
        input.addEventListener('keydown', function (event) {
            if (event.key === ',' && !input.disabled) {
                event.preventDefault();
                document.execCommand('insertText', false, '.');
            }
        });
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
            // Direct listener on pointerdown (more reliable than click for disabled)
            field.addEventListener('pointerdown', function (event) {
                console.log('🔒 Pointerdown on field:', field.id, 'Disabled:', field.disabled);
                if (field.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('✋ Showing blocked message');
                    showGeometryBlockedMessage();
                }
            }, true);

            // Also mousedown as a fallback
            field.addEventListener('mousedown', function (event) {
                console.log('🔒 Mousedown on field:', field.id, 'Disabled:', field.disabled);
                if (field.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('✋ Showing blocked message (mousedown)');
                    showGeometryBlockedMessage();
                }
            }, true);

            // Keydown to prevent keyboard input
            field.addEventListener('keydown', function (event) {
                if (field.disabled) {
                    event.preventDefault();
                    showGeometryBlockedMessage();
                }
            });
        });

        // Global listener as a backup
        document.addEventListener('pointerdown', function (event) {
            const target = event.target;
            if (target.disabled && geometryFields.includes(target)) {
                console.log('Global: Disabled field detected');
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
                diametroExteriorInput.value = formatForInput(medio + wireDiameter);
                diametroInteriorInput.value = formatForInput(medio - wireDiameter);
            } else if (changedInput === diametroExteriorInput && exterior !== null) {
                diametroMedioInput.value = formatForInput(exterior - wireDiameter);
                diametroInteriorInput.value = formatForInput(exterior - 2 * wireDiameter);
            } else if (changedInput === diametroInteriorInput && interior !== null) {
                diametroMedioInput.value = formatForInput(interior + wireDiameter);
                diametroExteriorInput.value = formatForInput(interior + 2 * wireDiameter);
            }
        } finally {
            isSyncing = false;
        }
    }

    allowCommaAsDecimal(wireDiameterInput);
    if (diametroMedioInput) allowCommaAsDecimal(diametroMedioInput);
    if (diametroExteriorInput) allowCommaAsDecimal(diametroExteriorInput);
    if (diametroInteriorInput) allowCommaAsDecimal(diametroInteriorInput);

    materialSelect.addEventListener('change', updateGeometryAvailability);
    wireDiameterInput.addEventListener('input', function () {
        updateGeometryAvailability();
        // When the wire diameter changes, recalculate based on the mean diameter if it exists
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
