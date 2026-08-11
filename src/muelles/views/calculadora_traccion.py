
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
from muelles.views.spring_animation import (
    animation_http_response,
    build_compression_animation_gif,
)
from muelles.views.spring_report_pdf import build_spring_report_pdf_response
from springcalc import Material, ExtensionSpring
from muelles.views.get_data_spring import get_data_spring
from muelles.views.get_available_materials import get_available_materials
import traceback


def _calcular_muelle_traccion(request):
    """Runs the extension calculator computation from the POST data.

    Returns (spring, result, start_length, end_length) on success. Exceptions
    are propagated so each view can decide how to display the error.
    """
    datos_entrada_muelle = get_data_spring(request)
    material_obj = Material(material_name=datos_entrada_muelle['material'])

    muelle = ExtensionSpring(
        material=material_obj,
        wire_diameter=float(request.POST.get('diametro_hilo', 0))
    )

    diametro_medio = datos_entrada_muelle.get('diametro_medio')

    muelle.set_diameter(
        mean_diameter=diametro_medio,
    )
    muelle.calculate_spring_properties(
        nr_coils=datos_entrada_muelle['numero_espiras'],
        pitch=None,
        free_length=datos_entrada_muelle['longitud_libre']
    )

    tension_inicial = float(request.POST.get('tension_inicial', 0)) if request.POST.get('tension_inicial') else 0.0
    muelle.set_initial_stress(tension_inicial)

    longitud_libre = float(request.POST.get('longitud_libre', 0))
    numero_espiras = float(request.POST.get('numero_espiras', 0))
    numero_ciclos = float(request.POST.get('numero_ciclos', 1e6))  # Default value of 1 million cycles

    # Assign the number of cycles to the spring object (already read from the form)
    muelle.number_cycles = numero_ciclos
    muelle.shot_peening = request.POST.get('shot_peening') == 'si'

    muelle.calculate_spring_properties(
        nr_coils=numero_espiras,
        pitch=None,
        free_length=longitud_libre
    )
    muelle_data = muelle.get_spring_data()

    def _to_float_mm(value):
        return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)

    # Generate curve points: use the form values or a default extension.
    longitud_libre_mm = _to_float_mm(muelle.free_length)
    longitud_inicial = datos_entrada_muelle.get('longitud_inicial')
    longitud_final = datos_entrada_muelle.get('longitud_final')

    if longitud_inicial is None and longitud_final is None:
        longitud_inicial = longitud_libre_mm
        longitud_final = longitud_libre_mm * 1.10
    elif longitud_inicial is None:
        longitud_inicial = longitud_libre_mm
    elif longitud_final is None:
        longitud_final = float(longitud_inicial) * 1.10

    longitud_inicial = float(longitud_inicial)
    longitud_final = float(longitud_final)

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

    # Generate stress curve using the MuelleLineal object's method
    curva_esfuerzo_vs_position = build_curve(
        'get_forces_vs_position_graph',
        'get_data_positions',
    )

    # Generate stress vs travel curve
    curva_esfuerzo_vs_travel = build_curve(
        'get_forces_vs_travel_graph',
        'get_data_travels',
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
    try:
        goodman_data = muelle.create_goodman_diagram()
    except Exception:
        goodman_data = None

    resultado = {
            'material_nombre': muelle.material.material_name,
            'modulo_corte': muelle.material.shear_modulus,
            'diametro_medio': round(muelle_data.get('mean_diameter', 0), 2),
            'diametro_hilo': round(muelle_data.get('wire_diameter', 0), 2),
            'indice_muelle': round(muelle_data.get('spring_index', 0), 2),
            'constante_muelle': round(muelle_data.get('spring_constant', 0), 2),
            'pitch': round(muelle_data.get('pitch', 0), 2),
            'numero_espiras_utiles': round(muelle_data.get('nr_active_coils', 0), 1),
            'longitud_hilo': round(muelle_data.get('wire_length', 0), 2),
            'factor_wahl': round(muelle_data.get('wahl_factor', 0), 3),
            'longitud_libre': muelle.free_length,
            'numero_espiras': muelle.nr_coils,
            'diametro_exterior': muelle_data.get('mean_diameter', 0) + muelle_data.get('wire_diameter', 0),
            'diametro_interior': muelle_data.get('mean_diameter', 0) - muelle_data.get('wire_diameter', 0),
            'shot_peening': muelle.shot_peening,
            'curva_esfuerzos': curva_esfuerzo_vs_position,
            'curva_recorrido': curva_esfuerzo_vs_travel,
            'curva_diametros': curva_diametros_vs_posicion,
            'diagrama_goodman': goodman_data,
            'numero_ciclos': muelle.number_cycles,
            'tension_inicial': round(muelle_data.get('initial_stress', 0), 2)
        }
    return muelle, resultado, longitud_inicial, longitud_final


def calculadora_traccion(request):
    """Extension spring calculator view"""
    resultado = None
    materials = get_available_materials()
    if request.method == 'POST':
        try:
            _muelle, resultado, _li, _lf = _calcular_muelle_traccion(request)
        except Exception as e:
            print(f"Error calculating spring: {e}")
            tb = traceback.format_exc()
            resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}, 'traceback': tb}
    return render(request, 'muelles/calculadora_traccion.html', {
            'resultado': resultado,
            'materiales': materials,
        })


@csrf_protect
def calculadora_traccion_pdf(request):
    """Generates the PDF report for the extension calculator (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de tracción para generar el PDF.'), status=405)
    try:
        _muelle, resultado, _li, _lf = _calcular_muelle_traccion(request)
    except Exception as e:
        resultado = {'error': _('Error en los cálculos: %(error)s') % {'error': str(e)}}
    return build_spring_report_pdf_response(
        _('Reporte de Muelle de Tracción'), resultado, 'muelle_traccion_report.pdf'
    )


@csrf_protect
def calculadora_traccion_animacion(request):
    """Generates a GIF animation of the spring extension (opens inline)."""
    if request.method != 'POST':
        return HttpResponse(_('Usa el formulario de tracción para generar la animación.'), status=405)
    try:
        muelle, _resultado, longitud_inicial, longitud_final = _calcular_muelle_traccion(request)
    except Exception as e:
        return HttpResponse(
            _('Error en los cálculos: %(error)s') % {'error': str(e)}, status=400
        )
    gif_bytes = build_compression_animation_gif(muelle, longitud_inicial, longitud_final)
    return animation_http_response(gif_bytes, 'muelle_traccion_animacion.gif')
