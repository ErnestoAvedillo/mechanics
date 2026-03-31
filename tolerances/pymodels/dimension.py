from pydantic import BaseModel, BeforeValidator, Field
from pint import UnitRegistry, Quantity
from typing import Optional, Any, Annotated
from numpy import random, ndarray

ureg = UnitRegistry()


# Función para convertir cualquier entrada a objeto Pint
def as_quantity(v: Any) -> Quantity:
    if isinstance(v, Quantity):
        return v
    if isinstance(v, (int, float)):
        return v * ureg.mm  # Asume mm por defecto si es número
    if isinstance(v, str):
        return ureg(v)
    return v


# Tipo personalizado para reutilizar
PintQuantity = Annotated[Quantity, BeforeValidator(as_quantity)]


class Dimension(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    nominal: PintQuantity = 0.0 * ureg.mm
    tol_sup: PintQuantity = 0.0 * ureg.mm
    tol_inf: PintQuantity = 0.0 * ureg.mm
    mean: Optional[PintQuantity] = 0.0 * ureg.mm
    sigma: Optional[PintQuantity] = 0.0 * ureg.mm
    vector_samples: Optional[ndarray] = None
    CP: float = 1.0
    
    def __add__(self, other: 'Dimension') -> 'GausianDimensionGenerator':
        """Suma dos dimensiones usando el operador +"""
        if not isinstance(other, Dimension):
            return NotImplemented
        
        # Sumar nominales
        nominal_sum = self.nominal + other.nominal
        
        # Sumar tolerancias
        tol_sup_sum = self.tol_sup + other.tol_sup
        tol_inf_sum = self.tol_inf + other.tol_inf

        
        # Usar el CP del primer elemento
        cp_result = self.CP
        
        # Número de muestras
        num_samples = getattr(self, 'number_samples', 100000)
        
        # Crear nueva dimensión resultado
        result = GausianDimensionGenerator(
            nominal=nominal_sum,
            tol_sup=tol_sup_sum,
            tol_inf=tol_inf_sum,
            CP=cp_result,
            number_samples=num_samples
        )
        
        if self.vector_samples is not None and other.vector_samples is not None:
            result.vector_samples = self.vector_samples + other.vector_samples
            result.mean = result.vector_samples.mean() * ureg.mm
            result.sigma = result.vector_samples.std() * ureg.mm
        
        return result
    
    def __sub__(self, other: 'Dimension') -> 'GausianDimensionGenerator':
        """Resta dos dimensiones usando el operador -"""
        if not isinstance(other, Dimension):
            return NotImplemented
        
        # Restar nominales
        nominal_sub = self.nominal - other.nominal
        
        # Restar tolerancias (la superior e inferior se intercambian)
        tol_sup_sub = self.tol_sup - other.tol_inf
        tol_inf_sub = self.tol_inf - other.tol_sup
        
        cp_result = self.CP
        num_samples = getattr(self, 'number_samples', 100000)
        
        result = GausianDimensionGenerator(
            nominal=nominal_sub,
            tol_sup=tol_sup_sub,
            tol_inf=tol_inf_sub,
            CP=cp_result,
            number_samples=num_samples
        )
        
        # Restar los vectores de muestras
        if self.vector_samples is not None and other.vector_samples is not None:
            result.vector_samples = self.vector_samples - other.vector_samples
            result.mean = result.vector_samples.mean() * ureg.mm
            result.sigma = result.vector_samples.std() * ureg.mm
        
        return result
    
    def __truediv__(self, other):
        """Dividir una diemension por un escalar o float"""
        if isinstance(other, (int, float)):
            # Dividir por un escalar
            nominal_div = self.nominal / other
            tol_sup_div = self.tol_sup / other
            tol_inf_div = self.tol_inf / other
            
            cp_result = self.CP
            num_samples = getattr(self, 'number_samples', 100000)
            
            result = GausianDimensionGenerator(
                nominal=nominal_div,
                tol_sup=tol_sup_div,
                tol_inf=tol_inf_div,
                CP=cp_result,
                number_samples=num_samples
            )
        
            if self.vector_samples is not None:
                result.vector_samples = self.vector_samples / other
                result.mean = result.vector_samples.mean() * ureg.mm
                result.sigma = result.vector_samples.std() * ureg.mm
            
            return result
        
        # Si se intenta dividir por otra dimensión, no es soportado en este contexto
        return NotImplemented


class GausianDimensionGenerator(Dimension):
    number_samples: int = Field(default=100000, validation_alias="NumberSamples")

    # Generar vector de muestras después de la validación del modelo
    def model_post_init(self, __context: Any) -> None:
        self.mean = self.nominal + (self.tol_sup + self.tol_inf) / 2
        self.sigma = (self.tol_sup - self.tol_inf) / 6 / self.CP
        self.vector_samples = random.normal(loc=self.mean.magnitude,
                                     scale=self.sigma.magnitude,
                                     size=self.number_samples)

from scipy.stats import skewnorm
import numpy as np

class SkewedDimensionGenerator(Dimension):
    number_samples: int = 100000
    skewness: float = 0.0  # 0 is normal, positive shifts right, negative shifts left

    def model_post_init(self, __context: Any) -> None:
        # Calculate Mean and Sigma based on tolerances (similar to your Gaussian logic)
        self.mean = self.nominal + (self.tol_sup - self.tol_inf) / 2
        self.sigma = (self.tol_sup - self.tol_inf) / 6 / self.CP
        
        # 'a' is the shape parameter for skewnorm
        # We use scipy.stats.skewnorm.rvs to generate the data
        # Note: loc and scale in skewnorm aren't exactly mean/std, but close for low skew
        samples_raw = skewnorm.rvs(
            a=self.skewness, 
            loc=self.mean.magnitude, 
            scale=self.sigma.magnitude, 
            size=self.number_samples
        )
        
        self.vector_samples = samples_raw 


class DimensionOperator:
    """Clase para realizar operaciones entre dimensiones (Gaussiana y Skewed)."""
    
    @staticmethod
    def add(dim1: Dimension, dim2: Dimension) -> GausianDimensionGenerator:
        """
        Suma dos dimensiones.
        
        Args:
            dim1: Primera dimensión
            dim2: Segunda dimensión
            
        Returns:
            GausianDimensionGenerator: Nueva dimensión con la suma de ambas
        """
        # Sumar nominales
        nominal_sum = dim1.nominal + dim2.nominal
        
        # Sumar tolerancias
        tol_sup_sum = dim1.tol_sup + dim2.tol_sup
        tol_inf_sum = dim1.tol_inf + dim2.tol_inf
        
        # Usar el CP del primer elemento (puede modificarse si es necesario)
        cp_result = dim1.CP
        
        # Número de muestras (usar el del primer elemento)
        num_samples = getattr(dim1, 'number_samples', 100000)
        
        # Crear nueva dimensión resultado
        result = GausianDimensionGenerator(
            nominal=nominal_sum,
            tol_sup=tol_sup_sum,
            tol_inf=tol_inf_sum,
            CP=cp_result,
            number_samples=num_samples
        )
        
        # Sumar los vectores de muestras elemento a elemento
        if dim1.vector_samples is not None and dim2.vector_samples is not None:
            result.vector_samples = dim1.vector_samples + dim2.vector_samples
        
        return result
    
    @staticmethod
    def subtract(dim1: Dimension, dim2: Dimension) -> GausianDimensionGenerator:
        """
        Resta la segunda dimensión de la primera.
        
        Args:
            dim1: Primera dimensión (minuendo)
            dim2: Segunda dimensión (sustraendo)
            
        Returns:
            GausianDimensionGenerator: Nueva dimensión con la resta
        """
        # Restar nominales
        nominal_sub = dim1.nominal - dim2.nominal
        
        # Restar tolerancias (la superior e inferior se intercambian)
        tol_sup_sub = dim1.tol_sup - dim2.tol_inf
        tol_inf_sub = dim1.tol_inf - dim2.tol_sup
        
        cp_result = dim1.CP
        num_samples = getattr(dim1, 'number_samples', 100000)
        
        result = GausianDimensionGenerator(
            nominal=nominal_sub,
            tol_sup=tol_sup_sub,
            tol_inf=tol_inf_sub,
            CP=cp_result,
            number_samples=num_samples
        )
        
        # Restar los vectores de muestras
        if dim1.vector_samples is not None and dim2.vector_samples is not None:
            result.vector_samples = dim1.vector_samples - dim2.vector_samples
        
        return result

