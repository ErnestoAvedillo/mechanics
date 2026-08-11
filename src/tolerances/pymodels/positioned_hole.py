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

    def __sub__(self, other: "PositionedHole") -> "PositionedHole":
        if not isinstance(other, PositionedHole):
            return None
        # Calculate with the nominal values of the position and diameter of the resulting free gap
        # Calculate the center position of the resulting diameter of the free gap
        center_x = (self.position.nominal_x - other.position.nominal_x) / 2
        center_y = (self.position.nominal_y - other.position.nominal_y) / 2
        # Calculate the distance between the centers of the two holes
        distance_self_other = np.sqrt((self.position.nominal_x - other.position.nominal_x) ** 2 +
                                      (self.position.nominal_y - other.position.nominal_y) ** 2)
        # Take into account the case where the holes are not overlapping,
        # in which case the free gap is the distance between the holes minus their radii
        if distance_self_other > (self.diameter_evolv + other.diameter_evolv) / 2:
            diameter_evolv = 0
        else:
            gresultant_gap = (self.diameter_evolv + other.diameter_evolv) / 2 - distance_self_other
            diameter_evolv = np.minimum(gresultant_gap, np.minimum(self.diameter_evolv, other.diameter_evolv))
        # I'll make the same calculation for the vector of samples,
        # and taking into account the case where the holes are not overlapping
        # Calculate the vector for the centers of the resulting diameter of the free gap
        vector_centers_x = (self.position.vector_x - other.position.vector_x) / 2
        vector_centers_y = (self.position.vector_y - other.position.vector_y) / 2
        # Calculate the vector for the distances between the centers of the two holes for each sample
        vector_distances_self_other = np.sqrt((self.position.vector_x - other.position.vector_x) ** 2 +
                                              (self.position.vector_y - other.position.vector_y) ** 2)
        
        #Initialize the vector for the diameters of the resulting free gap with zeros
        min_diameter = np.zeros_like(vector_distances_self_other)
        #Check the case where the holes are overlapping
        mask_overlapping = vector_distances_self_other < (self.diameter.vector_samples + other.diameter.vector_samples) / 2
        # Calculate the overlapp for all samples.
        theoretical_min_diameter = (self.diameter.vector_samples + other.diameter.vector_samples) / 2 - vector_distances_self_other
        #Take the minimum between the overlap and the diameters of the holes for the samples where they are overlapping
        current_min_diameter = np.minimum(theoretical_min_diameter, np.minimum(self.diameter.vector_samples, other.diameter.vector_samples) )
        #Update min_diameter only for the samples where the holes are overlapping
        min_diameter[mask_overlapping] = current_min_diameter[mask_overlapping]
        diameter = Dimension(nominal=diameter_evolv,
                             tol_inf=0,
                             tol_sup=0,
                             number_samples=self.diameter.number_samples,
                             vector_samples=min_diameter,
                             mean=min_diameter.mean(),
                             sigma=min_diameter.std())
        position = SquaredPosition(nominal_x=center_x,
                                   nominal_y=center_y,
                                   tol=0,
                                   vector_x=vector_centers_x,
                                   vector_y=vector_centers_y,
                                   sigma=np.sqrt(vector_centers_x.std() ** 2 +
                                                 vector_centers_y.std() ** 2),
                                   number_samples=self.diameter.number_samples)

        result = PositionedHole(diameter=diameter, position=position)
        return result
