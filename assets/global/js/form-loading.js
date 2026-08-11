(function () {
    'use strict';

    function loadingLabel(button) {
        if (button.dataset.loadingText) {
            return button.dataset.loadingText;
        }
        if (typeof gettext === 'function') {
            return gettext('Calculando...');
        }
        return 'Calculando...';
    }

    function opensNewTab(submitter, form) {
        var formTarget = submitter.formTarget || form.getAttribute('target') || '';
        return formTarget === '_blank';
    }

    function setupForm(form) {
        var submitButtons = Array.prototype.slice.call(
            form.querySelectorAll('button[type="submit"], input[type="submit"]')
        );
        if (!submitButtons.length) {
            return;
        }

        form.addEventListener('submit', function (event) {
            if (form.dataset.submitting === 'true') {
                return;
            }

            // Another submit listener (e.g. field validation) may have already
            // cancelled this submission; don't show a spinner that would never
            // be cleared because the page isn't actually navigating away.
            if (event.defaultPrevented) {
                return;
            }

            var submitter = event.submitter || submitButtons[0];

            submitButtons.forEach(function (btn) {
                if (btn.dataset.originalText === undefined) {
                    btn.dataset.originalText = btn.textContent;
                }
                btn.disabled = true;
                btn.classList.add('is-loading');
            });
            submitter.textContent = loadingLabel(submitter);

            if (opensNewTab(submitter, form)) {
                // The current page doesn't navigate away (the response opens in a
                // new tab), so restore the buttons after a short delay instead of
                // leaving them stuck in the loading state forever.
                form.dataset.submitting = 'true';
                window.setTimeout(function () {
                    submitButtons.forEach(function (btn) {
                        btn.disabled = false;
                        btn.classList.remove('is-loading');
                        btn.textContent = btn.dataset.originalText;
                    });
                    form.dataset.submitting = 'false';
                }, 1500);
            } else {
                form.dataset.submitting = 'true';
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        Array.prototype.forEach.call(document.querySelectorAll('form'), setupForm);
    });
})();
