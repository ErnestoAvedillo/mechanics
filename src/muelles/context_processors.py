from django.conf import settings


def recaptcha(request):
    """Exposes the reCAPTCHA site key to every template without each view
    having to pass it explicitly."""
    return {'RECAPTCHA_SITE_KEY': settings.RECAPTCHA_SITE_KEY}
