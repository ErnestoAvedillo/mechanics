from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import (
    get_data_spring,
    parse_int,
    check_pitch_not_below_wire,
    build_error_result,
    build_working_points,
)
from muelles.views.spring_animation import animation_http_response, build_twist_animation_gif
from muelles.views.spring_report_pdf import build_spring_report_pdf_response
from springcalc import Material, TorsionSpring


def _calcular_muelle_torsion(request):
    """Runs the torsion calculator computation from the POST data.

    Returns (spring, result, start_angle, end_angle) on success. Exceptions
    are propagated so each view can decide how to display the error.
    """
    datos_entrada_muelle = get_data_spring(request)

    required_torsion_fields = {
        'diametro_medio': _('Diámetro medio'),
        'numero_espiras': _('Número de espiras'),
        'pitch': _('Pitch'),
        'angulo_libre': _('Ángulo libre'),
        'longitud_sujecion': _('Longitud de sujeción'),
        'Radio_sujecion': _('Radio de sujeción'),
    }
    missing_fields = [
        label for key, label in required_torsion_fields.items()
        if datos_entrada_muelle.get(key) is None
    ]
    if missing_fields:
        raise ValueError(
            _("Faltan campos obligatorios para torsión: %(fields)s") % {
                'fields': ', '.join(missing_fields)
            }
        )

    material_obj = Material(material_name=datos_entrada_muelle['material'])
    muelle = TorsionSpring(
        material=material_obj,
        wire_diameter=datos_entrada_muelle.get('diametro_hilo') or 0.0,
    )
    # The calculation library models a torsion spring with a whole number of
    # coils (TorsionSpring.nr_coils is an int); reject a fractional value here
    # with a clear message instead of letting pydantic raise a 500.
    nr_coils = parse_int(request.POST.get('numero_espiras'), 0, 'numero_espiras')
    # The coil pitch must be at least the wire diameter, otherwise the coils
    # would overlap. Checked here so the user gets a clear, translated error.
    check_pitch_not_below_wire(
        datos_entrada_muelle.get('pitch'),
        datos_entrada_muelle.get('diametro_hilo'),
    )
    muelle.set_geometry(
        mean_diameter=datos_entrada_muelle.get('diametro_medio'),
        nr_coils=nr_coils,
        pitch=datos_entrada_muelle.get('pitch'),
        free_angle=datos_entrada_muelle.get('angulo_libre'),
        fixed_leg_radius=datos_entrada_muelle.get('longitud_sujecion'),
        mobile_leg_radius=datos_entrada_muelle.get('Radio_sujecion')
    )
    angulo_inicial = datos_entrada_muelle.get('angulo_inicial')
    angulo_final = datos_entrada_muelle.get('angulo_final')
    muelle.add_position(angulo_inicial)
    muelle.add_position(angulo_final)

    def build_curve(graph_method_name, data_method_name):
        """Generates a curve if the class implements the required methods."""
        if not hasattr(muelle, graph_method_name):
            print(f"MuelleTorsion does not implement {graph_method_name}()")
            return None
        if not hasattr(muelle, data_method_name):
            print(f"MuelleTorsion does not implement {data_method_name}()")
            return None
        try:
            curva_imagen_b64 = getattr(muelle, graph_method_name)()
            return {
                'imagen': curva_imagen_b64,
                'datos': getattr(muelle, data_method_name)()
            }
        except Exception as graph_error:
            print(f"Error generating {graph_method_name}: {graph_error}")
            return None

    curva_esfuerzo_vs_position = build_curve(
        'get_forces_vs_position_graph',
        'get_data_positions',
    )

    curva_esfuerzo_vs_travel = build_curve(
        'get_forces_vs_travel_graph',
        'get_data_travels',
    )

    curva_diametros_vs_posicion = build_curve(
        'get_diameter_vs_position_graph',
        'get_data_positions',
    )

    goodman_data = None
    try:
        goodman_data = muelle.create_goodman_diagram()
    except Exception:
        goodman_data = None

    props = muelle.get_spring_properties()

    def _num(value, ndigits=2):
        """Plain rounded number from a float or a pint Quantity (N/D-safe)."""
        if value is None:
            return None
        if hasattr(value, 'magnitude'):
            value = value.magnitude
        try:
            return round(float(value), ndigits)
        except (TypeError, ValueError):
            return value

    def _fmt(value, unit, ndigits=2):
        """Rounded value with its unit appended, e.g. '13.7 mm' (N/D-safe)."""
        number = _num(value, ndigits)
        if number is None:
            return None
        sep = '' if unit == '°' else ' '
        return f"{number}{sep}{unit}"

    _MM = 'mm'
    _DEG = '°'          # degree sign
    _MPA = 'N/mm²'      # N/mm^2

    # The shared results template (_calculadora_results.html) reads Spanish
    # keys; get_spring_properties() returns English ones, so map them here,
    # rounding the values and appending their units, otherwise every field
    # shows "N/D" (or a raw pint Quantity such as "1.2 millimeter").
    resultado = {
        'material_nombre': props.get('material'),
        'modulo_corte': _fmt(getattr(muelle.material, 'shear_modulus', None), _MPA),
        'modulo_young': _fmt(props.get('young_modulus'), _MPA),
        'diametro_hilo': _fmt(props.get('wire_diameter'), _MM),
        'diametro_medio': _fmt(props.get('mean_diameter'), _MM),
        'diametro_exterior': _fmt(props.get('outer_diameter'), _MM),
        'diametro_interior': _fmt(props.get('inner_diameter'), _MM),
        'numero_espiras': props.get('nr_coils'),
        'numero_espiras_utiles': _num(props.get('nr_active_coils'), 1),
        'pitch': _fmt(props.get('pitch'), _MM),
        'ancho_muelle': _fmt(props.get('spring_width'), _MM),
        'angulo_libre': _fmt(props.get('free_angle'), _DEG),
        'angulo_tangencias': _fmt(props.get('tangency_angle'), _DEG),
        'longitud_hilo_total': _fmt(props.get('wire_length_total'), _MM),
        'longitud_hilo_cuerpo': _fmt(props.get('body_wire_length'), _MM),
        'constante_muelle': _fmt(props.get('spring_constant'), 'N·mm/rad', 3),
        'indice_muelle': _num(props.get('spring_index')),
        'factor_wahl': _num(props.get('wahl_factor'), 3),
        'factor_wahl_eval': _num(props.get('wahl_factor_eval'), 3),
        'factor_wahl_category': props.get('wahl_factor_category'),
        'momento_resistente': _fmt(props.get('resisting_moment'), 'mm^4'),
        'radious_leg_fija': _fmt(props.get('fixed_leg_radius'), _MM),
        'long_leg_fija': _fmt(props.get('fixed_leg_length'), _MM),
        'radious_leg_movil': _fmt(props.get('mobile_leg_radius'), _MM),
        'long_leg_movil': _fmt(props.get('mobile_leg_length'), _MM),
        'numero_ciclos': props.get('number_cycles'),
        'shot_peening': props.get('shot_peening'),
    }

    resultado['puntos_trabajo'] = build_working_points(muelle)
    resultado['curva_esfuerzos'] = curva_esfuerzo_vs_position
    resultado['curva_recorrido'] = curva_esfuerzo_vs_travel
    resultado['curva_diametros'] = curva_diametros_vs_posicion
    resultado['diagrama_goodman'] = goodman_data
    return muelle, resultado, angulo_inicial, angulo_final


def calculadora_torsion(request):
    """Torsion spring calculator view"""
    resultado = None
    materials = get_available_materials()
    if request.method == 'POST':
        try:
            _muelle, resultado, _ai, _af = _calcular_muelle_torsion(request)
            for key, value in resultado.items():
                print(f"{key}: {value}")
        except Exception as e:
            resultado = build_error_result(e, 'Error calculating torsion spring')
    return render(request, 'muelles/calculadora_torsion.html', {
        'materiales': materials,
        'resultado': resultado
    })


@csrf_protect
def calculadora_torsion_pdf(request):
    """Generates the PDF report for the torsion calculator (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de torsión para generar el PDF.'), status=405)
    try:
        _muelle, resultado, _ai, _af = _calcular_muelle_torsion(request)
    except Exception as e:
        resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}}
    return build_spring_report_pdf_response(
        _('Reporte de Muelle de Torsión'), resultado, 'muelle_torsion_report.pdf'
    )


@csrf_protect
def calculadora_torsion_animacion(request):
    """Generates a GIF animation of the torsion spring rotation (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de torsión para generar la animación.'), status=405)
    try:
        muelle, _resultado, angulo_inicial, angulo_final = _calcular_muelle_torsion(request)
    except Exception as e:
        return HttpResponse(
            _('Error en los cálculos: %(error)s') % {'error': str(e)}, status=400
        )
    gif_bytes = build_twist_animation_gif(muelle, angulo_inicial, angulo_final)
    return animation_http_response(gif_bytes, 'muelle_torsion_animacion.gif')
