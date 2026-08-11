from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
import traceback
import numpy as np
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import get_data_spring
from muelles.views.spring_animation import (
    animation_http_response,
    build_compression_animation_gif,
)
from muelles.views.spring_report_pdf import build_spring_report_pdf_response
from springcalc import Material, CompressionSpringGeneral, ureg


# def _add_load_position_from_curve(muelle, length, deflection_mm, force_n):
#     """Adds a load position using the simulated progressive compression curve
#     (simulate_progressive_compression) instead of the spring's mean constant:
#     in a 3K spring the load does not vary linearly with position, so
#     calculate_load_at_position (which uses that mean constant) would give an
#     incorrect load.
#     """
#     if length < muelle.solid_length:
#         raise ValueError(_("La posicion no puede ser menor que la longitud de bloqueo del muelle"))

#     travel = muelle.free_length - length
#     travel_mm = float(travel.to('mm').magnitude)
#     load_n = float(np.interp(travel_mm, deflection_mm, force_n))
#     load = load_n * ureg.N

#     muelle.position_length = length
#     stress = muelle.calculate_stress_at_position(load)
#     outer_diameter = muelle.calculate_outer_diameter_at_position(length)

#     muelle.positions.add_load_position(
#         position=length,
#         travel=travel,
#         load=load,
#         stress=stress,
#         outer_diameter=outer_diameter,
#         inner_diameter=max(outer_diameter - 2 * muelle.wire_diameter, 0 * ureg.mm),
#     )


def _calcular_muelle_2k(request):
    """Runs the 3K spring calculator computation (dual constant) from the
    POST data.

    Returns (spring, result, start_length, end_length) on success. Exceptions
    are propagated so each view can decide how to display the error.
    """
    datos_entrada_muelle = get_data_spring(request)
    material_obj = Material(material_name=datos_entrada_muelle['material'])

    muelle = CompressionSpringGeneral(
        material=material_obj,
        wire_diameter=float(request.POST.get('diametro_hilo', 0))
    )

    diametro_medio_qty = float(datos_entrada_muelle['diametro_medio']) * ureg.mm
    length_1_qty = float(datos_entrada_muelle['length_1']) * ureg.mm
    pitch_1_qty = float(datos_entrada_muelle['pitch_1']) * ureg.mm
    length_2_qty = float(datos_entrada_muelle['length_2']) * ureg.mm
    pitch_2_qty = float(datos_entrada_muelle['pitch_2']) * ureg.mm
    length_3_qty = float(datos_entrada_muelle['length_3']) * ureg.mm
    pitch_3_qty = float(datos_entrada_muelle['pitch_3']) * ureg.mm

    # Section 1 (closed, base) -> section 2 (open, body) -> section 3 (closed, free end).
    altura_transicion_1_qty = length_1_qty
    altura_transicion_2_qty = altura_transicion_1_qty + length_2_qty
    free_length_qty = altura_transicion_2_qty + length_3_qty

    def func_diametro(h):
        return diametro_medio_qty

    def func_pitch(h):
        if h < altura_transicion_1_qty:
            return pitch_1_qty
        if h < altura_transicion_2_qty:
            return pitch_2_qty
        return pitch_3_qty

    muelle.set_geometry(func_D=func_diametro, func_p=func_pitch, free_length=free_length_qty)
    muelle.calculate_spring_properties()

    def _to_float_mm(value):
        return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)

    longitud_libre_mm = _to_float_mm(muelle.free_length)
    longitud_bloqueo = _to_float_mm(muelle.solid_length)
    longitud_inicial = datos_entrada_muelle['longitud_inicial']
    longitud_final = datos_entrada_muelle['longitud_final']

    if longitud_inicial is None and longitud_final is None:
        longitud_inicial = longitud_libre_mm
        longitud_final = max(longitud_bloqueo, longitud_libre_mm * 0.85)
    elif longitud_inicial is None:
        longitud_inicial = longitud_libre_mm
    elif longitud_final is None:
        longitud_final = max(longitud_bloqueo, float(longitud_inicial) * 0.9)

    longitud_inicial_qty = max(float(longitud_inicial), longitud_bloqueo) * ureg.mm
    longitud_final_qty = max(float(longitud_final), longitud_bloqueo) * ureg.mm

    # # The "mean" constant that calculate_spring_properties leaves in
    # # muelle.spring_constant integrates the flexibility of the whole spring
    # # without accounting for one section binding before the other, so it
    # # is not useful for a 2K spring. The real two-slope curve comes from
    # # simulating the progressive compression (section-by-section coil
    # # collision).
    max_deflection_qty = muelle.free_length - muelle.solid_length
    deflection_hist, force_hist, stiffness_hist = muelle.simulate_progressive_compression(
        max_deflection=max_deflection_qty
    )
    # deflection_mm = deflection_hist.to('mm').magnitude
    # force_n = force_hist.to('N').magnitude

    stiffness_finite_mask = np.isfinite(stiffness_hist.magnitude)
    stiffness_finite = stiffness_hist[stiffness_finite_mask]
    constante_muelle_1 = round(stiffness_finite[0], 2) if stiffness_finite.size else None
    constante_muelle_2 = round(stiffness_finite[-1], 2) if stiffness_finite.size else None

    muelle.empty_tables()
    muelle.add_load_position(longitud_inicial_qty)
    muelle.add_load_position(longitud_final_qty)
    # _add_load_position_from_curve(muelle, longitud_inicial, deflection_mm, force_n)
    # _add_load_position_from_curve(muelle, longitud_final, deflection_mm, force_n)

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

    curva_esfuerzo_vs_travel = build_curve('get_forces_vs_travel_graph', 'get_data_travels')
    curva_esfuerzo_vs_position = build_curve('get_forces_vs_position_graph', 'get_data_positions')
    curva_diametros_vs_posicion = build_curve('get_diameter_vs_position_graph', 'get_data_positions')

    try:
        curva_progresiva = {
            'imagen': muelle.get_progressive_compression_graph(deflection_hist, force_hist),
            'datos': None,
        }
    except Exception as graph_error:
        print(f"Error generating progressive curve: {graph_error}")
        curva_progresiva = None

    goodman_data = None
    muelle.shot_peening = datos_entrada_muelle['shot_peening']
    muelle.number_cycles = datos_entrada_muelle['numero_ciclos']
    try:
        goodman_data = muelle.create_goodman_diagram()
    except Exception:
        goodman_data = None

    resultado = {
        'material_nombre': muelle.material.material_name,
        'modulo_corte': muelle.material.shear_modulus,
        'modulo_young': muelle.material.young_modulus,
        'diametro_medio': round(diametro_medio_qty, 2),
        'diametro_hilo': round(muelle.wire_diameter, 2),
        'indice_muelle': round(muelle.spring_index, 2),
        'constante_muelle_1': constante_muelle_1,
        'constante_muelle_2': constante_muelle_2,
        'pitch_1': round(pitch_1_qty, 2),
        'pitch_2': round(pitch_2_qty, 2),
        'pitch_3': round(pitch_3_qty, 2),
        'length_1': length_1_qty,
        'length_2': length_2_qty,
        'length_3': length_3_qty,
        'longitud_hilo': round(muelle.wire_length, 2),
        'factor_wahl': round(muelle.wahl_factor, 3),
        'longitud_libre': muelle.free_length,
        'numero_espiras': round(muelle.nr_coils, 1),
        'longitud_bloqueo': round(muelle.solid_length, 2),
        'curva_esfuerzos': curva_esfuerzo_vs_position,
        'curva_recorrido': curva_esfuerzo_vs_travel,
        'curva_diametros': curva_diametros_vs_posicion,
        'curva_progresiva': curva_progresiva,
        'diagrama_goodman': goodman_data,
        'numero_ciclos': muelle.number_cycles,
        'shot_peening': muelle.shot_peening,
    }
    return muelle, resultado, _to_float_mm(longitud_inicial), _to_float_mm(longitud_final)


@csrf_protect
@ensure_csrf_cookie
def calculadora_2k(request):
    """2K non-linear spring calculator view (dual constant)"""
    resultado = None
    materials = get_available_materials()
    if request.method == 'POST':
        try:
            _muelle, resultado, _li, _lf = _calcular_muelle_2k(request)
        except Exception as e:
            print(f"Error calculating 2K spring: {e}")
            tb = traceback.format_exc()
            resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}, 'traceback': tb}
    return render(request, 'muelles/calculadora_2k.html', {
        'resultado': resultado,
        'materiales': materials,
    })


@csrf_protect
def calculadora_2k_pdf(request):
    """Generates the PDF report for the 2K spring (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de muelle 2K para generar el PDF.'), status=405)
    try:
        _muelle, resultado, _li, _lf = _calcular_muelle_2k(request)
    except Exception as e:
        resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}}
    return build_spring_report_pdf_response(
        _('Reporte de Muelle 2K (No Lineal)'), resultado, 'muelle_2k_report.pdf'
    )


@csrf_protect
def calculadora_2k_animacion(request):
    """Generates a GIF animation of the 2K spring (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de muelle 2K para generar la animación.'), status=405)
    try:
        muelle, _resultado, longitud_inicial, longitud_final = _calcular_muelle_2k(request)
    except Exception as e:
        return HttpResponse(
            _('Error en los cálculos: %(error)s') % {'error': str(e)}, status=400
        )
    gif_bytes = build_compression_animation_gif(muelle, longitud_inicial, longitud_final)
    return animation_http_response(gif_bytes, 'muelle_2k_animacion.gif')
