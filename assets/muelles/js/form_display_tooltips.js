document.addEventListener('DOMContentLoaded', function () {
    const tooltipTargets = document.querySelectorAll('.input-overlay');

    if (!tooltipTargets.length) {
        return;
    }

    const tooltip = document.createElement('div');
    tooltip.className = 'form-tooltip';
    document.body.appendChild(tooltip);

    function getTooltipText(target) {
        const ownText = target.getAttribute('data-tooltip');
        if (ownText) {
            return ownText;
        }

        const labeledChild = target.querySelector('[data-tooltip]');
        if (labeledChild) {
            return labeledChild.getAttribute('data-tooltip');
        }

        const label = target.querySelector('.label');
        if (label) {
            return label.textContent.trim();
        }

        return '';
    }

    function showTooltip(target) {
        const text = getTooltipText(target);
        if (!text) {
            return;
        }

        tooltip.textContent = text;
        const rect = target.getBoundingClientRect();

        // Clamp horizontal position and flip below if there is not enough room above.
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const margin = 8;

        let left = rect.left + (rect.width / 2);
        const halfTooltip = tooltipWidth / 2;
        if (left - halfTooltip < margin) {
            left = halfTooltip + margin;
        }
        if (left + halfTooltip > viewportWidth - margin) {
            left = viewportWidth - halfTooltip - margin;
        }

        let top = rect.top - tooltipHeight - 10;
        if (top < margin) {
            top = rect.bottom + 10;
        }
        if (top + tooltipHeight > viewportHeight - margin) {
            top = viewportHeight - tooltipHeight - margin;
        }

        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
        tooltip.classList.add('is-visible');
    }

    function hideTooltip() {
        tooltip.classList.remove('is-visible');
    }

    tooltipTargets.forEach(function (target) {
        const editableFields = target.querySelectorAll('input, select, textarea');

        target.addEventListener('mouseenter', function () {
            showTooltip(target);
        });

        target.addEventListener('mouseleave', function() {
            if (target.contains(document.activeElement)) {
                return;
            }
            hideTooltip();
        });

        // focusin/focusout bubble, so this works when the inner input is being edited.
        target.addEventListener('focusin', function () {
            showTooltip(target);
        });
        target.addEventListener('focusout', function () {
            // Keep tooltip visible if focus moved to another field in same overlay.
            if (target.contains(document.activeElement)) {
                return;
            }
            hideTooltip();
        });

        editableFields.forEach(function (field) {
            field.addEventListener('input', function () {
                showTooltip(target);
            });
            field.addEventListener('click', function () {
                showTooltip(target);
            });
        });
    });

    window.addEventListener('scroll', hideTooltip, { passive: true });
});