from .dimension import Dimension
from .position import SquaredPosition
from typing import Any, Optional
from pydantic import BaseModel
import numpy as np

class PositionedHole(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    position: SquaredPosition
    diameter: Dimension
    diameter_evolv: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        self.diameter_evolv = self.diameter.nominal - self.diameter.tol_inf - self.position.tol
    
    def __sub__(self, other:"PositionedHole")->"PositionedHole":
        if not isinstance(other, PositionedHole):
            return None
        center_x = (self.position.nominal_x - other.position.nominal_x) / 2
        center_y = (self.position.nominal_y - other.position.nominal_y) / 2
        distance_self_other = np.sqrt((self.position.nominal_x - other.position.nominal_x) ** 2 +
                                      (self.position.nominal_y - other.position.nominal_y) ** 2)

        if distance_self_other > (self.diameter_evolv + other.diameter_evolv)/2:
            diameter_evolv = distance_self_other-self.diameter_evolv / 2 - other.diameter_evolv /2
        else:
            diameter_evolv = min(self.diameter_evolv, other.diameter_evolv)

        
        vector_centers_x = (self.position.vector_x - other.position.vector_x) / 2
        vector_centers_y = (self.position.vector_y - other.position.vector_y) / 2
        vector_distances_self_other= np.sqrt((self.position.vector_x - other.position.vector_x) ** 2 +
                                      (self.position.vector_y - other.position.vector_y) ** 2)
        
        diam_nominal = (
                        self.diameter.nominal.to("mm").magnitude
                        + other.diameter.nominal.to("mm").magnitude
                       ) / 2
        mask = vector_distances_self_other > diam_nominal
        vector_diameters = np.minimum(self.diameter.vector_samples, other.diameter.vector_samples)

        vector_diameters[mask] = (vector_distances_self_other[mask]-
                                 self.diameter.vector_samples[mask] / 2 - 
                                 other.diameter.vector_samples[mask] /2)
        diameter = Dimension(nominal=diameter_evolv,
                             tol_inf=0,
                             tol_sup=0,
                             number_samples=self.diameter.number_samples,
                             vector_samples=vector_diameters,
                             mean=vector_diameters.mean(),
                             sigma=vector_diameters.std()
                            )
        position=SquaredPosition(nominal_x=center_x,
                                 nominal_y=center_y,
                                 tol=0,
                                 vector_x=vector_centers_x,
                                 vector_y=vector_centers_y,
                                 sigma=np.sqrt(vector_centers_x.std() ** 2 +
                                               vector_centers_y.std() ** 2),
                                 vector_samples=vector_diameters,
                                )
        result = PositionedHole(diameter=diameter, position=position)
        return result