
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
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif has_comma:
        text = text.replace(',', '.')
    return text


def _to_float(value, default):
    try:
        return float(normalize_decimal_text(value))
    except (TypeError, ValueError):
        return default


def _to_magnitude(value):
    try:
        return float(value.magnitude)
    except AttributeError:
        return float(value)
