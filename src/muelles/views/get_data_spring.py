import traceback as _traceback

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy


# Human-readable labels so a parsing error names the field instead of
# dumping a raw Python traceback to the end user.
FIELD_LABELS = {
    'diametro_hilo': _lazy('Diámetro de hilo'),
    'diametro_exterior': _lazy('Diámetro exterior'),
    'diametro_medio': _lazy('Diámetro medio'),
    'diametro_interior': _lazy('Diámetro interior'),
    'diametro_medio_superior': _lazy('Diámetro medio superior'),
    'diametro_medio_inferior': _lazy('Diámetro medio inferior'),
    'longitud_libre': _lazy('Longitud libre'),
    'numero_espiras': _lazy('Número de espiras'),
    'numero_ciclos': _lazy('Número de ciclos'),
    'longitud_inicial': _lazy('Longitud inicial'),
    'longitud_final': _lazy('Longitud final'),
    'pitch': _lazy('Pitch'),
    'angulo_libre': _lazy('Ángulo libre'),
    'longitud_sujecion': _lazy('Longitud de sujeción'),
    'Radio_sujecion': _lazy('Radio de sujeción'),
    'angulo_inicial': _lazy('Ángulo inicial'),
    'angulo_final': _lazy('Ángulo final'),
    'pitch_superior': _lazy('Pitch superior'),
    'pitch_inferior': _lazy('Pitch inferior'),
    'tension_inicial': _lazy('Tensión inicial'),
    'length_1': _lazy('Longitud tramo 1'),
    'pitch_1': _lazy('Pitch tramo 1'),
    'length_2': _lazy('Longitud tramo 2'),
    'pitch_2': _lazy('Pitch tramo 2'),
    'length_3': _lazy('Longitud tramo 3'),
    'pitch_3': _lazy('Pitch tramo 3'),
}


def _field_label(field):
    if field is None:
        return _('valor')
    return FIELD_LABELS.get(field, field)


def normalize_decimal_text(value):
    """Return a string whose decimal separator is a dot.

    Tolerates the es-ES comma decimal ("2,3"), apostrophe/space/NBSP
    thousands separators, and the mixed "1.234,5" / "1,234.5" grouping
    styles. Non-string values are returned unchanged.
    """
    if not isinstance(value, str):
        return value
    text = value.strip().replace(' ', '').replace("'", '').replace(' ', '')
    if not text:
        return text
    has_comma = ',' in text
    has_dot = '.' in text
    if has_comma and has_dot:
        # The right-most separator is the decimal one; the other groups digits.
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif has_comma:
        text = text.replace(',', '.')
    return text


def parse_decimal(value, default=None, field=None):
    """Parse a form value into a float, tolerating comma decimals.

    Raises ``ValueError`` with a translated, field-named message when the
    value is present but not a valid number, so the calculator views can
    show it instead of a 500 traceback.
    """
    if value is None:
        return default
    text = normalize_decimal_text(value)
    if text is None or text == '':
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        raise ValueError(
            _('El campo «%(campo)s» debe ser un número válido (recibido: «%(valor)s»).')
            % {'campo': _field_label(field), 'valor': value}
        ) from None


def parse_int(value, default=None, field=None):
    """Parse a form value into an int, tolerating comma decimals.

    Accepts "3", "3.0" or "3,0"; rejects genuine fractional values such
    as "2.3" with a translated, field-named message. Used for fields the
    calculation library requires to be integer (e.g. the number of coils
    of a torsion spring).
    """
    number = parse_decimal(value, default=None, field=field)
    if number is None:
        return default
    if float(number).is_integer():
        return int(number)
    raise ValueError(
        _('El campo «%(campo)s» debe ser un número entero, sin decimales '
          '(recibido: «%(valor)s»).')
        % {'campo': _field_label(field), 'valor': value}
    )


def build_error_result(exc, log_prefix='Error en los cálculos'):
    """Build the ``resultado`` dict shown when a calculation fails.

    The full traceback is always written to the server log, but it is only
    handed to the template when ``DEBUG`` is on, so an end user never sees a
    Python traceback on screen — only the translated one-line message.
    """
    tb = _traceback.format_exc()
    print(f"{log_prefix}: {exc}\n{tb}")
    return {
        'error': _('Error en los cálculos: %(error)s') % {'error': str(exc)},
        'traceback': tb if settings.DEBUG else None,
    }


def _as_mm(value):
    """Return ``value`` in millimetres as a float, unwrapping a pint Quantity."""
    if value is None:
        return None
    if hasattr(value, 'magnitude'):
        return float(value.magnitude)
    return float(value)


def check_pitch_not_below_wire(pitch, wire_diameter, field='pitch'):
    """Reject a coil pitch smaller than the wire diameter.

    A pitch below the wire diameter means the coils physically overlap, so
    the spring cannot be wound. Raises a translated ``ValueError`` naming
    the field; returns silently when either value is missing or not
    positive (those cases are reported by other checks).
    """
    try:
        pitch_mm = _as_mm(pitch)
        wire_mm = _as_mm(wire_diameter)
    except (TypeError, ValueError):
        return
    if not pitch_mm or not wire_mm or pitch_mm <= 0 or wire_mm <= 0:
        return
    # 1 micron tolerance so an exact pitch == wire_diameter is accepted.
    if pitch_mm < wire_mm - 1e-3:
        raise ValueError(
            _('El paso «%(campo)s» (%(paso).4g mm) no puede ser menor que el '
              'diámetro de hilo (%(hilo).4g mm): las espiras se solaparían.')
            % {'campo': _field_label(field), 'paso': pitch_mm, 'hilo': wire_mm}
        )


def format_quantity(value, ndigits=2):
    """Format a pint Quantity (or plain number) as ``'<value> <unit>'``.

    Units are shortened for display: ``deg`` -> ``°``, ``mm·N`` -> ``N·mm``,
    ``MPa`` -> ``N/mm²``. Returns ``None`` for a missing value.
    """
    if value is None:
        return None
    if hasattr(value, 'magnitude'):
        magnitude = value.magnitude
        try:
            unit = f"{value.units:~P}"
        except Exception:
            unit = ''
    else:
        magnitude, unit = value, ''
    try:
        magnitude = round(float(magnitude), ndigits)
    except (TypeError, ValueError):
        return value
    unit = unit.replace('mm·N', 'N·mm').replace('MPa', 'N/mm²').replace('deg', '°')
    if not unit:
        return magnitude
    return f"{magnitude}{unit}" if unit == '°' else f"{magnitude} {unit}"


def build_working_points(muelle):
    """Return a small table (one row per working point) with the load and
    stress the spring sees at each of the two work positions.

    Reads ``muelle.get_data_positions()`` — a list of pydantic
    Linear/AngularLoadPosition rows whose fields are pint Quantities — and
    formats every value with its unit for the shared results template.
    Returns ``[]`` when no positions are available.
    """
    try:
        positions = list(muelle.get_data_positions() or [])
    except Exception:
        positions = []
    rows = []
    for index, point in enumerate(positions, start=1):
        rows.append({
            'indice': index,
            'posicion': format_quantity(getattr(point, 'position', None)),
            'recorrido': format_quantity(getattr(point, 'travel', None)),
            'carga': format_quantity(getattr(point, 'load', None)),
            'tension': format_quantity(getattr(point, 'stress', None)),
            'diametro_exterior': format_quantity(getattr(point, 'outer_diameter', None)),
            'diametro_interior': format_quantity(getattr(point, 'inner_diameter', None)),
        })
    return rows


def get_data_spring(request):
    def dec(field_name, default=None):
        return parse_decimal(request.POST.get(field_name), default, field_name)

    datos_muelle = {
        'material': request.POST.get('material'),
        'diametro_hilo': dec('diametro_hilo'),
        'shot_peening': request.POST.get('shot_peening') == 'si',
        'diametro_exterior': dec('diametro_exterior'),
        'diametro_medio': dec('diametro_medio'),
        'diametro_interior': dec('diametro_interior'),
        'diametro_medio_superior': dec('diametro_medio_superior'),
        'diametro_medio_inferior': dec('diametro_medio_inferior'),
        'longitud_libre': dec('longitud_libre', 0.0),
        'numero_espiras': dec('numero_espiras', 0.0),
        'numero_ciclos': dec('numero_ciclos', 1e6),
        'longitud_inicial': dec('longitud_inicial'),
        'longitud_final': dec('longitud_final'),
        'pitch': dec('pitch'),
        'angulo_libre': dec('angulo_libre'),
        'longitud_sujecion': dec('longitud_sujecion'),
        'Radio_sujecion': dec('Radio_sujecion'),
        'angulo_inicial': dec('angulo_inicial'),
        'angulo_final': dec('angulo_final'),
        'pitch_superior': dec('pitch_superior'),
        'pitch_inferior': dec('pitch_inferior'),
        'length_1': dec('length_1'),
        'pitch_1': dec('pitch_1'),
        'length_2': dec('length_2'),
        'pitch_2': dec('pitch_2'),
        'length_3': dec('length_3'),
        'pitch_3': dec('pitch_3'),
    }
    return datos_muelle
