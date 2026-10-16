from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import (
    get_data_spring,
    build_error_result,
    build_working_points,
)
from muelles.views.spring_animation import (
    animation_http_response,
    build_compression_animation_gif,
)
from muelles.views.spring_report_pdf import build_spring_report_pdf_response
from springcalc import Material, CompressionSpringGeneral, ureg


def _to_float_mm(value):
    return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)


def _calcular_muelle_conico_pitch_variable(request):
    """Runs the variable-pitch conical calculator computation.

    Returns (spring, result, start_length, end_length) on success. Exceptions
    are propagated so each view can decide how to display the error.
    """
    datos_entrada_muelle = get_data_spring(request)
    material_obj = Material(material_name=datos_entrada_muelle['material'])

    muelle = CompressionSpringGeneral(
        material=material_obj,
        wire_diameter=datos_entrada_muelle.get('diametro_hilo') or 0.0
    )

    diametro_medio_superior = float(datos_entrada_muelle['diametro_medio_superior'])
    diametro_medio_inferior = float(datos_entrada_muelle['diametro_medio_inferior'])
    longitud_libre = float(datos_entrada_muelle['longitud_libre'])
    pitch_superior = float(datos_entrada_muelle['pitch_superior'])
    pitch_inferior = float(datos_entrada_muelle['pitch_inferior'])

    free_length_qty = longitud_libre * ureg.mm
    diametro_superior_qty = diametro_medio_superior * ureg.mm
    diametro_inferior_qty = diametro_medio_inferior * ureg.mm

    # The wire centerline runs from d/2 above the base to d/2 below the free
    # end, so it spans the free length minus one wire diameter.
    centerline_length_qty = free_length_qty - muelle.wire_diameter

    def func_diametro(h):
        # Linear interpolation: h=0 at the base (lower diameter),
        # h=centerline_length at the free end (upper diameter).
        return diametro_inferior_qty + (diametro_superior_qty - diametro_inferior_qty) * (h / centerline_length_qty)

    # springcalc evaluates the pitch ~100k times (nested quad inside fsolve),
    # and pint arithmetic dominates the cost, so the profile runs on plain
    # floats in mm and only wraps the result in a Quantity on the way out.
    wire_mm = _to_float_mm(muelle.wire_diameter)
    centerline_mm = _to_float_mm(centerline_length_qty)
    pitch_inferior_mm = pitch_inferior
    pitch_delta_mm = pitch_superior - pitch_inferior
    interior_mm = centerline_mm - 2 * wire_mm
    mm_units = ureg.mm

    def _interior_pitch_mm(h_mm):
        # h_mm is measured from the interior zone's own start (h=wire_mm),
        # not from the spring's base (h=0): otherwise this reaches
        # pitch_superior_mm one wire diameter *before* top_start_mm and then
        # keeps extrapolating past it for the rest of the zone. With a wire
        # diameter that's a sizeable fraction of the free length (or a large
        # pitch_inferior/pitch_superior spread), that extrapolation pushed
        # the pitch through zero into negative values -- 2*pi/pitch is then
        # a genuine pole, which is what made quad report the integral as
        # "probably divergent" instead of merely warning about subdivisions.
        return pitch_inferior_mm + pitch_delta_mm * ((h_mm - wire_mm) / interior_mm)

    # The closed end zones (pitch = wire diameter) used to meet the interior
    # formula with a hard step, e.g. jumping from a 2 mm closed pitch straight
    # to an ~12 mm working pitch at a single point. springcalc integrates
    # 1/pitch to solve each coil's position (calculate_theta_max, then a
    # per-point fsolve+quad in get_h_theta_development), and a real jump in
    # pitch is a real jump in that integrand -- which is what was driving
    # scipy's quad/fsolve to stall near it (the "maximum subdivisions
    # achieved" / "not making good progress" warnings, and the multi-second
    # slowdown that came with them). Ramping linearly across each closed zone
    # instead keeps the pitch value continuous; only its slope still kinks at
    # the two junctions, which quad/fsolve handle far more gracefully than an
    # outright jump. With the offset above, the interior formula lands
    # exactly on pitch_inferior_mm/pitch_superior_mm at the zone boundaries,
    # so the ramp's far endpoints are just the entered pitches themselves.
    pitch_at_wire_mm = pitch_inferior_mm
    top_start_mm = centerline_mm - wire_mm
    pitch_at_top_mm = pitch_superior

    def func_pitch(h):
        # springcalc always passes h in mm.
        h_mm = h.magnitude
        if h_mm < wire_mm:
            return ureg.Quantity(wire_mm + (pitch_at_wire_mm - wire_mm) * (h_mm / wire_mm), mm_units)
        if h_mm > top_start_mm:
            return ureg.Quantity(
                pitch_at_top_mm + (wire_mm - pitch_at_top_mm) * ((h_mm - top_start_mm) / wire_mm), mm_units
            )
        return ureg.Quantity(_interior_pitch_mm(h_mm), mm_units)

    # springcalc integrates the coils over [0, free_length], so hand it the
    # centerline span and restore the real free length afterwards: loads,
    # travels and the reported free length are measured on the outer length.
    muelle.set_geometry(func_D=func_diametro, func_p=func_pitch, free_length=centerline_length_qty)
    muelle.calculate_spring_properties()
    muelle.free_length = free_length_qty

    longitud_libre_mm = _to_float_mm(muelle.free_length)
    longitud_bloqueo = _to_float_mm(muelle.solid_length)
    longitud_inicial = datos_entrada_muelle.get('longitud_inicial')
    longitud_final = datos_entrada_muelle.get('longitud_final')

    if longitud_inicial is None and longitud_final is None:
        longitud_inicial = longitud_libre_mm
        longitud_final = max(longitud_bloqueo, longitud_libre_mm * 0.85)
    elif longitud_inicial is None:
        longitud_inicial = longitud_libre_mm
    elif longitud_final is None:
        longitud_final = max(longitud_bloqueo, float(longitud_inicial) * 0.9)

    longitud_inicial = max(float(longitud_inicial), longitud_bloqueo) * ureg.mm
    longitud_final = max(float(longitud_final), longitud_bloqueo) * ureg.mm

    muelle.empty_tables()
    muelle.add_load_position(longitud_inicial)
    muelle.add_load_position(longitud_final)

    def build_curve(graph_method_name, data_method_name):
        if not hasattr(muelle, graph_method_name):
            return None
        try:
            return {
                'imagen': getattr(muelle, graph_method_name)(),
                'datos': getattr(muelle, data_method_name)(),
            }
        except Exception as graph_error:
            print(f"Error generating {graph_method_name}: {graph_error}")
            return None

    curva_esfuerzo_vs_travel = build_curve(
        'get_forces_vs_travel_graph',
        'get_data_travels',
    )

    curva_esfuerzo_vs_position = build_curve(
        'get_forces_vs_position_graph',
        'get_data_positions',
    )

    curva_diametros_vs_posicion = build_curve(
        'get_diameter_vs_position_graph',
        'get_data_positions',
    )

    goodman_data = None
    muelle.shot_peening = datos_entrada_muelle['shot_peening']
    muelle.number_cycles = datos_entrada_muelle['numero_ciclos']
    try:
        goodman_data = muelle.create_goodman_diagram()
    except Exception:
        goodman_data = None

    diametro_medio_actual = muelle.f_mean_diameter(muelle.free_length / 2)
    pitch_actual = func_pitch(0 * ureg.mm)

    resultado = {
        'material_nombre': muelle.material.material_name,
        'modulo_corte': muelle.material.shear_modulus,
        'modulo_young': muelle.material.young_modulus,
        'diametro_medio': round(diametro_medio_actual, 2),
        'diametro_medio_superior': round(diametro_superior_qty, 2),
        'diametro_medio_inferior': round(diametro_inferior_qty, 2),
        'diametro_hilo': round(muelle.wire_diameter, 2),
        'indice_muelle': round(muelle.spring_index, 2),
        'constante_muelle': round(muelle.spring_constant, 2),
        'pitch': round(pitch_actual, 2),
        'longitud_hilo': round(muelle.wire_length, 2),
        'factor_wahl': round(muelle.wahl_factor, 3),
        'longitud_libre': muelle.free_length,
        'numero_espiras': round(muelle.nr_coils, 1),
        'longitud_bloqueo': round(muelle.solid_length, 2),
        'curva_esfuerzos': curva_esfuerzo_vs_position,
        'curva_recorrido': curva_esfuerzo_vs_travel,
        'curva_diametros': curva_diametros_vs_posicion,
        'diagrama_goodman': goodman_data,
        'numero_ciclos': muelle.number_cycles,
        'shot_peening': muelle.shot_peening,
        'puntos_trabajo': build_working_points(muelle),
    }
    return muelle, resultado, _to_float_mm(longitud_inicial), _to_float_mm(longitud_final)


@csrf_protect
@ensure_csrf_cookie
def calculadora_conico_pitch_variable(request):
    """Variable-pitch conical compression spring calculator view"""
    resultado = None
    materials = get_available_materials()
    if request.method == 'POST':
        try:
            _muelle, resultado, _li, _lf = _calcular_muelle_conico_pitch_variable(request)
        except Exception as e:
            resultado = build_error_result(e, 'Error calculating variable-pitch conical spring')
    return render(request, 'muelles/calculadora_conico_pitch_variable.html', {
        'resultado': resultado,
        'materiales': materials,
    })


@csrf_protect
def calculadora_conico_pitch_variable_pdf(request):
    """Generates the PDF report for the variable-pitch conical spring (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de cónico de paso variable para generar el PDF.'), status=405)
    try:
        _muelle, resultado, _li, _lf = _calcular_muelle_conico_pitch_variable(request)
    except Exception as e:
        resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}}
    return build_spring_report_pdf_response(
        _('Reporte de Muelle Cónico de Paso Variable'), resultado, 'muelle_conico_pitch_variable_report.pdf'
    )


@csrf_protect
def calculadora_conico_pitch_variable_animacion(request):
    """Generates a GIF animation of the variable-pitch conical spring (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(
            _('Usa el formulario de cónico de paso variable para generar la animación.'), status=405
        )
    try:
        muelle, _resultado, longitud_inicial, longitud_final = _calcular_muelle_conico_pitch_variable(request)
    except Exception as e:
        return HttpResponse(
            _('Error en los cálculos: %(error)s') % {'error': str(e)}, status=400
        )
    gif_bytes = build_compression_animation_gif(muelle, longitud_inicial, longitud_final)
    return animation_http_response(gif_bytes, 'muelle_conico_pitch_variable_animacion.gif')
