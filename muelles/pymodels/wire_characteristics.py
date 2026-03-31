from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from .material import Material
import os
from pandas import read_csv
from pint import Quantity
from .units import ureg


def _diameter_to_mm_value(diametro_hilo) -> float:
    """Convierte el diámetro del hilo a un escalar en milímetros."""
    if isinstance(diametro_hilo, Quantity):
        return float(diametro_hilo.to('mm').magnitude)
    if isinstance(diametro_hilo, (int, float)):
        return float(diametro_hilo)
    return float(ureg.Quantity(diametro_hilo).to('mm').magnitude)

def get_wire_tolerance(diametro_hilo: float) -> float:
    """Obtiene la tolerancia del diámetro del hilo según el diámetro"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    material_dir = os.path.join(os.path.dirname(current_dir), 'material')
    file = os.path.join(material_dir, "DIAMETRO_TOLERANCIAS.csv")
    
    try:
        diametro_hilo_mm = _diameter_to_mm_value(diametro_hilo)
        pd = read_csv(file)
        if pd.iloc[0]['diameter'] > diametro_hilo_mm:
            return pd.iloc[0]['tolerance']
        if diametro_hilo_mm > pd.iloc[len(pd) - 1]['diameter']:
            return pd.iloc[len(pd) - 1]['tolerance']
        last_row = pd.iloc[0]
        for index, row in pd.iterrows():
            if row['diameter'] >= diametro_hilo_mm:
                return last_row['tolerance']
            last_row = row
        return pd.iloc[len(pd) - 1]['tolerance']
    except Exception as e:
        print(f"Error al obtener tolerancia: {e}")
        return 0.1  # Valor por defecto

def get_RMa_range(material, diametro_hilo: float) -> tuple:
    """Obtiene el rango de RMa para un material y diámetro de hilo dado"""
    try:
        diametro_hilo_mm = _diameter_to_mm_value(diametro_hilo)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        material_dir = os.path.join(os.path.dirname(current_dir), 'material')
        file = os.path.join(material_dir, material.RMa_file)
        
        if not os.path.exists(file):
            print(f"Archivo RMa no encontrado: {file}")
            return (1000.0, 1200.0)  # Valores por defecto
            
        df = read_csv(file)
        df.columns = df.columns.str.strip()  # Limpiar espacios en nombres de columnas
        
        # Si el diámetro es menor que el primer valor, usar el primero
        if diametro_hilo_mm <= df.iloc[0]['diameter']:
            return (float(df.iloc[0]['RMa_min']), float(df.iloc[0]['RMa_max']))
        
        # Si el diámetro es mayor que el último valor, usar el último
        if diametro_hilo_mm >= df.iloc[len(df) - 1]['diameter']:
            return (float(df.iloc[len(df) - 1]['RMa_min']), float(df.iloc[len(df) - 1]['RMa_max']))
        
        # Buscar entre qué valores está y retornar el valor inferior
        prev_row = df.iloc[0]
        for index, row in df.iterrows():
            if row['diameter'] >= diametro_hilo_mm:
                return (float(row['RMa_min']), float(row['RMa_max']))
            prev_row = row

        return (1000.0, 1200.0)  # Valores por defecto
        
    except Exception as e:
        print(f"Error al obtener rango RMa: {e}")
        return (1000.0, 1200.0)  # Valores por defecto

class WireCharacteristics(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    material: Material
    diametro_hilo: Quantity
    tolerancia_diametro: Quantity = None
    RMa_min: Quantity = None    
    RMa_max: Quantity = None

    @field_validator('diametro_hilo', 'tolerancia_diametro', mode='before')
    @classmethod
    def validate_diametro_hilo(cls, v):
        """Valida que el diámetro del hilo sea positivo"""
        if v is None:
            return v
        try:
            if isinstance(v, Quantity):
                quantity = v.to('mm')
            else: 
                quantity = (v * ureg.mm)
            if quantity.magnitude <= 0:
                raise ValueError("El diámetro del hilo debe ser positivo")
            return quantity
        except Exception as e:
            raise ValueError(f"El diámetro del hilo debe ser positivo: {e}")

    @field_validator('RMa_min', 'RMa_max', mode='before')
    @classmethod
    def validate_RMa(cls, v):
        """Valida que RMa_min y RMa_max sean positivos"""
        if v is not None:
            try:
                quantity = ureg(v).to('MPa')
                if quantity.magnitude <= 0:
                    raise ValueError("RMa_min y RMa_max deben ser valores positivos con unidades válidas MPa.")
                return quantity
            except Exception as e:
                raise ValueError(f"Error al validar RMa: {e}")
        return v
    
    def __str__(self):
        return (f"Material: {self.material.nombre_material}, "
                f"Diámetro del Hilo: {self.diametro_hilo} mm, "
                f"Tolerancia del Diámetro: {self.tolerancia_diametro} mm, "
                f"RMa Min: {self.RMa_min} MPa, "
                f"RMa Max: {self.RMa_max} MPa")

    @model_validator(mode='after')
    def assign_wire_characteristics(self):
        """Asigna automáticamente las características del hilo basándose en el material y diámetro"""
        if self.diametro_hilo is not None:
            object.__setattr__(
                self,
                'tolerancia_diametro',
                get_wire_tolerance(self.diametro_hilo),
            )
        
        if self.material and self.diametro_hilo and (self.RMa_min is None or self.RMa_max is None):
            rma_min, rma_max = get_RMa_range(self.material, self.diametro_hilo)
            object.__setattr__(self, 'RMa_min', rma_min)
            object.__setattr__(self, 'RMa_max', rma_max)
        
        return self
    
    def set_material(self, material:str, diametro_hilo:float):
        """Establece el material del muelle"""
        if not isinstance(material, Material):
            raise ValueError("El material debe ser una instancia de la clase Material")
        if diametro_hilo is None:
            raise ValueError("Debe proporcionar el diámetro del hilo para establecer el material")
        self.material = material
        self.diametro_hilo = diametro_hilo
        self.tolerancia_diametro = get_wire_tolerance(diametro_hilo)
        self.RMa_min, self.RMa_max = get_RMa_range(material, diametro_hilo)

        