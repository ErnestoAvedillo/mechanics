from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
import traceback
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import get_data_spring
from muelles.views.spring_animation import (
    animation_http_response,
    build_compression_animation_gif,
)
from muelles.views.spring_report_pdf import build_spring_report_pdf_response
from springcalc import Material
from springcalc import CompressionSpring


def _calcular_muelle_compresion(request):
    """Runs the compression calculator computation from the POST data.

    Returns (spring, result, start_length, end_length) on success. Exceptions
    are propagated so each view can decide how to display the error.
    """
    datos_entrada_muelle = get_data_spring(request)
    material_obj = Material(material_name=datos_entrada_muelle['material'])

    muelle = CompressionSpring(
        material=material_obj,
        wire_diameter=float(request.POST.get('diametro_hilo', 0))
    )

    diametro_medio = datos_entrada_muelle.get('diametro_medio')

    muelle.set_diameter(
        mean_diameter=diametro_medio
    )
    muelle.calculate_spring_properties(
        nr_coils=datos_entrada_muelle['numero_espiras'],
        pitch=None,
        free_length=datos_entrada_muelle['longitud_libre']
    )

    def _to_float_mm(value):
        return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)

    longitud_libre = _to_float_mm(muelle.free_length)
    longitud_bloqueo = _to_float_mm(muelle.solid_length)
    longitud_inicial = datos_entrada_muelle.get('longitud_inicial')
    longitud_final = datos_entrada_muelle.get('longitud_final')

    if longitud_inicial is None and longitud_final is None:
        longitud_inicial = longitud_libre
        longitud_final = max(longitud_bloqueo, longitud_libre * 0.85)
    elif longitud_inicial is None:
        longitud_inicial = longitud_libre
    elif longitud_final is None:
        longitud_final = max(longitud_bloqueo, float(longitud_inicial) * 0.9)

    longitud_inicial = max(float(longitud_inicial), longitud_bloqueo)
    longitud_final = max(float(longitud_final), longitud_bloqueo)

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

    # Generate stress vs travel curve
    curva_esfuerzo_vs_travel = build_curve(
        'get_forces_vs_travel_graph',
        'get_data_travels',
    )

    curva_esfuerzo_vs_position = build_curve(
        'get_forces_vs_position_graph',
        'get_data_positions',
    )

    #Generate diameter vs position curve
    curva_diametros_vs_posicion = None
    try:
        curva_imagen_b64 = muelle.get_diameter_vs_position_graph()
        curva_diametros_vs_posicion = {
            'imagen': curva_imagen_b64,
            'datos': muelle.get_data_positions()
        }
    except Exception:
        curva_diametros_vs_posicion = None

    # Generate Goodman diagram using the MuelleLineal object's method
    goodman_data = None
    muelle.shot_peening = datos_entrada_muelle['shot_peening']
    muelle.number_cycles = datos_entrada_muelle['numero_ciclos']
    try:
        # If the user submitted lengths, pass those; otherwise the method will use default values
        goodman_data = muelle.create_goodman_diagram()
    except Exception:
        goodman_data = None
    resultado = {
            'material_nombre': muelle.material.material_name,
            'modulo_corte': muelle.material.shear_modulus,
            'modulo_young': muelle.material.young_modulus,
            'diametro_medio': round(muelle.mean_diameter, 2),
            'diametro_hilo': round(muelle.wire_diameter, 2),
            'indice_muelle': round(muelle.spring_index, 2),
            'constante_muelle': round(muelle.spring_constant, 2),
            'pitch': round(muelle.pitch, 2),
            'numero_espiras_utiles': round(muelle.nr_active_coils, 1),
            'longitud_hilo': round(muelle.wire_length, 2),
            'factor_wahl': round(muelle.wahl_factor, 3),
            'longitud_libre': muelle.free_length,
            'numero_espiras': muelle.nr_coils,
            'diametro_exterior': muelle.outer_diameter,
            'diametro_interior': muelle.inner_diameter,
            'longitud_bloqueo': round(muelle.solid_length, 2),
            'curva_esfuerzos': curva_esfuerzo_vs_position,
            'curva_recorrido': curva_esfuerzo_vs_travel,
            'curva_diametros': curva_diametros_vs_posicion,
            'diagrama_goodman': goodman_data,
            'numero_ciclos': muelle.number_cycles,
            'shot_peening': muelle.shot_peening
        }
    return muelle, resultado, longitud_inicial, longitud_final


@csrf_protect
@ensure_csrf_cookie
def calculadora_compresion(request):
    """Compression spring calculator view"""
    resultado = None
    materials = get_available_materials()
    if request.method == 'POST':
        try:
            _muelle, resultado, _li, _lf = _calcular_muelle_compresion(request)
        except Exception as e:
            print(f"Error calculating spring: {e}")
            tb = traceback.format_exc()
            resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}, 'traceback': tb}
    return render(request, 'muelles/calculadora_compresion.html', {
        'resultado': resultado,
        'materiales': materials,
    })


@csrf_protect
def calculadora_compresion_pdf(request):
    """Generates the PDF report for the compression calculator (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de compresión para generar el PDF.'), status=405)
    try:
        _muelle, resultado, _li, _lf = _calcular_muelle_compresion(request)
    except Exception as e:
        resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}}
    return build_spring_report_pdf_response(
        _('Reporte de Muelle de Compresión'), resultado, 'muelle_compresion_report.pdf'
    )


@csrf_protect
def calculadora_compresion_animacion(request):
    """Generates a GIF animation of the spring compression (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de compresión para generar la animación.'), status=405)
    try:
        muelle, _resultado, longitud_inicial, longitud_final = _calcular_muelle_compresion(request)
    except Exception as e:
        return HttpResponse(
            _('Error en los cálculos: %(error)s') % {'error': str(e)}, status=400
        )
    gif_bytes = build_compression_animation_gif(muelle, longitud_inicial, longitud_final)
    return animation_http_response(gif_bytes, 'muelle_compresion_animacion.gif')
