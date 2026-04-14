
def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_magnitude(value):
    try:
        return float(value.magnitude)
    except AttributeError:
        return float(value)
