from .dimension import Dimension
from pydantic import BaseModel, BeforeValidator, Field
from pint import UnitRegistry, Quantity
from typing import Optional, Any, Annotated
from numpy import random, ndarray
from scipy.stats import norm
from .convert import PintQuantity
import numpy as np

ureg = UnitRegistry()


class SquaredPosition(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    nominal_x : PintQuantity = 0.0 * ureg.mm
    nominal_y : PintQuantity = 0.0 * ureg.mm
    tol: PintQuantity = 0.0 * ureg.mm
    sigma: Optional[PintQuantity] = 0.0 * ureg.mm
    vector_x: Optional[ndarray] = None
    vector_y: Optional[ndarray] = None
    dpmo: Optional[float] = 0
    CP: Optional[float] = 1.0
    number_samples: int = 100000


    def model_post_init(self, __context):

        # 6σ = lado / CP
        sigma = (self.tol / 2) / 3 / self.CP

        self.vector_x = np.random.normal(
            loc=self.nominal_x.magnitude,
            scale=sigma.magnitude,
            size=self.number_samples
        )

        self.vector_y = np.random.normal(
            loc=self.nominal_y.magnitude,
            scale=sigma.magnitude,
            size=self.number_samples
        )


    def __add__(self, other)->'SquaredPosition':
        if not isinstance(other, SquaredPosition):
            return NotImplemented
        nominal_x = self.nominal_x + other.nominal_x
        nominal_y = self.nominal_y + other.nominal_y
        tolerance = self.tol + other.tol
        
        result = SquaredPosition(
            nominal_x,
            nominal_y,
            tolerance
        )
        return result


    def __sub__(self, other)->'SquaredPosition':
        if not isinstance(other, SquaredPosition):
            return NotImplemented
        nominal_x = self.nominal_x - other.nominal_x
        nominal_y = self.nominal_y -  other.nominal_y
        tolerance = self.tol + other.tol
        
        result = SquaredPosition(
            nominal_x=nominal_x,
            nominal_y=nominal_y,
            tol=tolerance,
            number_samples=self.number_samples
        )
        return result


    def __add__(self, other)->'SquaredPosition':
        nominal_x = self.nominal_x + other.nominal_x
        nominal_y = self.nominal_y + other.nominal_y
        tolerance = self.tol + other.tol
        
        result = SquaredPosition(
            nominal_x,
            nominal_y,
            tol=tolerance,
            number_samples=self.number_samples
        )
        return result
    
    def get_dimension(self)->Dimension:
        distances = np.sqrt(self.vector_x ** 2 + self.vector_y ** 2)
        result = Dimension(
            mean = distances.mean(),
            tol_inf = -1 * distances.std() * self.CP / 2,
            tol_sup = distances.std() * self.CP / 2,
            vector_samples=distances,
            number_samples=self.number_samples
        )
        return result


    def calc_dpmo(self):
        """
        DPMO para zona cuadrada
        """
        out_x = np.abs(self.vector_x - self.nominal_x.magnitude) > (self.tol.magnitude / 2)
        out_y = np.abs(self.vector_y - self.nominal_y.magnitude) > (self.tol.magnitude / 2)

        failures = out_x | out_y
        self.dpmo = failures.mean() * 1_000_000
        return self.dpmo
