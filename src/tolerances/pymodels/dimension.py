from pydantic import BaseModel, Field
from pint import Quantity
from typing import Optional, Any
from numpy import random, ndarray
from scipy.stats import norm, skewnorm
from .convert import PintQuantity, ureg


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
        Calculates the DPMO for a normal distribution
        with asymmetric tolerances.
        """
        p_lower = norm.cdf(self.tol_inf, loc=self.mean, scale=self.sigma)
        p_upper = 1 - norm.cdf(self.tol_sup, loc=self.mean, scale=self.sigma)
        self.dpmo = (p_lower + p_upper) * 1_000_000
        return self.dpmo

    def __add__(self, other: 'Dimension') -> 'Dimension':
        """Adds two dimensions using the + operator"""
        if not isinstance(other, Dimension):
            return NotImplemented

        # Add nominals
        nominal_sum = self.nominal + other.nominal

        # Add tolerances
        tol_sup_sum = self.tol_sup + other.tol_sup
        tol_inf_sum = self.tol_inf + other.tol_inf

        # Use the CP of the first element
        cp_result = self.CP

        # Number of samples
        num_samples = getattr(self, 'number_samples', 100000)

        # Create the resulting new dimension
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
        """Subtracts two dimensions using the - operator"""
        if not isinstance(other, Dimension):
            return NotImplemented

        # Subtract nominals
        nominal_sub = self.nominal - other.nominal

        # Subtract tolerances (upper and lower are swapped)
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

        # Subtract the sample vectors
        if self.vector_samples is not None and other.vector_samples is not None:
            result.vector_samples = self.vector_samples - other.vector_samples
            result.mean = result.vector_samples.mean() * ureg.mm
            result.sigma = result.vector_samples.std() * ureg.mm

        return result

    def __truediv__(self, other) -> 'Dimension':
        """Divides a dimension using the / operator"""

        if not isinstance(other, (int, float)):
            return NotImplemented

        # Divide nominals
        nominal_sub = self.nominal / other

        # Divide tolerances
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

        # Divide the sample vectors
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
        self.calc_dpmo()
            
    def __str__(self):
        return_str = f"Dimension(nominal={self.nominal}, tol_sup={self.tol_sup},tol_inf={self.tol_inf} \n"
        return_str += f"mean={self.mean}, sigma={self.sigma}, tol_sup_sum={self.tol_sup_sum}, tol_inf_sum={self.tol_inf_sum})\n"
        return_str += f"dpmo={self.dpmo}"
        return return_str

class GausianDimensionGenerator(Dimension):
    number_samples: int = Field(default=100000,
                                validation_alias="NumberSamples")

    # Generate the sample vector after model validation
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
