from numpy import sqrt, pi
from typing import List, Optional
import traceback
import io
import base64
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
from .constants import WAHL_FACTOR_CONSTANTS, TIPOS_FINAL_MUELLE_TRACCION
from .goodman import Goodman, GoodmanData, GoodmanAnalyzer
from ..pymodels.material import Material
from .lineal import MuelleLineal, TENSION
from pint import Quantity
from muelles.pymodels.units import ureg
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

matplotlib.use('Agg')


class MuelleTraccion(MuelleLineal):
    tipo_final: str = TIPOS_FINAL_MUELLE_TRACCION[1]
    longitud_hilo: Optional[Quantity] = 0.0 * ureg.mm
    numero_espiras: Optional[float] = None
    fuerza_inicial: Optional[Quantity] = 0.0 * ureg.N
    tension_inicial: Optional[Quantity] = 0.0 * ureg.MPa

    @field_validator("longitud_hilo", mode="before")
    @classmethod
    def validate_longitud_hilo(cls, value):
        if isinstance(value, str):
            try:
                return ureg(value)
            except Exception as e:
                raise ValueError(f"Error al convertir longitud_hilo a Quantity: {e}")
        elif isinstance(value, (int, float)):
            return value * ureg.mm
        elif isinstance(value, Quantity):
            return value
        else:
            raise ValueError("longitud_hilo debe ser una cadena, un número o una Quantity")
    
    @field_validator("fuerza_inicial", mode="before")
    @classmethod
    def validate_fuerza_inicial(cls, value):
        if isinstance(value, str):
            try:
                return ureg(value)
            except Exception as e:
                raise ValueError(f"Error al convertir fuerza_inicial a Quantity: {e}")
        elif isinstance(value, (int, float)):
            return value * ureg.N
        elif isinstance(value, Quantity):
            return value
        else:
            raise ValueError("fuerza_inicial debe ser una cadena, un número o una Quantity")
    
    @field_validator("tension_inicial", mode="before")
    @classmethod
    def validate_tension_inicial(cls, value):
        if isinstance(value, str):
            try:
                return ureg(value)
            except Exception as e:
                raise ValueError(f"Error al convertir tension_inicial a Quantity: {e}")
        elif isinstance(value, (int, float)):
            return value * ureg.MPa
        elif isinstance(value, Quantity):
            return value
        else:
            raise ValueError("tension_inicial debe ser una cadena, un número o una Quantity")

    def __init__(self, material, diametro_hilo: float, **data):
        super().__init__(material, diametro_hilo, **data)
        self.numero_ciclos = int(1e6)
        self.shot_peening = False
        self.tension_inicial = float(data.get("tension_inicial", 0.0))
        self.fuerza_inicial = float(data.get("fuerza_inicial", 0.0))

    def set_material(self, material: str, diametro_hilo: float):
        super().set_material(material, diametro_hilo)
        if not isinstance(material, Material):
            raise ValueError("El material debe ser una instancia de la clase Material")
        if diametro_hilo is None:
            raise ValueError("""Debe proporcionar el diámetro del
                    hilo para establecer el material""")

    def validate_diameters(
            self,
            diametro_exterior: float = None,
            diametro_interior: float = None,
            diametro_medio: float = None,
            ):
        if sum(1 for var in [diametro_exterior,
                             diametro_interior,
                             diametro_medio] if var is not None) != 1:
            raise ValueError("""Debe proporcionar exactamente uno de los tres
                             diámetros: exterior, interior, medio""")

        if diametro_medio is not None:
            self.set_diametro_medio(diametro_medio)
        else: 
            diametro_medio = self.calcular_diametro_medio(diametro_exterior,
                                                          diametro_interior)
            self.set_diametro_medio(diametro_medio)

        self.calcular_factor_de_wahl()

    def calculate_spring_properties(self,
                                    numero_espiras: float = None,
                                    pitch: float = None,
                                    longitud_libre: float = None):
        self.set_numero_espiras(numero_espiras=numero_espiras,
                                pitch=pitch,
                                longitud_libre=longitud_libre)
        self.calcular_constante_muelle()
        self.calcular_longitud_hilo()

    def calculate_positions_table(self, step: List):
        for posicion in step:
            self.add_posicion_carga(posicion)

    def set_diametro_medio(self, diametro_medio: float):
        if diametro_medio <= 0:
            raise ValueError("El diámetro medio debe ser positivo")
        self.diametro_medio = diametro_medio

    def calcular_diametro_medio(self, diametro_exterior=None, diametro_interior=None):
        """Calcula el diámetro medio del muelle"""
        none_variables = sum(1 for var in [diametro_exterior,
                                           diametro_interior] if var is not None)
        if none_variables != 1:
            self.diametro_medio = (diametro_exterior + diametro_interior) / 2
            self.diametro_hilo = diametro_exterior - self.diametro_medio
            return self.diametro_medio
        
        if self.diametro_hilo <= 0 or self.diametro_hilo is None:
            raise ValueError("""El diámetro del hilo debe ser un valor positivo
                             y no nulo para calcular el diámetro medio""")
        if not diametro_exterior:
            return (diametro_interior + self.diametro_hilo)
        if not diametro_interior:
            diametro_medio = diametro_exterior - self.diametro_hilo
        if diametro_medio <= 0:
            raise ValueError("""El diámetro medio calculado debe ser un valor
                             positivo""")
        self.set_diametro_medio(diametro_medio)
        return self.diametro_medio

    def calcular_indice_muelle(self):
        self.indice_muelle = self.diametro_medio / self.diametro_hilo
        return self.indice_muelle

    def calculo_espiras_utiles(self):
        if self.tipo_final == "abierto":
            self.numero_espiras_utiles = self.numero_espiras - 0.5
        elif self.tipo_final == "cerrado":
            self.numero_espiras_utiles = self.numero_espiras - 1
        elif self.tipo_final == "semi-cerrado":
            self.numero_espiras_utiles = self.numero_espiras - 0.75
        else:
            self.numero_espiras_utiles = self.numero_espiras - 1

        if self.numero_espiras_utiles <= 0:
            raise ValueError("El número de espiras útiles debe ser mayor que cero")
        return self.numero_espiras_utiles

    def set_numero_espiras(self,
                           numero_espiras=None,
                           pitch=None,
                           longitud_libre=None):
        numero_variables = sum(1 for var in [numero_espiras,
                                             pitch,
                                             longitud_libre] if var is not None)
        if numero_variables != 2:
            raise ValueError("""Debe proporcionar exactamente dos variables:
                            numero_espiras, pitch, longitud_libre""")

        if pitch is None:
            self.pitch = longitud_libre / numero_espiras
            self.numero_espiras = numero_espiras
            self.longitud_libre = longitud_libre
        elif numero_espiras is None:
            self.numero_espiras = longitud_libre / pitch
            self.pitch = pitch
            self.longitud_libre = longitud_libre
        elif longitud_libre is None:
            self.longitud_libre = numero_espiras * pitch
            self.numero_espiras = numero_espiras
            self.pitch = pitch

        self.calculo_espiras_utiles()

    def set_numero_ciclos(self, numero_ciclos):
        self.numero_ciclos = int(numero_ciclos)
        return self.numero_ciclos

    def set_tension_inicial(self, tension_inicial: float):
        if tension_inicial < 0:
            raise ValueError("La tensión inicial no puede ser negativa")
        self.tension_inicial = tension_inicial
        return self.tension_inicial

    def calculo_pitch(self, longitud: float):
        self.pitch = longitud / self.numero_espiras
        return self.pitch

    def calcular_longitud_hilo(self):
        print (f"Calculando longitud del hilo con diametro_medio={self.diametro_medio}, pitch={self.pitch}, numero_espiras={self.numero_espiras}")
        print(f"Fórmula utilizada: longitud_hilo = {self.numero_espiras * sqrt((pi * self.diametro_medio) ** 2 + self.pitch**2)}")
        self.longitud_hilo = self.numero_espiras * sqrt((pi * self.diametro_medio) ** 2 + self.pitch**2)
        return self.longitud_hilo

    def calcular_factor_de_wahl(self):
        if self.indice_muelle == 0:
            self.calcular_indice_muelle()

        self.factor_wahl = (4 * self.indice_muelle - 1) / (4 * self.indice_muelle - 4) + 0.615 / self.indice_muelle

        if self.factor_wahl < WAHL_FACTOR_CONSTANTS["red"][1]:
            self.factor_wahl_category = "red"
        elif WAHL_FACTOR_CONSTANTS["orange"][0] <= self.factor_wahl < WAHL_FACTOR_CONSTANTS["orange"][1]:
            self.factor_wahl_category = "orange"
        else:
            self.factor_wahl_category = "green"

        return self.factor_wahl

    def calcular_constante_muelle(self):
        try:
            self.constante_muelle = (
                self.material.shear_modulus * self.diametro_hilo**4
            ) / (8 * self.diametro_medio**3 * self.numero_espiras_utiles)
        except Exception as e:
            raise ValueError(f"No se puede calcular la constante del muelle: {e}")
        return self.constante_muelle

    def calcular_paso(self):
        return self.longitud_libre / self.numero_espiras

    # def calcula_carga_en_posicion(self, longitud: float):
    #     if self.constante_muelle == 0:
    #         self.calcular_constante_muelle()

    #     if longitud < self.longitud_libre.magnitude:
    #         raise ValueError("En un muelle de tracción la longitud de cálculo no puede ser menor que la longitud libre")

    #     extension = longitud - self.longitud_libre
    #     carga = self.tension_inicial + self.constante_muelle * extension
    #     return carga

    def calacula_tension_en_posicion(self, longitud: float):
        try:
            carga = self.calcula_carga_en_posicion(longitud, TENSION)
            tension = (8 * self.diametro_medio * carga) / (3.1416 * self.diametro_hilo**3) * self.factor_wahl
            return tension
        except ValueError as e:
            raise ValueError(f"Error al calcular la tensión en posición {longitud}: {e}")

    def calcular_diametro_externo_en_posicion(self, longitud: float):
        self.longitud_posicion = longitud
        extension = self.longitud_posicion - self.longitud_libre
        diametro_externo = (
            self.diametro_medio
            + self.diametro_hilo
            - self.diametro_medio * self.material.poisson_coef * extension / self.longitud_libre
        )
        return diametro_externo

    def add_posicion_carga(self, longitud: float):
        try:
            self.longitud_posicion = longitud
            carga = self.calcula_carga_en_posicion(longitud,TENSION)
            tension = self.calacula_tension_en_posicion(self.longitud_posicion)
            diametro_externo = self.calcular_diametro_externo_en_posicion(self.longitud_posicion)
        except ValueError as e:
            raise ValueError(f"Error al agregar posición de carga en longitud {longitud}: {e}")

        self.posiciones.add_posicion_carga(
            posicion=self.longitud_posicion,
            recorrido=self.longitud_posicion - self.longitud_libre,
            carga=carga,
            tension=tension,
            diametro_externo=diametro_externo,
            diametro_interno=max(diametro_externo - 2 * self.diametro_hilo, 0)
        )

    def vaciar_tablas(self):
        self.posiciones.clear_table()

    def get_spring_data(self):
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
            "factor_wahl": self.factor_wahl,
            "factor_wahl_category": self.factor_wahl_category,
            "longitud_hilo": self.longitud_hilo,
            "numero_ciclos": self.numero_ciclos,
            "shot_peening": self.shot_peening,
            "indice_muelle": self.indice_muelle,
            "pitch": self.pitch,
            "tension_inicial": self.tension_inicial,
        }

    def get_data_positions(self):
        return self.posiciones.posiciones

    def get_data_travels(self):
        return self.posiciones.posiciones

    def get_forces_vs_position_graph(self, show=False):
        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_n_float(value):
            return float(value.to('N').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.posiciones.posiciones
        if not tabla_posiciones:
            raise ValueError('No hay posiciones para graficar')

        posiciones = [_to_mm_float(pc.posicion) for pc in tabla_posiciones]
        cargas = [_to_n_float(pc.carga) for pc in tabla_posiciones]

        plot = plt.figure()
        plt.plot(posiciones, cargas, marker='o')
        plt.title('Curva de Carga vs Posicion')
        plt.xlabel('Posicion (mm)')
        plt.ylabel('Carga (N)')
        plt.grid(True)
        if show:
            plt.show()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close(plot)
        return plot_data

    def get_forces_vs_travel_graph(self, show=False):
        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_n_float(value):
            return float(value.to('N').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.posiciones.posiciones
        if not tabla_posiciones:
            raise ValueError('No hay posiciones para graficar')

        recorridos = [_to_mm_float(pc.recorrido) for pc in tabla_posiciones]
        cargas = [_to_n_float(pc.carga) for pc in tabla_posiciones]

        plot = plt.figure()
        plt.plot(recorridos, cargas, marker='o')
        plt.title('Curva de Carga vs Recorrido')
        plt.xlabel('Recorrido (mm)')
        plt.ylabel('Carga (N)')
        plt.grid(True)
        if show:
            plt.show()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close(plot)

        return plot_data

    def get_diameter_graph(self):
        tabla_posiciones = self.posiciones.posiciones
        posiciones = [pc.posicion for pc in tabla_posiciones]
        diametros = [pc.diametro_externo for pc in tabla_posiciones]

        plot = plt.figure()
        plt.plot(posiciones, diametros, marker="o", color="orange")
        plt.title("Diámetro Externo vs Posición")
        plt.xlabel("Posición (mm)")
        plt.ylabel("Diámetro Externo (mm)")
        plt.grid(True)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close()

        return plot_data

    def get_diameter_vs_position_graph(self):
        tabla_posiciones = self.posiciones.posiciones
        posiciones = [pc.posicion for pc in tabla_posiciones]
        diametros = [pc.diametro_externo for pc in tabla_posiciones]

        diametro_exterior = self.diametro_medio + self.diametro_hilo
        diametro_interior = max(self.diametro_medio - self.diametro_hilo, 0)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [2, 1]})

        ax1.plot(posiciones, diametros, marker="o", color="orange")
        ax1.set_title("Diametro Externo vs Posicion")
        ax1.set_xlabel("Posicion (mm)")
        ax1.set_ylabel("Diametro Externo (mm)")
        ax1.grid(True)

        ax2.set_aspect("equal")
        ax2.axis("off")

        radio_exterior = diametro_exterior / 2.0
        radio_interior = diametro_interior / 2.0
        max_radio = max(radio_exterior, radio_interior, 1.0)
        padding = max_radio * 0.25

        ax2.add_patch(Circle((0, 0), radio_exterior, fill=False, lw=2, color="tab:green"))
        if radio_interior > 0:
            ax2.add_patch(Circle((0, 0), radio_interior, fill=False, lw=2, color="tab:blue"))

        ax2.plot([-radio_exterior, radio_exterior], [0, 0], color="tab:green", lw=1)
        ax2.text(0, -padding, f"Dext = {diametro_exterior:.2f} mm", ha="center", va="top", fontsize=8)

        if radio_interior > 0:
            ax2.plot([0, 0], [-radio_interior, radio_interior], color="tab:blue", lw=1)
            ax2.text(0, padding, f"Dint = {diametro_interior:.2f} mm", ha="center", va="bottom", fontsize=8)

        ax2.set_xlim(-max_radio - padding, max_radio + padding)
        ax2.set_ylim(-max_radio - padding, max_radio + padding)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plot_data = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close(fig)

        return plot_data

    def create_goodman_diagram(self):
        try:
            sigma_max = self.get_tension_max()
            sigma_min = self.get_tension_min()

            goodman_data = GoodmanData(
                material=self.material,
                diameter=self.diametro_hilo,
                carga="torsion",
                cycles=int(self.numero_ciclos),
            )

            analyzer = GoodmanAnalyzer(goodman_data, shot_peening=self.shot_peening)
            fig = analyzer.plot_diagram(sigma_max, sigma_min, show_plot=False)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            buf.seek(0)
            image_b64 = base64.b64encode(buf.getvalue()).decode()
            plt.close(fig)

            analisis = analyzer.get_analysis_summary(sigma_max, sigma_min)

            return {
                "imagen": image_b64,
                "analisis": analisis,
                "tensiones": {
                    "tension_max": round(sigma_max, 2),
                    "tension_min": round(sigma_min, 2),
                    "carga_max": round(self.get_carga_max(), 2),
                    "carga_min": round(self.get_carga_min(), 2),
                },
            }
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error creando diagrama de Goodman en MuelleTraccion: {e}\n{tb}")
            return {"error": str(e), "traceback": tb}

    def get_goodman_graph(self):
        goodman_diagram = Goodman(
            material=self.material,
            diameter=self.diametro_hilo,
            carga="torsion",
            numero_ciclos=self.numero_ciclos,
            shot_peening=self.shot_peening,
        )
        sigma_min = min(self.posiciones.posiciones, key=lambda x: x.tension).tension
        sigma_max = max(self.posiciones.posiciones, key=lambda x: x.tension).tension
        goodman_fig = goodman_diagram.get_goodman_graph(sigma_max, sigma_min)
        return goodman_fig

    def get_tension_max(self):
        return max(self.posiciones.posiciones, key=lambda x: x.tension).tension

    def get_tension_min(self):
        return min(self.posiciones.posiciones, key=lambda x: x.tension).tension

    def get_carga_max(self):
        return max(self.posiciones.posiciones, key=lambda x: x.carga).carga

    def get_carga_min(self):
        return min(self.posiciones.posiciones, key=lambda x: x.carga).carga

    def plot_diagramm(self):
        goodman_diagram = Goodman(
            material=self.material,
            diameter=self.diametro_hilo,
            carga="torsion",
            numero_ciclos=self.numero_ciclos,
            shot_peening=self.shot_peening,
        )
        sigma_min = self.get_tension_min()
        sigma_max = self.get_tension_max()
        goodman_diagram.plot_diagramm(sigma_max, sigma_min)

    def get_goodman_analysis_summary(self):
        goodman_diagram = Goodman(
            material=self.material,
            diameter=self.diametro_hilo,
            carga="torsion",
            numero_ciclos=self.numero_ciclos,
            shot_peening=self.shot_peening,
        )
        sigma_min = self.get_tension_min()
        sigma_max = self.get_tension_max()
        return goodman_diagram.get_analysis_summary(sigma_max, sigma_min)
