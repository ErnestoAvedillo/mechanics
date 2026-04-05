from .constants import WAHL_FACTOR_CONSTANTS, TIPOS_FINAL_MUELLE_COMPRESION
from ..pymodels.wire_characteristics import WireCharacteristics
from ..pymodels.material import Material
from ..pymodels.posiciones import PosicionesTableLineal
from typing import Optional
from pint import Quantity
from ..pymodels.units import ureg
from pydantic import field_validator, ConfigDict
import numpy as np
"""Clase para el cálculo de un muelle lineal"""
COMPRESSION = 1
TENSION = -1

class MuelleLineal(WireCharacteristics):
    # Campos adicionales de MuelleLineal
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
    diametro_medio: Quantity = 0.0 * ureg.mm  # en mm
    diametro_exterior: Quantity = 0.0 * ureg.mm  # en mm
    diametro_interior: Quantity = 0.0 * ureg.mm   # en mm
    longitud_libre: Quantity = 0.0 * ureg.mm  # en mm
    numero_espiras_utiles: float = 0.0
    pitch: Quantity = 0.0 * ureg.mm  # en mm
    shot_peening: bool = False
    revestimiento: Optional[str] = None
    indice_muelle: float = 0.0
    posiciones: PosicionesTableLineal = PosicionesTableLineal()
    constante_muelle: Quantity = 0.0 * ureg.N / ureg.mm  # en N/mm
    factor_wahl: float = 0.0  # factor de Wahl
    factor_wahl_category: Optional[str] = None  # categoría del factor de Wahl
    factor_wahl_eval: Optional[float] = None  # factor de Wahl evaluadoSS
    numero_ciclos: int = 1e6  # Número de ciclos para análisis de fatiga, por defecto 1 millón
    longitud_posicion: Optional[Quantity] = 0.0 * ureg.mm  # Longitud en la que se aplica la carga para análisis de fatiga
    carga_posicion: Optional[Quantity] = 0.0 * ureg.N  # Carga en la longitud de posición para análisis de fatiga
    tension_posicion: Optional[Quantity] = 0.0 * ureg.megapascal  # Tension para la carga para análisis de fatiga

    @field_validator('longitud_libre',
                     'longitud_posicion',
                     'diametro_exterior',
                     'diametro_interior',
                     'diametro_medio',
                     'pitch',
                     mode='before')
    @classmethod
    def validate_dimensions(cls, v):
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
    
    @field_validator('constante_muelle', mode='before')
    @classmethod
    def validate_constant_spring(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('N/mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.N / ureg.mm
                else:
                    quantity = ureg(v).to('N/mm')
                if quantity.magnitude < 0:
                    raise ValueError(f'{quantity} debe ser un valor positivo con unidades válidas.')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar cantidad: {e}')
        return quantity

    @field_validator('carga_posicion', mode='before')
    @classmethod
    def validate_carga_posicion(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('N')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.N
                else:
                    quantity = ureg(v).to('N')
                if quantity.magnitude < 0:
                    raise ValueError(f'{quantity} debe ser un valor positivo con unidades válidas.')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar cantidad: {e}')
        return quantity
    
    @field_validator('tension_posicion', mode='before') 
    @classmethod
    def validate_tension_posicion(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('MPa')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.megapascal
                else:
                    quantity = ureg(v).to('MPa')
                if quantity.magnitude < 0:
                    raise ValueError(f'{quantity} debe ser un valor positivo con unidades válidas.')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar cantidad: {e}')
        return quantity

    def __init__(self, material:Material, diametro_hilo: float, **data):
        """inicializo las variables del muelle a 0"""
        # Inicializar con valores por defecto

        data.update({
            'material': material,
            'diametro_hilo': diametro_hilo,
            'posiciones': PosicionesTableLineal()
        })
        super().__init__(**data)
        self.numero_ciclos = 1e6  # Valor por defecto de 1 millón de ciclos para análisis de fatiga
        self.shot_peening = False  # Valor por defecto sin shot peening
    
    def set_material(self, material:str, diametro_hilo:float):
        """Primera parte: Establece el material del muelle"""
        super().set_material(material, diametro_hilo)
        if not isinstance(material, Material):
            raise ValueError("El material debe ser una instancia de la clase Material")
        if diametro_hilo is None:
            raise ValueError("Debe proporcionar el diámetro del hilo para establecer el material")

    def validate_diameters(self, diametro_medio=None, diametro_exterior=None, diametro_interior=None):
        """Segunda parte: Valida y establece los diámetros del muelle"""
        parametres_provided = sum(1 for var in [diametro_exterior, diametro_interior, diametro_medio] if var is not None)
        if parametres_provided != 1:
            raise ValueError("""Debe proporcionar exactamente una de las siguientes variables:
                             diametro_exterior, diametro_interior, diametro_medio""")
        if diametro_exterior is not None:
            self.diametro_exterior = diametro_exterior
            self.diametro_medio = self.diametro_exterior - self.diametro_hilo
            self.diametro_interior = self.diametro_exterior - 2 * self.diametro_hilo
        elif diametro_interior is not None:
            self.diametro_interior = diametro_interior
            self.diametro_medio = self.diametro_interior + self.diametro_hilo
            self.diametro_exterior = self.diametro_interior + 2 * self.diametro_hilo
        elif diametro_medio is not None:
            self.diametro_medio = diametro_medio
            self.diametro_exterior = self.diametro_medio + self.diametro_hilo
            self.diametro_interior = self.diametro_medio - self.diametro_hilo
        self.calcular_factor_de_wahl()

    def calcular_indice_muelle(self):
        """Calcula el índice del muelle"""
        self.indice_muelle = self.diametro_medio / self.diametro_hilo
        return self.indice_muelle
    
    def set_numero_espiras_utiles(self, numero_espiras_utiles=None, pitch=None, longitud_libre=None):
        """Establece el número de espiras del muelle"""
        numero_variables = sum(1 for var in [numero_espiras_utiles, pitch, longitud_libre] if var is not None) 
        if numero_variables != 2:
            raise ValueError("Debe proporcionar exactamente dos de las tres variables: numero_espiras_utiles, pitch, longitud_libre")
        if not pitch:
            self.pitch = longitud_libre / numero_espiras_utiles
            self.longitud_libre = longitud_libre
        elif not numero_espiras_utiles:
            self.numero_espiras_utiles = longitud_libre / pitch
            self.pitch = pitch
            self.longitud_libre = longitud_libre
        elif not longitud_libre:
            self.longitud_libre = numero_espiras_utiles * pitch
            self.pitch = pitch
    
    def set_numero_ciclos(self, numero_ciclos):
        """Establece el número de ciclos para el análisis de fatiga"""
        self.numero_ciclos = numero_ciclos
        return self.numero_ciclos

    def calculo_pitch(self, longitud:float):
        """Calcula el pitch del muelle"""
        self.longitud_libre = longitud
        self.pitch = longitud / self.numero_espiras_utiles
        return self.pitch

    def calcular_factor_de_wahl(self):
        """Calcula el factor de Wahl"""
        if self.indice_muelle == 0:
            self.calcular_indice_muelle()
        self.factor_wahl = (4 * self.indice_muelle - 1) / (4 * self.indice_muelle - 4) + 0.615 / self.indice_muelle
        """Evalúa el factor de Wahl y lo clasifica en categorías"""
        if self.factor_wahl < WAHL_FACTOR_CONSTANTS['red'][1]:
            self.factor_wahl_category = 'red'
        elif WAHL_FACTOR_CONSTANTS['orange'][0] <= self.factor_wahl < WAHL_FACTOR_CONSTANTS['orange'][1]:
            self.factor_wahl_category = 'orange'
        else:
            self.factor_wahl_category = 'green'
        return self.factor_wahl, self.factor_wahl_category

    def calcular_constante_muelle(self):
        """Calcula la constante del muelle (N/mm)"""
        try:
            self.constante_muelle = (self.material.shear_modulus * np.power(self.diametro_hilo,4)) / (8 * np.power(self.diametro_medio,3) * self.numero_espiras_utiles)
        except ValueError:
            raise ValueError("No se puede calcular la constante del muelle sin el diámetro medio")
        return self.constante_muelle

    def calcula_carga_en_posicion(self, longitud:float, spring_class=COMPRESSION):
        """Calcula la carga en una posición dada usando la constante del muelle"""
        if self.constante_muelle == 0:
            self.calcular_constante_muelle()
        self.longitud_posicion = longitud
        self.carga_posicion = spring_class * self.constante_muelle * (self.longitud_libre - self.longitud_posicion)
        self.calcula_tension_en_posicion()
        return self.carga_posicion

    def calcula_tension_en_posicion(self):
        """Calcula la tensión en el hilo del muelle en una posición prdefinida dada"""
        try:
            tension = (8 * self.diametro_medio * self.carga_posicion) / (3.1416 * self.diametro_hilo**3) * self.factor_wahl
            return tension
        except ValueError as e:
            raise ValueError(f"Error al calcular la tensión en posición {self.longitud_posicion}: {e}")

