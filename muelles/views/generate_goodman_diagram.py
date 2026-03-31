from muelles.lineal.goodman import GoodmanAnalyzer, GoodmanData
import matplotlib.pyplot as plt
import numpy as np
import io
import base64


def generate_goodman_diagram(muelle, longitud_inicial, longitud_final, shot_peening=False,numero_ciclos=1e6):
    """Genera el diagrama de Goodman para el muelle"""
    try:
        # Calcular tensiones máxima y mínima
        deformacion_max = muelle.longitud_libre - longitud_final
        deformacion_min = muelle.longitud_libre - longitud_inicial
        
        carga_max = muelle.constante_muelle * deformacion_max if deformacion_max > 0 else 0
        carga_min = muelle.constante_muelle * deformacion_min if deformacion_min > 0 else 0
        
        # Tensión de cortante usando fórmula de Wahl
        tension_max = (8 * carga_max * muelle.diametro_medio * muelle.factor_wahl) / (np.pi * muelle.diametro_hilo**3) if carga_max > 0 else 0
        tension_min = (8 * carga_min * muelle.diametro_medio * muelle.factor_wahl) / (np.pi * muelle.diametro_hilo**3) if carga_min > 0 else 0
        
        # Crear análisis de Goodman
        goodman_data = GoodmanData(
            material=muelle.material,
            diameter=muelle.diametro_hilo,
            carga="torsion",  # Para muelles helicoidales es carga de torsión
            numero_ciclos=numero_ciclos
        )
        
        analyzer = GoodmanAnalyzer(goodman_data, shot_peening=shot_peening)
        
        # Generar diagrama
        fig = analyzer.plot_diagram(tension_max, tension_min, show_plot=False)
        
        # Guardar diagrama en base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        goodman_imagen = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        # Obtener resumen del análisis
        analisis = analyzer.get_analysis_summary(tension_max, tension_min)
        
        return {
            'imagen': goodman_imagen,
            'analisis': analisis,
            'tensiones': {
                'tension_max': round(tension_max, 2),
                'tension_min': round(tension_min, 2),
                'carga_max': round(carga_max, 2),
                'carga_min': round(carga_min, 2)
            }
        }
    except Exception as e:
        print(f"Error generando diagrama de Goodman: {e}")
        return None
