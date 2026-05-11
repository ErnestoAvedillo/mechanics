"""Class dimension with nominal, tolerances, mean, sigma and vector of samples.
The class allows to perform operations between dimensions, such as addition and subtraction, and to calculate the DPMO.
"""
from pydantic import BaseModel, Field
from pint import UnitRegistry
from typing import Optional, Any, Annotated
from numpy import random, ndarray
from scipy.stats import norm, skewnorm
from .convert import PintQuantity


ureg = UnitRegistry()


class Dimension(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    number_samples: int = Field(default=100000,
                                validation_alias="NumberSamples")
    nominal: PintQuantity = 0.0 * ureg.mm
    tol_sup: PintQuantity = 0.0 * ureg.mm
    tol_inf: PintQuantity = 0.0 * ureg.mm
    tol_sup_sum: Optional[PintQuantity] = 0.0 * ureg.mm
    tol_inf_sum: Optional[PintQuantity] = 0.0 * ureg.mm
    mean: Optional[PintQuantity] = 0.0 * ureg.mm
    sigma: Optional[PintQuantity] = 0.0 * ureg.mm
    vector_samples: Optional[ndarray] = None
    number_samples: int = 100000
    dpmo: Optional[float] = 0
    CP: float = 1.0

    def calc_dpmo(self):
        """
        Calcula el DPMO para una distribución normal
        con tolerancias asimétricas.
        """
        p_lower = norm.cdf(self.tol_inf, loc=self.mean, scale=self.sigma)
        p_upper = 1 - norm.cdf(self.tol_supp, loc=self.mean, scale=self.sigma)
        self.dpmo = (p_lower + p_upper) * 1_000_000
        return self.dpmo

    def __add__(self, other: 'Dimension') -> 'Dimension':
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
            tol_sup_sum=tol_sup_sum,
            tol_inf_sum=tol_inf_sum,
            CP=cp_result,
            number_samples=num_samples

        )

        if self.vector_samples is not None and other.vector_samples is not None:
            result.vector_samples = self.vector_samples + other.vector_samples
            result.mean = result.vector_samples.mean() * ureg.mm
            result.sigma = result.vector_samples.std() * ureg.mm

        return result

    def __sub__(self, other: 'Dimension') -> 'Dimension':
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

    def __truediv__(self, other) -> 'Dimension':
        """Resta dos dimensiones usando el operador -"""

        if not isinstance(other, (int, float)):
            return NotImplemented

        # Restar nominales
        nominal_sub = self.nominal / other

        # Restar tolerancias (la superior e inferior se intercambian)
        tol_sup_sub = self.tol_sup / other
        tol_inf_sub = self.tol_inf / other

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
        if self.vector_samples is not None and other is not None:
            result.vector_samples = self.vector_samples / other
            result.mean = result.vector_samples.mean() * ureg.mm
            result.sigma = result.vector_samples.std() * ureg.mm
        return result

    def model_post_init(self, __context: Any) -> None:
        if self.vector_samples is None:
            self.mean = self.nominal + (self.tol_sup + self.tol_inf) / 2
            self.sigma = (self.tol_sup - self.tol_inf) / 6 / self.CP
            self.vector_samples = random.normal(loc=self.mean.magnitude,
                                                scale=self.sigma.magnitude,
                                                size=self.number_samples)
            
    def __str__(self):
        return_str = f"Dimension(nominal={self.nominal}, tol_sup={self.tol_sup},tol_inf={self.tol_inf} \n"
        return_str += f"mean={self.mean}, sigma={self.sigma}, tol_sup_sum={self.tol_sup_sum}, tol_inf_sum={self.tol_inf_sum})\n"
        return_str += f"dpmo={self.dpmo}"
        return return_str

class GausianDimensionGenerator(Dimension):
    number_samples: int = Field(default=100000,
                                validation_alias="NumberSamples")

    # Generar vector de muestras después de la validación del modelo
    def model_post_init(self, __context: Any) -> None:
        self.mean = self.nominal + (self.tol_sup + self.tol_inf) / 2
        self.sigma = (self.tol_sup - self.tol_inf) / 6 / self.CP
        self.vector_samples = random.normal(loc=self.mean.magnitude,
                                            scale=self.sigma.magnitude,
                                            size=self.number_samples)


class SkewedDimensionGenerator(Dimension):
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
