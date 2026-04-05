from django.shortcuts import render
import traceback
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import get_data_spring
from muelles.pymodels.material import Material
from muelles.lineal.compresion import MuelleCompresion


def calculadora_compresion(request):
    """Vista de la calculadora de muelles de compresión"""
    resultado = None
    materials = get_available_materials()
    muelle = None  # Inicializar la variable
    if request.method == 'POST':
        try:
            datos_entrada_muelle = get_data_spring(request)
            # Crear objeto Material desde el código
            material_obj = Material(nombre_material=datos_entrada_muelle['material'])

            muelle = MuelleCompresion(
                material=material_obj,  
                diametro_hilo=float(request.POST.get('diametro_hilo', 0))  # Usar el nombre correcto del HTML
            )

            diametro_medio = datos_entrada_muelle.get('diametro_medio')
            diametro_exterior = datos_entrada_muelle.get('diametro_exterior')
            diametro_interior = datos_entrada_muelle.get('diametro_interior')
            # diametros_proporcionados = [
            #     d for d in [diametro_medio, diametro_exterior, diametro_interior]
            #     if d is not None
            # ]
            # if len(diametros_proporcionados) != 1:
            #     raise ValueError(
            #         'Debe proporcionar exactamente una de las siguientes variables: '
            #     )

            muelle.validate_diameters(
                diametro_medio=diametro_medio
            )
            muelle.calculate_spring_properties(
                numero_espiras=datos_entrada_muelle['numero_espiras'],
                pitch=None,
                longitud_libre=datos_entrada_muelle['longitud_libre']
            )
            muelle_data = muelle.get_spring_data()

            def _to_float_mm(value):
                return float(value.magnitude) if hasattr(value, 'magnitude') else float(value)

            # Generar puntos para curvas: usa formulario o valores por defecto seguros.
            longitud_libre = _to_float_mm(muelle.longitud_libre)
            longitud_bloqueo = _to_float_mm(muelle.longitud_bloqueo)
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

            muelle.vaciar_tablas()
            muelle.add_posicion_carga(longitud_inicial)
            muelle.add_posicion_carga(longitud_final)

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

            # Generar curva de esfuerzos vs recorrido
            curva_esfuerzo_vs_travel = build_curve(
                'get_forces_vs_travel_graph',
                'get_data_travels',
            )

            curva_esfuerzo_vs_position = build_curve(
                'get_forces_vs_position_graph',
                'get_data_positions',
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
            muelle.shot_peening = datos_entrada_muelle['shot_peening']
            muelle.numero_ciclos = datos_entrada_muelle['numero_ciclos']
            try:
                # Si el usuario envió longitudes, pasar esas; si no, el método usará valores por defecto
                goodman_data = muelle.create_goodman_diagram()
            except Exception:
                goodman_data = None
            resultado = {
                    'material_nombre': muelle.material.nombre_material,
                    'modulo_corte': muelle.material.shear_modulus,
                    'modulo_young': muelle.material.young_modulus,
                    'diametro_medio': round(muelle.diametro_medio, 2),
                    'diametro_hilo': round(muelle.diametro_hilo, 2),
                    'indice_muelle': round(muelle.indice_muelle, 2),
                    'constante_muelle': round(muelle.constante_muelle, 2),
                    'pitch': round(muelle.pitch, 2),
                    'numero_espiras_utiles': round(muelle.numero_espiras_utiles, 1),
                    'longitud_hilo': round(muelle.longitud_hilo, 2),
                    'factor_wahl': round(muelle.factor_wahl, 3),
                    'longitud_libre': muelle.longitud_libre,
                    'numero_espiras': muelle.numero_espiras,
                    'diametro_exterior': muelle.diametro_exterior,
                    'diametro_interior': muelle.diametro_interior,
                    'longitud_bloqueo': round(muelle.longitud_bloqueo, 2),
                    'curva_esfuerzos': curva_esfuerzo_vs_position,
                    'curva_recorrido': curva_esfuerzo_vs_travel,
                    'curva_diametros': curva_diametros_vs_posicion,
                    'diagrama_goodman': goodman_data,
                    'numero_ciclos': muelle.numero_ciclos,
                    'shot_peening': muelle.shot_peening
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
    return render(request, 'muelles/calculadora_compresion.html', {
        'resultado': resultado,
        'materiales': materials,
    })

