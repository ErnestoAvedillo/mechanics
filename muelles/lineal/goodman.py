import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pydantic import BaseModel, computed_field, field_validator
from ..pymodels.wire_characteristics import WireCharacteristics
from ..pymodels.material import Material
from muelles.regresiones.factor_f.usar_modelo_factor_f import ModeloFactorF
from math import log10
import io
import base64
from pint import Quantity
from ..pymodels.units import ureg

class GoodmanData(BaseModel):
    """Modelo de datos para el diagrama de Goodman - solo validación y datos"""
    material: Material
    diameter: float
    carga: str = "axial"
    cycles: int = 1e6  # Número de ciclos para el análisis de fatiga, por defecto 1 millón

    @field_validator('diameter', mode='before')
    @classmethod
    def validate_diameter(cls, v):
        if isinstance(v, Quantity):
            return float(v.to('mm').magnitude)
        if isinstance(v, (int, float)):
            return float(v)
        return float(ureg(v).to('mm').magnitude)

    @computed_field
    @property
    def wire_characteristics(self) -> WireCharacteristics:
        """Características del hilo calculadas automáticamente"""
        return WireCharacteristics(material=self.material, diametro_hilo=self.diameter)


class GoodmanAnalyzer:
    """Servicio para análisis de Goodman - lógica de negocio y cálculos"""
    
    def __init__(self, data: GoodmanData, shot_peening: bool = False):
        self.data = data
        self.wire_char = data.wire_characteristics
        self.shot_peening = shot_peening
        self._calculate_factors()
    
    def _calculate_factors(self):
        """Calcula todos los factores de resistencia según Shigley"""
        # 1. Resistencia última a la tracción (RMa_min) del material
        self.Sut = self.wire_char.RMa_min

        # 2. Resistencia máxima a cortante (Ssu) - aproximada como 0.75 * RMa_min para aceros
        self.Ssu = 0.67 * self.Sut

        # 4. Límite de fatiga al cortante no corregido (Sse')
        # Para muelles de acero, a menudo se usa Sse' ≈ 0.5 * Sut para vida infinita
        self.Sse_prime = self.wire_char.material.elastic_limit_factor * self.Sut

        # Shigley Diseño de ingenieria mecánica, 9na edición, sección 6-8, pág. 274
        # Cálculo de los factores de corrección para resistencia a la fatiga, Factores de Marín
        # factor de superficie
        if self.shot_peening:
            # El shot peening mejora la resistencia a la fatiga, por lo que se puede usar un factor de corrección de 1 
            self.k_a = 1 
        else:
            self.k_a = 4.51 * self.Sut**(-0.265)
        
        # factor de tamaño
        if self.data.carga in ["torsion", "flexion"]:
            self.k_b = 0.879 * (self.data.diameter / 25.4)**(-0.107)
        else:
            self.k_b = 1
        
        # factor de carga
        if self.data.carga == "flexion":
            self.k_c = 1.0
        elif self.data.carga == "axial":
            self.k_c = 0.85
        else:
            self.k_c = 0.59
        
        # factor de temperatura
        self.k_d = 1.0
        # factor de confiabilidad
        self.k_e = 1.0
        # factor de fatiga
        modelo_factor_f = ModeloFactorF()
        self.factor_f = modelo_factor_f.predecir(self.Ssu)
        if self.data.cycles <= 1e3:
            self.Ssf_prime = self.Sut * self.data.cycles**(log10(self.factor_f)/3)  # Aproximación para bajos ciclos
        else:
            if self.data.cycles > 1e6:
                cycles = 1e6  # Limitar a 1 millón de ciclos para la predicción
            else:
                cycles = self.data.cycles
            a = (self.factor_f  * self.Sut)**2 /  self.Sse_prime
            b = -log10(self.factor_f  * self.Sut / self.Sse_prime) / 3
            self.Ssf_prime = a * cycles**b
        # Límite de fatiga corregido (Sse)
        # self.Sse = self.k_a * self.k_b * self.k_c * self.k_d * self.k_e *self.Sse_prime
        self.Sse = self.Sse_prime
        # Límite de fatiga al cortante corregido (Ssf)
        self.Ssf = self.k_a * self.k_b * self.k_c * self.k_d * self.k_e * self.Ssf_prime

    @staticmethod
    def _to_mpa_float(value) -> float:
        if isinstance(value, Quantity):
            return float(value.to('MPa').magnitude)
        return float(value)

    def plot_diagram(self, sigma_max: float, sigma_min: float, show_plot: bool = True):
        """
        Grafica el diagrama de Goodman con el punto de operación marcado
        
        Args:
            sigma_max: Tensión máxima del ciclo de carga
            sigma_min: Tensión mínima del ciclo de carga
            show_plot: Si mostrar el gráfico inmediatamente
        
        Returns:
            Figure de matplotlib para mayor flexibilidad
        """
        sigma_max = self._to_mpa_float(sigma_max)
        sigma_min = self._to_mpa_float(sigma_min)

        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Coordenadas del diagrama de Goodman
        V1 = (self.Sse - self.Ssf) / (self.Ssu - self.Ssf) * self.Ssu
        Sv1 = self.Ssu - (self.Ssu - V1) * (self.Ssu + self.Ssf) / self.Ssu
        
        # Líneas del diagrama
        goodman_x = [0, V1, self.Sse, V1, 0]
        goodman_y = [self.Ssf, self.Sse, self.Sse, Sv1, -self.Ssf]

        ax.plot(goodman_x, goodman_y, 'b-', linewidth=2, label='Envolvente de Goodman')
        ax.fill(goodman_x, goodman_y, alpha=0.3, color='lightblue', label='Región segura')
        
        # Punto de operación
        mean_tension = (sigma_max + sigma_min) / 2
        amplitude = (sigma_max - sigma_min) / 2
        
        ax.plot([mean_tension, mean_tension], [sigma_min, sigma_max], 
                'ro-', linewidth=2, markersize=8, label='Punto de operación')
        ax.plot(mean_tension, mean_tension, 'go', markersize=10, label=f'σₘ={mean_tension:.1f}, σₐ={amplitude:.1f}')
        
        # Configuración del gráfico
        ax.set_title(f'Diagrama de Goodman - Material: {self.data.material.nombre_material}')
        ax.set_xlabel('Mean Tension σₘ (MPa)')
        ax.set_ylabel('Alternating Tension σₐ (MPa)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Añadir información técnica
        info_text = f"""Factors de Goodman:
        Nr de cycles: {self.data.cycles:.1e}
        Correction factors
        kₐ = {self.k_a:.3f}
        k_b = {self.k_b:.3f}
        k_c = {self.k_c:.3}
        Sut = {self.Ssu:.1f} MPa
        Se = {self.Sse:.1f} MPa
        Sf = {self.Ssf:.1f} MPa
        Security factor (Sf/Sa): {self.calculate_safety_factor(sigma_max, sigma_min):.2f}"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                verticalalignment='top', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        if show_plot:
            plt.show()

        return fig

    def get_diagram_image(self, sigma_max: float, sigma_min: float):
        """Retorna la imagen del diagrama de Goodman en base64"""
        fig = self.plot_diagram(sigma_max, sigma_min, show_plot=False)
        # Guardar diagrama en base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        goodman_imagen = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return goodman_imagen
    
    def calculate_safety_factor(self, sigma_max: float, sigma_min: float) -> float:
        """
        Calcula el factor de seguridad del punto de operación. Shigley 6.12, pág. 275
        
        Args:
            sigma_max: Tensión máxima del ciclo
            sigma_min: Tensión mínima del ciclo
            
        Returns:
            Factor de seguridad
        """
        sigma_max = self._to_mpa_float(sigma_max)
        sigma_min = self._to_mpa_float(sigma_min)

        mean_tension = (sigma_max + sigma_min) / 2
        amplitude = (sigma_max - sigma_min) / 2
        
        # Ecuación de Goodman modificada
        if amplitude == 0:
            return float('inf')
        
        factor_seguridad = 1 / (amplitude/self.Sse + mean_tension/self.Ssu)
        return factor_seguridad
    
    def get_analysis_summary(self, sigma_max: float, sigma_min: float) -> dict:
        """
        Retorna un resumen completo del análisis de Goodman
        
        Returns:
            Diccionario con todos los parámetros calculados
        """
        sigma_max = self._to_mpa_float(sigma_max)
        sigma_min = self._to_mpa_float(sigma_min)

        return {
            'material': self.data.material.nombre_material,
            'diameter': self.data.diameter,
            'load_type': self.data.carga,
            'factors': {
                'k_a': self.k_a,
                'k_b': self.k_b, 
                'k_c': self.k_c,
                'k_d': self.k_d,
                'k_e': self.k_e
            },
            'strengths': {
                'Se_MPa': self.Sse,
                'Sf_MPa': self.Ssf,
                'RMa_min_MPa': self.wire_char.RMa_min,
                'RMa_max_MPa': self.wire_char.RMa_max
            },
            'operation_point': {
                'sigma_max_MPa': sigma_max,
                'sigma_min_MPa': sigma_min,
                'mean_tension_MPa': (sigma_max + sigma_min) / 2,
                'amplitude_MPa': (sigma_max - sigma_min) / 2
            },
            'safety_factor': self.calculate_safety_factor(sigma_max, sigma_min)
        }


# Retrocompatibilidad: mantener la interfaz original para no romper código existente
class Goodman(GoodmanAnalyzer):
    """Clase de retrocompatibilidad - usa la nueva arquitectura internamente"""
    
    def __init__(self, material: Material, diameter: float, carga: str = "axial", numero_ciclos: int = 1e6, shot_peening: bool = False):
        data = GoodmanData(material=material, diameter=diameter, carga=carga, cycles=numero_ciclos)
        super().__init__(data, shot_peening=shot_peening)
    
    def plot_goodman_graph(self, sigma_max: float, sigma_min: float):
        """Método original para retrocompatibilidad"""
        return self.plot_diagram(sigma_max, sigma_min, show_plot=True)
    
    def get_goodman_graph(self, sigma_max: float, sigma_min: float):
        """Método original para retrocompatibilidad"""
        return self.plot_diagram(sigma_max, sigma_min, show_plot=False)
