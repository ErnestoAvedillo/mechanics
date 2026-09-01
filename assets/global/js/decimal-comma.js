/**
 * Global decimal-comma support for <input type="number">.
 *
 * A number input silently discards a typed "," (it is not a valid
 * character for the field), so a user entering "2,3" ends up submitting
 * "23" — or, on some locales/browsers, an empty value that later blows up
 * server-side. This converts the comma (and the numpad "Decimal" key) into
 * a dot before the browser drops it, on every numeric field of every page.
 *
 * Loaded unconditionally from base.html, so it also covers pages whose
 * own scripts don't handle this (e.g. the tolerance calculators).
 */
(function () {
    'use strict';

    function onKeyDown(event) {
        var target = event.target;
        if (!target || target.tagName !== 'INPUT') {
            return;
        }
        if (target.type !== 'number' || target.disabled || target.readOnly) {
            return;
        }
        if (event.key !== ',' && event.key !== 'Decimal') {
            return;
        }
        event.preventDefault();
        if (String(target.value).indexOf('.') === -1) {
            // execCommand keeps the browser's own undo stack intact; it is
            // deprecated but still the most reliable cross-browser insert.
            var inserted = false;
            try {
                inserted = document.execCommand('insertText', false, '.');
            } catch (err) {
                inserted = false;
            }
            if (!inserted) {
                target.value = String(target.value) + '.';
                target.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    }

    document.addEventListener('keydown', onKeyDown, true);
})();
