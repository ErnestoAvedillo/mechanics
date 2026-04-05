
from django.shortcuts import render
from muelles.pymodels.material import Material
from muelles.lineal.traccion import MuelleTraccion
from muelles.views.get_data_spring import get_data_spring
from muelles.views.get_available_materials import get_available_materials
import traceback

def calculadora_traccion(request):
    """Vista de la calculadora de muelles de tracción"""
    resultado = None
    materials = get_available_materials()
    muelle = None  # Inicializar la variable
    if request.method == 'POST':
        try:
            datos_entrada_muelle = get_data_spring(request)
                    # Crear objeto Material desde el código
            material_obj = Material(nombre_material=datos_entrada_muelle['material'])

            muelle = MuelleTraccion(
                material=material_obj,  
                diametro_hilo=float(request.POST.get('diametro_hilo', 0))  # Usar el nombre correcto del HTML
            )

            diametro_medio = datos_entrada_muelle.get('diametro_medio')

            muelle.validate_diameters(
                diametro_medio=diametro_medio,
            )
            muelle.calculate_spring_properties(
                numero_espiras=datos_entrada_muelle['numero_espiras'],
                pitch=None,
                longitud_libre=datos_entrada_muelle['longitud_libre']
            )
            muelle.set_tension_inicial(
                float(request.POST.get('tension_inicial', 0)) if request.POST.get('tension_inicial') else 0.0
            )
            muelle_data = muelle.get_spring_data()

            tension_inicial = float(request.POST.get('tension_inicial', 0)) if request.POST.get('tension_inicial') else 0.0
            muelle.set_tension_inicial(tension_inicial)
            
            longitud_libre = float(request.POST.get('longitud_libre', 0))
            numero_espiras = float(request.POST.get('numero_espiras', 0))
            numero_ciclos = float(request.POST.get('numero_ciclos', 1e6))  # Valor por defecto de 1 millón de ciclos

            # Asignar el número de ciclos al objeto muelle (ya leído desde el formulario)
            muelle.numero_ciclos = numero_ciclos
            muelle.shot_peening = request.POST.get('shot_peening') == 'si'

            muelle.calculate_spring_properties(
                numero_espiras=numero_espiras,
                pitch=None,
                longitud_libre=longitud_libre
            )
            muelle_data = muelle.get_spring_data()

            def _to_float_mm(value):
                return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)

            # Generar puntos para curvas: usa formulario o extension por defecto.
            longitud_libre_mm = _to_float_mm(muelle.longitud_libre)
            longitud_inicial = datos_entrada_muelle.get('longitud_inicial')
            longitud_final = datos_entrada_muelle.get('longitud_final')

            if longitud_inicial is None and longitud_final is None:
                longitud_inicial = longitud_libre_mm
                longitud_final = longitud_libre_mm * 1.10
            elif longitud_inicial is None:
                longitud_inicial = longitud_libre_mm
            elif longitud_final is None:
                longitud_final = float(longitud_inicial) * 1.10

            muelle.vaciar_tablas()
            muelle.add_posicion_carga(float(longitud_inicial))
            muelle.add_posicion_carga(float(longitud_final))

            def build_curve(graph_method_name, data_method_name):
                if not hasattr(muelle, graph_method_name):
                    return None
                try:
                    return {
                        'imagen': getattr(muelle, graph_method_name)(),
                        'datos': getattr(muelle, data_method_name)(),
                    }
                except Exception as graph_error:
                    print(f"Error generando {graph_method_name}: {graph_error}")
                    return None

            # Generar curva de esfuerzos usando método del objeto MuelleLineal
            curva_esfuerzo_vs_position = build_curve(
                'get_forces_vs_position_graph',
                'get_data_positions',
            )

            # Generar curva de esfuerzos vs recorrido
            curva_esfuerzo_vs_travel = build_curve(
                'get_forces_vs_travel_graph',
                'get_data_travels',
            )

            #Generar curva de diametros vs posición
            curva_diametros_vs_posicion = None
            try:
                curva_imagen_b64 = muelle.get_diameter_vs_position_graph()
                curva_diametros_vs_posicion = {
                    'imagen': curva_imagen_b64,
                    'datos': muelle.get_data_positions()
                }
            except Exception:
                curva_diametros_vs_posicion = None

            # Generar diagrama de Goodman usando método del objeto MuelleLineal
            goodman_data = None
            try:
                # Si el usuario envió longitudes, pasar esas; si no, el método usará valores por defecto
                goodman_data = muelle.create_goodman_diagram()
            except Exception:
                goodman_data = None

            resultado = {
                    'material_nombre': muelle.material.nombre_material,
                    'modulo_corte': muelle.material.shear_modulus,
                    'diametro_medio': round(muelle_data.get('diametro_medio', 0), 2),
                    'diametro_hilo': round(muelle_data.get('diametro_hilo', 0), 2),
                    'indice_muelle': round(muelle_data.get('indice_muelle', 0), 2),
                    'constante_muelle': round(muelle_data.get('constante_muelle', 0), 2),
                    'pitch': round(muelle_data.get('pitch', 0), 2),
                    'numero_espiras_utiles': round(muelle_data.get('numero_espiras_utiles', 0), 1),
                    'longitud_hilo': round(muelle_data.get('longitud_hilo', 0), 2),
                    'factor_wahl': round(muelle_data.get('factor_wahl', 0), 3),
                    'longitud_libre': muelle.longitud_libre,
                    'numero_espiras': muelle.numero_espiras,
                    'diametro_exterior': muelle_data.get('diametro_medio', 0) + muelle_data.get('diametro_hilo', 0),
                    'diametro_interior': muelle_data.get('diametro_medio', 0) - muelle_data.get('diametro_hilo', 0),
                    'shot_peening': muelle.shot_peening,
                    'curva_esfuerzos': curva_esfuerzo_vs_position,
                    'curva_recorrido': curva_esfuerzo_vs_travel,
                    'curva_diametros': curva_diametros_vs_posicion,
                    'diagrama_goodman': goodman_data,
                    'numero_ciclos': muelle.numero_ciclos,
                    'shot_peening': muelle.shot_peening,
                    'tension_inicial': round(muelle_data.get('tension_inicial', 0), 2)
                }
        except Exception as e:
            print(f"Error en cálculo de muelle: {e}")
            tb = traceback.format_exc()
            if muelle is not None:
                try:
                    muelle_data = muelle.get_spring_data()
                    for key, value in muelle_data.items():
                        print(f"{key}: {value}")
                except:
                    pass
            resultado = {'error': f'Error en los cálculos: {str(e)}', 'traceback': tb}
    return render(request, 'muelles/calculadora_traccion.html', {
            'resultado': resultado,
            'materiales': materials,
        })
