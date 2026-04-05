from math import pi
from pydantic import field_validator, model_validator, ConfigDict
from .constants import WAHL_FACTOR_CONSTANTS, TIPOS_FINAL_MUELLE_COMPRESION, TIPOS_CONFORMADO
from ..pymodels.wire_characteristics import WireCharacteristics
from ..pymodels.material import Material
from .goodman import Goodman
import traceback
from typing import List, Optional
import os
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
import io
import base64
import numpy as np
from .goodman import GoodmanData, GoodmanAnalyzer
from .lineal import MuelleLineal
from pint import Quantity
from ..pymodels.units import ureg
from ..pymodels.posiciones import PosicionesTableLineal
"""Clase para el cálculo de un muelle de compresión"""


class MuelleCompresion(MuelleLineal):
    # Campos adicionales de MuelleCompresion
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
    tipo_final: str = TIPOS_FINAL_MUELLE_COMPRESION[1]  # por defecto rectificado
    tipo_conformado: str = TIPOS_CONFORMADO[1] # por defecto conformado en frío
    longitud_hilo: Optional[Quantity] = 0.0 * ureg.mm # en mm
    numero_espiras: Optional[float] = None
    longitud_bloqueo: Quantity = 0.0 * ureg.mm  # Longitud con carga máxima en mm
    posiciones: PosicionesTableLineal = PosicionesTableLineal()

    @field_validator('longitud_hilo', "longitud_bloqueo", mode='before')
    @classmethod
    def validate_quantities(cls, value):
        if isinstance(value, str):
            try:
                quantity = ureg(value)
                return quantity.to('mm')
            except Exception as e:
                raise ValueError(f"Error al convertir '{value}' a Quantity: {e}")
        elif isinstance(value, (int, float)):
            return Quantity(value, 'mm')
        elif isinstance(value, Quantity):
            return value.to('mm')
        else:
            raise ValueError(f"Valor no válido para Quantity: {value}")
        
    def __init__(self, material, diametro_hilo: float, **data):
        """inicializo las variables del muelle a 0"""
        # Inicializar con valores por defecto
        super().__init__(material, diametro_hilo, **data)
    
    def set_material(self, material, diametro_hilo):
        return super().set_material(material, diametro_hilo)
    
    def calculate_spring_properties(self,
                                    numero_espiras:float=None,
                                    pitch:float=None,
                                    longitud_libre:float=None):
        """Tercera parte: Calcula todas las propiedades del muelle"""
        parameters_provided = sum(1 for var in [numero_espiras, pitch, longitud_libre] if var is not None)
        if parameters_provided != 2:
            raise ValueError("Debe proporcionar exactamente dos de las siguientes variables: numero_espiras, pitch, longitud_libre")

        if numero_espiras is not None and pitch is not None:
            self.numero_espiras = numero_espiras
            self.pitch = pitch
            self.longitud_libre = self.numero_espiras * self.pitch
        elif numero_espiras is not None and longitud_libre is not None:
            self.numero_espiras = numero_espiras
            self.longitud_libre = longitud_libre
            self.pitch = self.longitud_libre / self.numero_espiras
        elif pitch is not None and longitud_libre is not None:
            self.pitch = pitch
            self.longitud_libre = longitud_libre
            self.numero_espiras = self.longitud_libre / self.pitch
        else:
            raise ValueError("Debe proporcionar exactamente dos de las siguientes variables: numero_espiras, pitch, longitud_libre")

        if self.pitch <= self.diametro_hilo:
            raise ValueError("El pitch debe ser mayor que el diámetro del hilo para evitar interferencias entre espiras.")
        self.calculo_espiras_utiles(numero_espiras=self.numero_espiras)
        self.calcular_factor_de_wahl()
        self.calcular_constante_muelle()
        self.calcular_longitud_bloqueo()
        self.calcular_longitud_hilo()
        self.calcula_carga_en_posicion(self.longitud_bloqueo)
        self.calcular_diametro_externo_en_posicion(self.longitud_bloqueo)
        properties = self.get_spring_data()
        return properties

    def calculo_espiras_utiles(self, numero_espiras=numero_espiras):
        """Calcula el número de espiras útiles del muelle según el tipo de final"""
        self.numero_espiras = numero_espiras
        # Solo se calculan las espiras útiles para muelles de compresión
        # conformados en frio. En conformado en caliente se resta 1.5 veces el diámetro del hilo.
        if self.tipo_conformado == TIPOS_CONFORMADO[1]:  # conformado en frío
            self.numero_espiras_utiles = self.numero_espiras - 2
            if self.tipo_final in [TIPOS_FINAL_MUELLE_COMPRESION[3], TIPOS_FINAL_MUELLE_COMPRESION[4]]:  # no rectificado
                self.numero_espiras_utiles -= 1.5
        else: # conformado en caliente
            self.numero_espiras_utiles = self.numero_espiras - 1.5
        if self.tipo_final in [TIPOS_FINAL_MUELLE_COMPRESION[1], TIPOS_FINAL_MUELLE_COMPRESION[2]]:  # rectificado
            self.numero_espiras_utiles -= 0.3
        else:
            self.numero_espiras_utiles -= 1.1
        return self.numero_espiras_utiles

    def calcular_longitud_hilo(self):
        """Calcula la longitud del hilo del muelle"""
        self.longitud_hilo = self.numero_espiras * np.sqrt((pi * self.diametro_medio)**2 + self.pitch**2)
        return self.longitud_hilo

    def calcular_paso(self):
        """Calcula el paso del muelle"""
        return self.longitud_libre / self.numero_espiras

    def calcular_longitud_bloqueo(self):
        """Calcula la longitud de bloqueo del muelle"""
        self.longitud_bloqueo = self.numero_espiras * self.diametro_hilo
        return self.longitud_bloqueo

    def add_posicion_carga(self, longitud):
        """Agrega una posición de carga a la tabla de posiciones"""
        try:
            if longitud < self.longitud_bloqueo.magnitude:
                raise ValueError("La posición no puede ser menor que la longitud de bloqueo del muelle")
            carga = self.calcula_carga_en_posicion(longitud)
            tension = self.calcula_tension_en_posicion()
            diametro_externo = self.calcular_diametro_externo_en_posicion(longitud)
        except ValueError as e:
            raise ValueError(f"Error al agregar posición de carga en longitud {longitud}: {e}")
        self.posiciones.add_posicion_carga(
            posicion=self.longitud_posicion,
            recorrido=self.longitud_libre - self.longitud_posicion,
            carga=carga,
            tension=tension,
            diametro_externo=diametro_externo,
            diametro_interno=max(diametro_externo - 2 * self.diametro_hilo, 0 * ureg.mm)
        )
    
    def calcular_diametro_externo_en_posicion(self, longitud):
        """Calcula el diámetro externo del muelle"""
        self.longitud_posicion = longitud
        diametro_externo = self.diametro_medio + self.diametro_hilo + \
                           self.diametro_medio * self.material.poisson_coef * \
                           (self.longitud_libre - self.longitud_posicion) / self.longitud_libre
        return diametro_externo

    def vaciar_tablas(self):
        """Vacía las tablas de posiciones, cargas, tensiones y diámetros externos"""
        self.posiciones.clear_table()

    def get_spring_data(self):
        """Retorna un diccionario con los datos principales del muelle"""
        return {
            "material": self.material.nombre_material,
            "young_modulus": self.material.young_modulus,
            "shear_modulus": self.material.shear_modulus,
            "elastic_limit_factor": self.material.elastic_limit_factor,
            "poisson_coef": self.material.poisson_coef,
            "RMa_file": self.material.RMa_file,
            "diametro_hilo": self.diametro_hilo,
            "diametro_medio": self.diametro_medio,
            "longitud_libre": self.longitud_libre,
            "numero_espiras": self.numero_espiras,
            "numero_espiras_utiles": self.numero_espiras_utiles,
            "constante_muelle": self.constante_muelle,
            "indice_muelle": self.indice_muelle,
            "factor_wahl": self.factor_wahl,
            "factor_wahl_category": self.factor_wahl_category,
            "longitud_bloqueo": self.longitud_bloqueo,
            "longitud_hilo": self.longitud_hilo,
            "numero_ciclos": self.numero_ciclos,
            "shot_peening": self.shot_peening    
        }

    def get_data_positions(self):
        """Retorna la tabla de posiciones, cargas, tensiones y diámetros externos"""
        return self.posiciones.posiciones

    def get_data_travels(self):
        """Retorna la tabla de posiciones para la curva de recorrido"""
        return self.posiciones.posiciones

    def get_forces_vs_position_graph(self, show=False):
        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_n_float(value):
            return float(value.to('N').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.posiciones.posiciones
        posiciones = [_to_mm_float(pc.posicion) for pc in tabla_posiciones]
        cargas = [_to_n_float(pc.carga) for pc in tabla_posiciones]
        plot = plt.figure()
        plt.plot(posiciones, cargas, marker='o')
        plt.title('Curva de Carga vs Posición')
        plt.xlabel('Posición (mm)')
        plt.ylabel('Carga (N)')
        plt.grid(True)
        if show:
            plt.show()

        # Save the plot to a BytesIO object
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close()

        return plot_data

    def get_forces_vs_travel_graph(self, show=False):
        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_n_float(value):
            return float(value.to('N').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.posiciones.posiciones
        recorridos = [_to_mm_float(pc.recorrido) for pc in tabla_posiciones]
        cargas = [_to_n_float(pc.carga) for pc in tabla_posiciones]
        plot = plt.figure()
        plt.plot(recorridos, cargas, marker='o')
        plt.title('Curva de Carga vs Recorrido')
        plt.xlabel('Recorrido (mm)')
        plt.ylabel('Carga (N)')
        plt.grid(True)
        # Save the plot to a BytesIO object
        if show:
            plt.show()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close()

        return plot_data

    def get_diameter_graph(self, show=False):
        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.posiciones.posiciones
        posiciones = [_to_mm_float(pc.posicion) for pc in tabla_posiciones]
        diametros = [_to_mm_float(pc.diametro_externo) for pc in tabla_posiciones]
        plot = plt.figure()
        plt.plot(posiciones, diametros, marker='o', color='orange')
        plt.title('Diámetro Externo vs Posición')
        plt.xlabel('Posición (mm)')
        plt.ylabel('Diámetro Externo (mm)')
        plt.grid(True)
        if show:
            plt.show()

        # Save the plot to a BytesIO object
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close()

        return plot_data

    def get_diameter_vs_position_graph(self, show=False):
        """Grafica diametro vs posicion y agrega un esquema con
        circunferencias."""
        def _to_mm_float(value):
            if isinstance(value, Quantity):
                return float(value.to('mm').magnitude)
            return float(value)

        tabla_posiciones = self.posiciones.posiciones
        posiciones = [_to_mm_float(pc.posicion) for pc in tabla_posiciones]
        diametros = [_to_mm_float(pc.diametro_externo) for pc in tabla_posiciones]

        diametro_exterior = self.diametro_medio + self.diametro_hilo
        diametro_interior = max(self.diametro_medio - self.diametro_hilo, 0 * ureg.mm)
        diametro_exterior_mm = _to_mm_float(diametro_exterior)
        diametro_interior_mm = _to_mm_float(diametro_interior)

        fig, (ax1, ax2) = plt.subplots(
            1,
            2,
            figsize=(10, 4),
            gridspec_kw={"width_ratios": [2, 1]}
        )

        ax1.plot(posiciones, diametros, marker='o', color='orange')
        ax1.set_title('Diametro Externo vs Posicion')
        ax1.set_xlabel('Posicion (mm)')
        ax1.set_ylabel('Diametro Externo (mm)')
        ax1.grid(True)

        ax2.set_aspect('equal')
        ax2.axis('off')

        radio_exterior = diametro_exterior_mm / 2.0
        radio_interior = diametro_interior_mm / 2.0
        max_radio = max(radio_exterior, radio_interior, 1.0)
        padding = max_radio * 0.25

        ax2.add_patch(Circle((0, 0),
                             radio_exterior,
                             fill=False, lw=2,
                             color='tab:green'))
        if radio_interior > 0:
            ax2.add_patch(Circle((0, 0),
                                 radio_interior,
                                 fill=False,
                                 lw=2,
                                 color='tab:blue'))

        ax2.plot([-radio_exterior, radio_exterior],
                 [0, 0],
                 color='tab:green',
                 lw=1)
        ax2.text(0,
                 -padding,
                 f"Dext = {diametro_exterior_mm:.2f} mm",
                 ha='center',
                 va='top',
                 fontsize=8)

        if radio_interior > 0:
            ax2.plot([0, 0],
                     [-radio_interior, radio_interior],
                     color='tab:blue',
                     lw=1)
            ax2.text(0,
                     padding,
                     f"Dint = {diametro_interior_mm:.2f} mm",
                     ha='center',
                     va='bottom',
                     fontsize=8)

        ax2.set_xlim(-max_radio - padding, max_radio + padding)
        ax2.set_ylim(-max_radio - padding, max_radio + padding)
        if show:
            plt.show()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close(fig)

        return plot_data

    def create_goodman_diagram(self, show=False):
        """Genera el diagrama de Goodman y devuelve un diccionario con la
        imagen en base64, el análisis y las tensiones calculadas. Si falla,
        devuelve un diccionario con las claves 'error' y 'traceback'."""
        try:
            # Obtener tensiones desde la tabla de posiciones
            sigma_max = self.get_tension_max()
            sigma_min = self.get_tension_min()

            # Preparar datos para Goodman
            goodman_data = GoodmanData(
                material=self.material,
                diameter=self.diametro_hilo,
                carga='torsion',
                cycles=int(self.numero_ciclos)
            )

            analyzer = GoodmanAnalyzer(goodman_data,
                                       shot_peening=self.shot_peening)
            if show:
                analyzer.plot_diagram(sigma_max=sigma_max, sigma_min=sigma_min)
                return
            
            image_b64 = analyzer.get_diagram_image(sigma_max=sigma_max,
                                                   sigma_min=sigma_min)

            analisis = analyzer.get_analysis_summary(sigma_max, sigma_min)

            return {
                'imagen': image_b64,
                'analisis': analisis,
                'tensiones': {
                    'tension_max': round(sigma_max, 2),
                    'tension_min': round(sigma_min, 2),
                    'carga_max': round(self.get_carga_max(), 2),
                    'carga_min': round(self.get_carga_min(), 2)
                }
            }
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error creando diagrama de Goodman en MuelleLineal: {e}\n{tb}")
            return {'error': str(e), 'traceback': tb}

    def get_goodman_graph(self, goodman: Goodman, show=True):
        """Crea el diagrama de Goodman para el muelle"""
        # Placeholder implementation
        # Aquí se implementaría la lógica para crear el diagrama de Goodman
        sigma_min = min(self.posiciones.posiciones,
                        key=lambda x: x.tension).tension
        sigma_max = max(self.posiciones.posiciones,
                        key=lambda x: x.tension).tension
        if show:
            goodman.plot_goodman_graph(sigma_max, sigma_min)
        else:
            goodman_fig = goodman.get_goodman_graph(sigma_max, sigma_min)
        return goodman_fig

    def get_goodman_analysis_summary(self, goodman: Goodman):
        """Retorna un resumen completo del análisis de Goodman"""
        sigma_min = self.get_tension_min()
        sigma_max = self.get_tension_max()
        return goodman.get_analysis_summary(sigma_max, sigma_min)

    def get_tension_max(self):
        """Retorna la tensión máxima del muelle"""
        return max(self.posiciones.posiciones, key=lambda x: x.tension).tension

    def get_tension_min(self):
        """Retorna la tensión mínima del muelle"""
        return min(self.posiciones.posiciones, key=lambda x: x.tension).tension

    def get_carga_max(self):
        """Retorna la carga máxima del muelle"""
        return max(self.posiciones.posiciones, key=lambda x: x.carga).carga

    def get_carga_min(self):
        """Retorna la carga mínima del muelle"""
        return min(self.posiciones.posiciones, key=lambda x: x.carga).carga
