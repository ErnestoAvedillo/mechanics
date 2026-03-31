"""Cálculo de muelles de torsión."""
from math import pi
import io
import base64
import numpy as np
from math import sqrt, atan
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
from muelles.pymodels.material import Material
from muelles.pymodels.wire_characteristics import WireCharacteristics
from typing import Optional
from muelles.pymodels.posiciones import PosicionesTableAngular
from pint import Quantity
from muelles.pymodels.units import ureg
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


def _mag(v):
    """Extract the magnitude from a Quantity, or return the value as-is."""
    return v.magnitude if isinstance(v, Quantity) else v


class MuelleTorsion(WireCharacteristics):
    model_config = ConfigDict(arbitrary_types_allowed=True,
                              validate_assignment=True)
    diametro_medio: Quantity = 0.0 * ureg.mm
    diametro_interior: Quantity = 0.0 * ureg.mm
    diametro_exterior: Quantity = 0.0 * ureg.mm
    angulo_libre: Quantity = 0.0 * ureg.degree
    angulo_tangencias: Quantity = 0.0 * ureg.degree
    angle_travel: Quantity = 0.0 * ureg.degree
    angle_position: Quantity = 0.0 * ureg.degree
    torque_position: Quantity = 0.0 * ureg.N * ureg.mm
    tension_position: Quantity = 0.0 * ureg.MPa
    pitch: Quantity = 0.0 * ureg.mm
    shot_peening: bool = False
    # Número de ciclos para análisis de fatiga, por defecto 1 millón
    numero_ciclos: int = 1e6  
    numero_espiras_utiles: float = 0.0
    numero_espiras: int = 0
    ancho_muelle: Quantity = 0.0 * ureg.mm  # en mm
    radious_leg_fija: Quantity = 0.0 * ureg.mm  # en mm
    long_leg_fija: Quantity = 0.0 * ureg.mm  # en mm
    radious_leg_movil: Quantity = 0.0 * ureg.mm  # en mm
    long_leg_movil: Quantity = 0.0 * ureg.mm  # en mm
    indice_muelle: float = 0.0  # factor_wahl: float = 0.0  # factor de Wahl
    factor_wahl_category: Optional[str] = None  # categoría del factor de Wahl
    factor_wahl_eval: Optional[float] = None  # factor de Wahl evaluado
    factor_wahl: float = 0.0  # factor de Wahl
    longitud_hilo_total: Quantity = 0.0 * ureg.mm  # en mm
    longitud_hilo_cuerpo: Quantity = 0.0 * ureg.mm  # en mm
    constante_muelle: Quantity = 0.0 * ureg.N * ureg.mm / ureg.rad  # en Nmm/rad
    momento_resistente: Quantity = 0.0 * ureg.mm * ureg.mm * ureg.mm * ureg.mm  # en Nmm
    # Lista de posiciones para análisis de fatiga
    positions: PosicionesTableAngular = PosicionesTableAngular()

    @field_validator('diametro_medio',
                     'diametro_exterior',
                     'diametro_interior',
                     'pitch',
                     'ancho_muelle',
                     'radious_leg_fija',
                     'long_leg_fija',
                     'radious_leg_movil',
                     'long_leg_movil',
                     'longitud_hilo_total',
                     'longitud_hilo_cuerpo',
                     mode='before')
    @classmethod
    def validate_positive_quantities(cls, v):
        """Valida que las cantidades sean positivas y tengan unidades correctas"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.mm
                else:
                    quantity = ureg(v).to('mm')
                if quantity.magnitude < 0:
                    raise ValueError(f'{quantity} debe ser un valor positivo con unidades válidas.')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar cantidad: {e}')
        return quantity

    @field_validator('angulo_libre', 'angulo_tangencias', 'angle_position', 'angle_travel', mode='before')
    @classmethod
    def validate_positive_angles(cls, v):
        """Valida que los ángulos sean positivos y tengan unidades correctas"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('degree')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.degree
                else:
                    quantity = ureg(v).to('degree')
                if quantity.magnitude < 0:
                    quantity =  360 * ureg.degree + quantity
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar ángulo: {e}')
        return quantity
    
    @field_validator('constante_muelle',mode='before')
    @classmethod
    def validate_positive_spring_constant(cls, v):
        """Valida que la constante del muelle sea positiva"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('N*mm/rad')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg('N*mm/rad')
                else:
                    quantity = ureg(v).to('N*mm/rad')
                if quantity.magnitude <= 0:
                    raise ValueError(f'{v} debe ser un valor positivo')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar constante del muelle: {e}')
        return quantity

    @field_validator('momento_resistente', mode='before')
    @classmethod
    def validate_positive_sptring_constant(cls,v):
        """Valida el momento resistente"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('mm**4')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg('mm**4')
                else:
                    quantity = ureg(v).to('mm**4')
                if quantity.magnitude <= 0:
                    raise ValueError(f'{v} debe ser un valor positivo')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar momento resistente: {e}')
        return quantity
    
    @field_validator('torque_position', mode='before')
    @classmethod
    def validate_torque_position(cls, v):
        """Valida la posición de torque"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('N*mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg('N*mm')
                else:
                    quantity = ureg(v).to('N*mm')
                if quantity.magnitude < 0:
                    raise ValueError(f'{v} debe ser un valor positivo')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar posición de torque: {e}')
        return quantity
    
    @field_validator('tension_position', mode='before')
    @classmethod
    def validate_tension_position(cls, v):
        """Valida la posición de tensión"""
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('MPa')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg('MPa')
                else:
                    quantity = ureg(v).to('MPa')
                if quantity.magnitude < 0:
                    raise ValueError(f'{v} debe ser un valor positivo')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar posición de tensión: {e}')
        return quantity

    def __init__(self, material: Material, wire_diameter: float, **data):
        data.update({
            'material': material,
            'diametro_hilo': wire_diameter,
        })
        super().__init__(**data)
        self.numero_ciclos = 1e6  # Valor por defecto de 1 millón de ciclos
        self.shot_peening = False  # Valor por defecto sin shot peening
        self.numero_espiras_utiles = 0.0
        self.numero_espiras = 0
        self.indice_muelle = 0.0  # factor_wahl: float = 0.0  # factor de Wahl
        self.factor_wahl_category = None  # categoría del factor de Wahl
        self.factor_wahl_eval = None  # factor de Wahl evaluado
        self.factor_wahl = 0.0  # factor de Wahl
        # Lista de posiciones para análisis de fatiga
        self.positions = PosicionesTableAngular()
    
    def configure_spring(self,
                         diametro_medio: float,
                         numero_espiras: int,
                         pitch: float,
                         angulo_libre: float,
                         radious_leg_fija: float,
                         radious_leg_movil: float):
        """Configura el muelle de torsión con los parámetros proporcionados"""
        self.set_diametro_medio(diametro_medio)
        self.set_numero_espiras(numero_espiras)
        self.set_pitch(pitch)
        self.set_angulo_libre(angulo_libre)
        self.set_radious_leg_fija(radious_leg_fija)
        self.set_radious_leg_movil(radious_leg_movil)
        return self.calculate_spring_properties()

    def calculate_spring_properties(self):
        """Calcula todas las propiedades del muelle de torsión basándose en los parámetros proporcionados"""
        self.set_angulo_tangencias(self.angulo_libre, self.radious_leg_fija, self.radious_leg_movil)
        self.set_ancho_muelle(self.numero_espiras, self.pitch, self.angulo_libre)
        self.set_longitud_hilo(self.numero_espiras, self.pitch, self.angulo_tangencias, self.radious_leg_fija, self.radious_leg_movil)
        self.calcular_indice_muelle()
        self.calcular_factor_de_wahl()
        self.calculate_length_legs(self.radious_leg_fija, self.radious_leg_movil)
        self.set_momento_resistente()
        self.calcula_constante_muelle()
        return self.get_spring_properties()

    def set_material(self, material: str, diametro_hilo: float):
        """Establece el material del muelle de torsión"""
        super().set_material(material, diametro_hilo)
        if not isinstance(material, Material):
            raise ValueError("""El material debe ser una instancia de la clase
                             Material""")
        if diametro_hilo is None:
            raise ValueError("""Debe proporcionar el diámetro del hilo para
                            establecer el material""")

    def set_diametro_medio(self, diametro_medio):
        """Establece el diámetro medio del muelle de torsión"""
        if _mag(diametro_medio) <= 0:
            raise ValueError("El diámetro medio debe ser un valor positivo")
        self.diametro_medio = diametro_medio
        self.diametro_interior = self.diametro_medio - self.diametro_hilo
        self.diametro_exterior = self.diametro_medio + self.diametro_hilo
        return

    def set_numero_espiras(self, numero_espiras):
        """Establece el número de espiras del muelle de torsión"""
        if numero_espiras <= 0:
            raise ValueError("El número de espiras debe ser un valor positivo")
        self.numero_espiras = numero_espiras
        return self.numero_espiras
    
    def set_pitch(self, pitch):
        """Establece el pitch del muelle de torsión"""
        self.pitch = pitch
        if self.pitch <= self.diametro_hilo:
            raise ValueError("El pitch debe ser un valor positivo")
        return self.pitch
    
    def set_angulo_libre(self, angulo_libre):
        """Establece el ángulo libre del muelle de torsión"""
        if angulo_libre < 0:
            angulo_libre = 360 + angulo_libre
        self.angulo_libre = angulo_libre
        return self.angulo_libre

    def set_radious_leg_fija(self, radious_leg_fija):
        """Establece el radio de la pata fija del muelle de torsión"""
        self.radious_leg_fija = radious_leg_fija
        if self.radious_leg_fija < self.diametro_medio / 2:
            raise ValueError("El radio de la pata fija debe ser al menos la mitad del diámetro medio")
        return self.radious_leg_fija

    def set_radious_leg_movil(self, radious_leg_movil):
        """Establece el radio de la pata móvil del muelle de torsión"""
        self.radious_leg_movil = radious_leg_movil
        if self.radious_leg_movil < self.diametro_medio / 2:
            raise ValueError("El radio de la pata móvil debe ser al menos la mitad del diámetro medio")
        return self.radious_leg_movil

    def calcular_indice_muelle(self):
        """Calcula el índice del muelle de torsión"""
        self.indice_muelle = self.diametro_medio / self.diametro_hilo
        return self.indice_muelle

    def calcular_factor_de_wahl(self):
        """Calcula el factor de Wahl para muelles de torsión"""
        if self.indice_muelle is None:
            self.calcular_indice_muelle()

        self.factor_wahl = ((4*self.indice_muelle**2 - self.indice_muelle - 1)
                            /
                            (4 * self.indice_muelle * (self.indice_muelle - 1))
                            )
        if self.indice_muelle < 4:
            self.factor_wahl_category = 'Bajo'
            self.factor_wahl_eval = 1 + 0.5 / self.indice_muelle
        elif 4 <= self.indice_muelle < 8:
            self.factor_wahl_category = 'Medio'
            self.factor_wahl_eval = 1 + 0.75 / self.indice_muelle
        else:
            self.factor_wahl_category = 'Alto'
            self.factor_wahl_eval = 1 + 1.0 / self.indice_muelle

        return self.factor_wahl_eval

    def set_ancho_muelle(self, numero_espiras, pitch, angulo_libre):
        """Establece el ancho del muelle de torsión"""
        if numero_espiras is None or pitch is None or angulo_libre is None:
            raise ValueError("""Debe proporcionar número de espiras útiles,
                             pitch y ángulo libre para establecer el ancho del
                             muelle""")
        self.angulo_libre = angulo_libre
        self.pitch = pitch
        self.ancho_muelle = (self.numero_espiras + self.angulo_libre / 2 / pi) * self.pitch
        self.numero_espiras_utiles = (self.numero_espiras +
                                      self.angulo_libre / 2 / pi)

        return self.ancho_muelle

    def set_longitud_hilo(self,
                          numero_espiras: int,
                          pitch: float,
                          angulo_tangencias: float,
                          radious_leg_fija: float,
                          radious_leg_movil: float):
        """Calcula la longitud del hilo del muelle de torsión"""
        parameters_provided = [numero_espiras,
                               pitch,
                               angulo_tangencias,
                               radious_leg_fija,
                               radious_leg_movil]
        if sum(1 for var in parameters_provided if var is None) > 0:
            raise ValueError("""Debe proporcionar número de espiras útiles,
                             pitch, ángulo libre, y radios de las patas para
                             calcular la longitud del hilo""")
        if _mag(self.diametro_medio) <= 0:
            raise ValueError("""El diámetro medio debe ser un valor positivo
                             para calcular la longitud del hilo""")
        self.numero_espiras = numero_espiras
        self.pitch = pitch
        self.angulo_tangencias = angulo_tangencias
        self.radious_leg_fija = radious_leg_fija
        self.radious_leg_movil = radious_leg_movil
        longitud_una_vuelta = np.sqrt((pi * self.diametro_medio) ** 2 +
                                   (self.pitch / (2 * pi)) ** 2) 
        self.longitud_hilo_cuerpo = ((self.numero_espiras + self.angulo_tangencias / 2 / pi) *
                                     longitud_una_vuelta)
        self.calculate_length_legs(self.radious_leg_fija, self.radious_leg_movil)
        self.longitud_hilo_total = (self.longitud_hilo_cuerpo +
                                    self.long_leg_fija + self.long_leg_movil)
        return self.longitud_hilo_total

    def set_angulo_tangencias(self,
                              angulo_libre,
                              radious_leg_fija,
                              radious_leg_movil):
        """Calcula el ángulo de tangencias del muelle de torsión"""
        parameters_provided = [angulo_libre,
                               radious_leg_fija,
                               radious_leg_movil]
        if sum(1 for var in parameters_provided if var is None) > 0:
            raise ValueError("""Debe proporcionar ángulo libre y radios de las
                             patas para calcular el ángulo de tangencias""")
        self.angulo_libre = angulo_libre
        self.radious_leg_fija = radious_leg_fija
        self.radious_leg_movil = radious_leg_movil
        angulo_cero_equivalente = (2 * pi -
                                   atan(self.radious_leg_fija / self.diametro_medio) -
                                   atan(self.radious_leg_movil / self.diametro_medio))
        if self.angulo_libre + angulo_cero_equivalente > 2 * pi:
            self.angulo_tangencias = angulo_cero_equivalente + self.angulo_libre - 2 * pi
        else:
            self.angulo_tangencias = 2 * pi - angulo_cero_equivalente - self.angulo_libre
        self.numero_espiras_utiles = self.numero_espiras + self.angulo_tangencias / 2 / pi
        return self.angulo_tangencias

    def calculate_length_legs(self,
                              radious_leg_fija=None,
                              radious_leg_movil=None):
        """Calcula la longitud de las patas del muelle de torsión"""
        self.radious_leg_fija = radious_leg_fija
        self.radious_leg_movil = radious_leg_movil
        if self.radious_leg_fija is None or self.radious_leg_fija < self.diametro_medio / 2:
            self.radious_leg_fija = self.diametro_medio / 2
        if self.radious_leg_movil is None or self.radious_leg_movil < self.diametro_medio / 2:
            self.radious_leg_movil = self.diametro_medio / 2
        self.long_leg_fija = np.sqrt(self.diametro_medio**2 / 4 + self.radious_leg_fija**2)
        self.long_leg_movil = np.sqrt(self.diametro_medio**2 / 4 + self.radious_leg_movil**2)
        return self.long_leg_fija, self.long_leg_movil

    def set_numero_ciclos(self, numero_ciclos):
        """Establece el número de ciclos para el análisis de fatiga del muelle de torsión"""
        self.numero_ciclos = numero_ciclos
        return self.numero_ciclos

    def set_shot_peening(self, shot_peening: bool):
        """Establece si el muelle de torsión ha sido tratado con shot peening"""
        self.shot_peening = shot_peening
        return self.shot_peening

    def calcula_constante_muelle(self):
        """Calcula la constante del muelle de torsión"""
        if _mag(self.momento_resistente) <= 0:
            self.set_momento_resistente()
        self.constante_muelle = (self.material.young_modulus *
                                 self.momento_resistente /
                                 self.longitud_hilo_total)
        return self.constante_muelle

    def calcular_torque(self, angulo_giro):
        """Calcula el torque aplicado al muelle de torsión para un ángulo de
        giro dado en grados"""
        if _mag(angulo_giro) <= 0:
            raise ValueError("El ángulo de giro debe ser un valor positivo")
        self.angulo_giro = angulo_giro
        self.torque_position = self.constante_muelle * self.angulo_giro
        return self.torque_position

    def set_momento_resistente(self):
        """Calcula el momento resistente del muelle de torsión para un torque
        máximo dado"""
        self.momento_resistente = pi * np.pow(self.diametro_hilo, 4) / 64
        return self.momento_resistente

    def calcular_tension(self, torque):
        """Calcula la tensión máxima en el muelle de torsión para un torque
        dado"""
        if _mag(torque) <= 0:
            raise ValueError("El torque debe ser un valor positivo para \
            calcular la tensión")
        tension = ((32 * torque * self.factor_wahl) /
                   (pi * np.pow(self.diametro_medio, 3)))
        return tension

    def add_position(self, angle_travel=None, torque=None):
        """Agrega una posición usando un ángulo recorrido o torque para análisis de fatiga"""
        if angle_travel is None and torque is None:
            raise ValueError("Debe proporcionar un ángulo o un torque solo")
        if angle_travel is not None and torque is not None:
            raise ValueError("Debe proporcionar solo un ángulo o un torque")
        if angle_travel is not None and angle_travel <= 0:
            raise ValueError("El ángulo debe ser un valor positivo")
        if torque is not None and torque <= 0:
            raise ValueError("El torque debe ser un valor positivo")
        if self.constante_muelle <= 0:
            self.calcula_constante_muelle()
        if angle_travel is not None:
            self.angle_travel = angle_travel
            self.torque_position = self.constante_muelle * self.angle_travel
            self.tension_position = self.calcular_tension(self.torque_position)
        else:
            self.torque_position = torque
            self.angle_travel = self.torque_position / self.constante_muelle
            self.tension_position = self.calcular_tension(self.angle_travel)
        self.angle_position = self.angulo_libre - self.angle_travel
        nuevo_angulo_tangencias = self.angulo_tangencias + self.angle_travel
        nuevo_diametro_medio = (4 * (self.longitud_hilo_cuerpo ** 2 - self.pitch ** 2) / 
                                (2 * pi * self.numero_espiras + nuevo_angulo_tangencias) ** 2) ** 0.5
        diametro_exterior = nuevo_diametro_medio + self.diametro_hilo
        diametro_interior = nuevo_diametro_medio - self.diametro_hilo
        if not hasattr(self, 'positions'):
            self.positions = PosicionesTableAngular()
        self.positions.add_posicion_carga(self.angle_position,
                                          self.angle_travel,
                                          self.torque_position,
                                          self.tension_position, diametro_exterior, diametro_interior)
        return self.positions

    def clean_positions(self):
        """Limpia la lista de posiciones para análisis de fatiga"""
        self.positions.clear_table()
        
        return self.positions.posiciones

    def get_positions(self):
        """Obtiene la lista de posiciones para análisis de fatiga"""
        return self.positions.posiciones

    def get_data_positions(self):
        """Retorna la tabla de posiciones angulares para curvas por posición."""
        return self.positions.posiciones

    def get_data_travels(self):
        """Retorna la tabla de posiciones angulares para curvas por recorrido."""
        return self.positions.posiciones

    def get_forces_vs_position_graph(self, show=False):
        """Genera la curva de torque vs posición angular."""
        def _to_deg_float(value):
            return float(value.to('degree').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_torque_float(value):
            return float(value.to('N*mm').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.positions.posiciones
        if not tabla_posiciones:
            raise ValueError('No hay posiciones para graficar')

        posiciones = [_to_deg_float(pc.posicion) for pc in tabla_posiciones]
        torques = [_to_torque_float(pc.carga) for pc in tabla_posiciones]

        plot = plt.figure()
        plt.plot(posiciones, torques, marker='o')
        plt.title('Curva de Torque vs Posicion Angular')
        plt.xlabel('Posicion (grados)')
        plt.ylabel('Torque (N*mm)')
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
        """Genera la curva de torque vs recorrido angular."""
        def _to_deg_float(value):
            return float(value.to('degree').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_torque_float(value):
            return float(value.to('N*mm').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.positions.posiciones
        if not tabla_posiciones:
            raise ValueError('No hay posiciones para graficar')

        recorridos = [_to_deg_float(pc.recorrido) for pc in tabla_posiciones]
        torques = [_to_torque_float(pc.carga) for pc in tabla_posiciones]

        plot = plt.figure()
        plt.plot(recorridos, torques, marker='o')
        plt.title('Curva de Torque vs Recorrido Angular')
        plt.xlabel('Recorrido (grados)')
        plt.ylabel('Torque (N*mm)')
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

    def get_diameter_vs_position_graph(self, show=False):
        """Grafica diametro externo vs posicion angular y seccion del muelle."""
        def _to_deg_float(value):
            return float(value.to('degree').magnitude) if isinstance(value, Quantity) else float(value)

        def _to_mm_float(value):
            return float(value.to('mm').magnitude) if isinstance(value, Quantity) else float(value)

        tabla_posiciones = self.positions.posiciones
        if not tabla_posiciones:
            raise ValueError('No hay posiciones para graficar')

        posiciones = [_to_deg_float(pc.posicion) for pc in tabla_posiciones]
        diametros = [_to_mm_float(pc.diametro_externo) for pc in tabla_posiciones]

        diametro_exterior = self.diametro_medio + self.diametro_hilo
        diametro_interior = max(self.diametro_medio - self.diametro_hilo, 0 * ureg.mm)
        diametro_exterior_mm = _to_mm_float(diametro_exterior)
        diametro_interior_mm = _to_mm_float(diametro_interior)

        fig, (ax1, ax2) = plt.subplots(
            1,
            2,
            figsize=(10, 4),
            gridspec_kw={'width_ratios': [2, 1]}
        )

        ax1.plot(posiciones, diametros, marker='o', color='orange')
        ax1.set_title('Diametro Externo vs Posicion Angular')
        ax1.set_xlabel('Posicion (grados)')
        ax1.set_ylabel('Diametro Externo (mm)')
        ax1.grid(True)

        ax2.set_aspect('equal')
        ax2.axis('off')

        radio_exterior = diametro_exterior_mm / 2.0
        radio_interior = diametro_interior_mm / 2.0
        max_radio = max(radio_exterior, radio_interior, 1.0)
        padding = max_radio * 0.25

        ax2.add_patch(Circle((0, 0), radio_exterior, fill=False, lw=2, color='tab:green'))
        if radio_interior > 0:
            ax2.add_patch(Circle((0, 0), radio_interior, fill=False, lw=2, color='tab:blue'))

        ax2.plot([-radio_exterior, radio_exterior], [0, 0], color='tab:green', lw=1)
        ax2.text(0, -padding, f"Dext = {diametro_exterior_mm:.2f} mm", ha='center', va='top', fontsize=8)

        if radio_interior > 0:
            ax2.plot([0, 0], [-radio_interior, radio_interior], color='tab:blue', lw=1)
            ax2.text(0, padding, f"Dint = {diametro_interior_mm:.2f} mm", ha='center', va='bottom', fontsize=8)

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
    
    def get_spring_properties(self)-> dict:
        """Obtiene un diccionario con todas las propiedades del muelle de torsión"""
        return {
            'material': self.material.nombre_material,
            'modulo_young': self.material.young_modulus,
            'diametro_hilo': self.diametro_hilo,
            'diametro_medio': self.diametro_medio,
            'diametro_interior': self.diametro_interior,
            'diametro_exterior': self.diametro_exterior,
            'angulo_libre': self.angulo_libre,  # Convertir a grados para la salida
            'angulo_tangencias': self.angulo_tangencias,  # Convertir a grados para la salida
            'pitch': self.pitch,
            'shot_peening': self.shot_peening,
            'numero_ciclos': self.numero_ciclos,
            'numero_espiras_utiles': self.numero_espiras_utiles,
            'numero_espiras': self.numero_espiras,
            'ancho_muelle': self.ancho_muelle,
            'radious_leg_fija': self.radious_leg_fija,
            'long_leg_fija': self.long_leg_fija,
            'radious_leg_movil': self.radious_leg_movil,
            'long_leg_movil': self.long_leg_movil,
            'indice_muelle': self.indice_muelle,
            'factor_wahl': self.factor_wahl,
            'factor_wahl_category': self.factor_wahl_category,
            'factor_wahl_eval': self.factor_wahl_eval,
            'longitud_hilo_total': self.longitud_hilo_total,
            'longitud_hilo_cuerpo': self.longitud_hilo_cuerpo,
            'constante_muelle': self.constante_muelle,
            'momento_resistente': self.momento_resistente
        }