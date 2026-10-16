import json
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import URLError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.http import JsonResponse
from django.urls import Resolver404, resolve
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from muelles.views.calculadora_compresion import calculadora_compresion
from muelles.views.calculadora_traccion import calculadora_traccion
from muelles.views.calculadora_torsion import calculadora_torsion
from muelles.views.calculadora_conico import calculadora_conico
from muelles.views.calculadora_conico_pitch_variable import calculadora_conico_pitch_variable
from muelles.views.calculadora_2k import calculadora_2k

RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

# Only these calculator pages may be embedded in the shared link, so this
# endpoint can't be turned into a generic "email anyone a link" relay.
ALLOWED_SHARE_VIEWS = {
    calculadora_compresion,
    calculadora_traccion,
    calculadora_torsion,
    calculadora_conico,
    calculadora_conico_pitch_variable,
    calculadora_2k,
}


def _verify_recaptcha(token, remote_ip):
    if not settings.RECAPTCHA_SECRET_KEY or not token:
        return False
    data = urllib_parse.urlencode({
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': token,
        'remoteip': remote_ip or '',
    }).encode('utf-8')
    try:
        with urllib_request.urlopen(RECAPTCHA_VERIFY_URL, data=data, timeout=5) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except (URLError, ValueError, TimeoutError):
        return False
    return bool(result.get('success'))


@require_POST
@csrf_protect
def compartir_resultado_email(request):
    """Sends a link back to a spring calculator (with its inputs encoded in
    the URL, same mechanism as the shared-link auto-fill) by email, from the
    site's own account. Gated by reCAPTCHA so it can't be abused as an open
    mail relay; the target page is restricted to the six calculators.
    """
    origen = (request.POST.get('origen') or '').strip()
    destino = (request.POST.get('destino') or '').strip()
    pagina = (request.POST.get('pagina') or '').strip()
    datos = (request.POST.get('datos') or '').strip()
    recaptcha_token = request.POST.get('g-recaptcha-response', '')

    for campo, valor in ((_('remitente'), origen), (_('destinatario'), destino)):
        try:
            validate_email(valor)
        except ValidationError:
            return JsonResponse(
                {'ok': False, 'error': _('El email de %(campo)s no es válido.') % {'campo': campo}},
                status=400,
            )

    try:
        match = resolve(pagina)
    except Resolver404:
        match = None
    if match is None or match.func not in ALLOWED_SHARE_VIEWS:
        return JsonResponse({'ok': False, 'error': _('Página no válida.')}, status=400)

    if not _verify_recaptcha(recaptcha_token, request.META.get('REMOTE_ADDR')):
        return JsonResponse(
            {'ok': False, 'error': _('Verificación anti-robots fallida. Inténtalo de nuevo.')},
            status=400,
        )

    link = request.build_absolute_uri(pagina)
    if datos:
        link += '?datos=' + urllib_parse.quote(datos, safe='')

    subject = _('Cálculo de muelle compartido')
    body = _(
        '%(origen)s ha compartido contigo un cálculo de muelle.\n\n'
        'Ábrelo en este enlace:\n%(link)s'
    ) % {'origen': origen, 'link': link}

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino],
            reply_to=[origen],
        )
        email.send(fail_silently=False)
    except Exception:
        return JsonResponse(
            {'ok': False, 'error': _('No se pudo enviar el email. Inténtalo más tarde.')},
            status=502,
        )

    return JsonResponse({'ok': True})
