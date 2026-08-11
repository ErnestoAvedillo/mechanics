document.addEventListener('DOMContentLoaded', function () {
    const shotPeeningToggle = document.getElementById('shot_peening');

    if (!shotPeeningToggle) {
        return;
    }

    // The label contains a <span class="toggle-switch"> child, so we update
    // only the text node that follows it, not the whole textContent.
    const toggleLabel = document.querySelector('label[for="shot_peening"]');

    function updateToggleText() {
        if (!toggleLabel) {
            return;
        }
        // Find or create the text node after the span.
        const span = toggleLabel.querySelector('.toggle-switch');
        let textNode = span ? span.nextSibling : null;
        const newText = shotPeeningToggle.checked ? ' ' + gettext('Activado') : ' ' + gettext('Desactivado');

        if (textNode && textNode.nodeType === Node.TEXT_NODE) {
            textNode.textContent = newText;
        } else if (span) {
            span.insertAdjacentText('afterend', newText);
        }
    }

    shotPeeningToggle.addEventListener('change', updateToggleText);

    // Sync text with current checkbox state on page load.
    updateToggleText();
});