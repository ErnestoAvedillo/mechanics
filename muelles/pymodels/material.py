from pydantic import BaseModel, field_validator, model_validator, ConfigDict, ValidationInfo
import pandas as pd
import os
from typing import List, Optional
from pint import Quantity
from .units import ureg

def get_materials_dataframe() -> pd.DataFrame:
    """Obtiene el DataFrame completo de materiales desde materials.csv"""
    # Obtener la ruta del archivo CSV
    current_dir = os.path.dirname(os.path.abspath(__file__))
    material_dir = os.path.join(os.path.dirname(current_dir), 'material')
    csv_path = os.path.join(material_dir, 'materials.csv')
    
    try:
        df = pd.read_csv(csv_path)
        # Limpiar espacios en blanco en todas las columnas de texto
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"Error al leer materials.csv: {e}")
        return pd.DataFrame()

def get_available_materials() -> List[str]:
    """Obtiene la lista de materiales disponibles desde materials.csv"""
    df = get_materials_dataframe()
    if not df.empty:
        return df['denomination'].tolist()
    return []


class Material(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    nombre_material: str
    young_modulus: Optional[Quantity] = None
    shear_modulus: Optional[Quantity] = None
    elastic_limit_factor: Optional[Quantity] = None    
    poisson_coef: Optional[Quantity] = None
    RMa_file: Optional[str] = None

    @field_validator('nombre_material')
    @classmethod
    def validate_material_name(cls, v):
        """Valida que el nombre del material esté en la lista de materiales disponibles"""
        available_materials = get_available_materials()
        if v not in available_materials:
            raise ValueError(f'Material "{v}" no válido. Materiales disponibles: {", ".join(available_materials)}')
        return v
    
    @field_validator('young_modulus',
                     'shear_modulus',
                     'elastic_limit_factor',
                     'poisson_coef', mode='before')
    @classmethod
    def validate_positive_quantities(cls, v, info: ValidationInfo):
        """Valida que las cantidades sean positivas y tengan unidades correctas"""
        if v is not None:
            try:
                quantity = ureg(v).to('MPa') if info.field_name in ['young_modulus', 'shear_modulus'] else ureg(v)
                if quantity.magnitude <= 0:
                    raise ValueError(f'{info.field_name} debe ser un valor positivo con unidades válidas Pascal (Pa) para young_modulus y shear_modulus, sin unidades para elastic_limit_factor, y adimensional para poisson_coef.')
                return quantity
            except Exception as e:
                raise ValueError(f'Error al validar {info.field_name}: {e}')
        return v
    
    @model_validator(mode='after')
    def assign_material_properties(self):
        """Asigna automáticamente las propiedades del material basándose en materials.csv"""
        if self.nombre_material:
            df = get_materials_dataframe()
            if not df.empty:
                # Limpiar los nombres de las columnas (eliminar espacios)
                df.columns = df.columns.str.strip()
                
                # Buscar la fila correspondiente al material
                material_row = df[df['denomination'] == self.nombre_material]
                
                if not material_row.empty:
                    row = material_row.iloc[0]
                    
                    # Asignar propiedades automáticamente (solo si no están ya establecidas y el valor no está vacío)
                    if self.young_modulus is None and 'young_modulus' in df.columns:
                        val = row.get('young_modulus')
                        if pd.notna(val) and str(val).strip() != '':
                            self.young_modulus = float(val) * ureg.MPa
                    
                    if self.shear_modulus is None and 'shear_modulus' in df.columns:
                        val = row.get('shear_modulus')
                        if pd.notna(val) and str(val).strip() != '':
                            self.shear_modulus = float(val) * ureg.MPa
                    
                    if self.elastic_limit_factor is None and 'factor_limite_elástico' in df.columns:
                        val = row.get('factor_limite_elástico')
                        if pd.notna(val) and str(val).strip() != '':
                            self.elastic_limit_factor = float(val) * ureg.dimensionless
                    
                    if self.poisson_coef is None and 'poisson_coef' in df.columns:
                        val = row.get('poisson_coef')
                        if pd.notna(val) and str(val).strip() != '':
                            self.poisson_coef = float(val) * ureg.dimensionless
                    
                    if self.RMa_file is None and 'RMa_file' in df.columns:
                        val = row.get('RMa_file')
                        if pd.notna(val) and str(val).strip() != '':
                            self.RMa_file = str(val).strip()
        
        return self
    