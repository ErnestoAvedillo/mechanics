from django.shortcuts import render
import traceback
from muelles.views.get_available_materials import get_available_materials
from muelles.views.get_data_spring import get_data_spring
from muelles.pymodels.material import Material
from muelles.lineal.torsion import MuelleTorsion

def calculadora_torsion(request):
    """Vista de la calculadora de muelles de torsión"""
    resultado = None
    materials = get_available_materials()
    muelle = None  # Inicializar la variable
    if request.method == 'POST':
        try:
            # Aquí se pueden obtener los datos del formulario de torsión y realizar los cálculos correspondientes
            datos_entrada_muelle = get_data_spring(request)

            required_torsion_fields = {
                'diametro_medio': 'Diámetro medio',
                'numero_espiras': 'Número de espiras',
                'pitch': 'Pitch',
                'angulo_libre': 'Ángulo libre',
                'longitud_sujecion': 'Longitud de sujeción',
                'Radio_sujecion': 'Radio de sujeción',
            }
            missing_fields = [
                label for key, label in required_torsion_fields.items()
                if datos_entrada_muelle.get(key) is None
            ]
            if missing_fields:
                raise ValueError(
                    f"Faltan campos obligatorios para torsión: {', '.join(missing_fields)}"
                )

            muelle_data = {
                "Material": datos_entrada_muelle.get('material'),
                "diametro_hilo": datos_entrada_muelle.get('diametro_hilo'),
                'shot_peening': datos_entrada_muelle.get('shot_peening') == 'si',
                'numero_ciclos': datos_entrada_muelle.get('numero_ciclos'),
                'diametro_exterior': datos_entrada_muelle.get('diametro_exterior'),
                'diametro_medio': datos_entrada_muelle.get('diametro_medio'),
                'diametro_interior': datos_entrada_muelle.get('diametro_interior'),
                'longitud_sujecion': datos_entrada_muelle.get('longitud_sujecion'),
                'Radio_sujecion': datos_entrada_muelle.get('Radio_sujecion'),
                'angulo_inicial': datos_entrada_muelle.get('angulo_inicial'),
                'angulo_final': datos_entrada_muelle.get('angulo_final'),
                'numero_espiras': datos_entrada_muelle.get('numero_espiras'),
                'pitch': datos_entrada_muelle.get('pitch')
            }
            material_obj = Material(nombre_material=datos_entrada_muelle['material'])
            muelle = MuelleTorsion(material=material_obj, wire_diameter=float(request.POST.get('diametro_hilo', 0)))
            muelle.configure_spring(
                diametro_medio=datos_entrada_muelle.get('diametro_medio'),
                numero_espiras=datos_entrada_muelle.get('numero_espiras'),
                pitch=datos_entrada_muelle.get('pitch'),
                angulo_libre=datos_entrada_muelle.get('angulo_libre'),
                radious_leg_fija=datos_entrada_muelle.get('longitud_sujecion'),
                radious_leg_movil=datos_entrada_muelle.get('Radio_sujecion')
            )
            muelle.add_position(datos_entrada_muelle.get('angulo_inicial'))
            muelle.add_position(datos_entrada_muelle.get('angulo_final'))

            def build_curve(graph_method_name, data_method_name):
                """Genera una curva si la clase implementa los métodos requeridos."""
                if not hasattr(muelle, graph_method_name):
                    print(f"MuelleTorsion no implementa {graph_method_name}()")
                    return None
                if not hasattr(muelle, data_method_name):
                    print(f"MuelleTorsion no implementa {data_method_name}()")
                    return None
                try:
                    curva_imagen_b64 = getattr(muelle, graph_method_name)()
                    return {
                        'imagen': curva_imagen_b64,
                        'datos': getattr(muelle, data_method_name)()
                    }
                except Exception as graph_error:
                    print(f"Error generando {graph_method_name}: {graph_error}")
                    return None

            # Generar curva de esfuerzos usando método del objeto MuelleTorsion
            curva_esfuerzo_vs_position = None
            curva_esfuerzo_vs_position = build_curve(
                'get_forces_vs_position_graph',
                'get_data_positions',
            )

            # Generar curva de esfuerzos vs recorrido
            curva_esfuerzo_vs_travel = None
            curva_esfuerzo_vs_travel = build_curve(
                'get_forces_vs_travel_graph',
                'get_data_travels',
            )

            #Generar curva de diametros vs posición
            curva_diametros_vs_posicion = None
            curva_diametros_vs_posicion = build_curve(
                'get_diameter_vs_position_graph',
                'get_data_positions',
            )

            # Generar diagrama de Goodman usando método del objeto MuelleLineal
            goodman_data = None
            try:
                # Si el usuario envió longitudes, pasar esas; si no, el método usará valores por defecto
                goodman_data = muelle.create_goodman_diagram()
            except Exception:
                goodman_data = None
            resultado = muelle.get_spring_properties()

            resultado['curva_esfuerzos'] = curva_esfuerzo_vs_position
            resultado['curva_recorrido'] = curva_esfuerzo_vs_travel
            resultado['curva_diametros'] = curva_diametros_vs_posicion
            resultado['diagrama_goodman'] = goodman_data
            for key, value in resultado.items():
                print(f"{key}: {value}")
        except Exception as e:
            print(f"Error en cálculo de muelle de torsión: {e}")
            tb = traceback.format_exc()
            resultado = {'error': f'Error en los cálculos: {str(e)}', 'traceback': tb}
    # Esta vista se puede implementar de manera similar a las otras, adaptando el formulario y los cálculos para muelles de torsión
    return render(request, 'muelles/calculadora_torsion.html', {
        'materiales': get_available_materials(),
        'resultado': resultado
    })
