from tolerances.pymodels.dimension import Dimension
from tolerances.pymodels.position import SquaredPosition
from tolerances.pymodels.positioned_hole import PositionedHole
from matplotlib import pyplot as plt


SAMPLES = 100000
Hole_position_1 = SquaredPosition(nominal_x=0,
                                 nominal_y=0,
                                 tol=0.5,
                                 number_samples=SAMPLES)
Hole_position_2 = SquaredPosition(nominal_x=0.5,
                                 nominal_y=0.5,
                                 tol=0.5,
                                 number_samples=SAMPLES)
Diameter1 = Dimension(nominal=10,
                      tol_sup=0.5,
                      tol_inf=0,
                      CP=2,
                      number_samples=SAMPLES)
Diameter2 = Dimension(nominal=11,
                      tol_sup=0,
                      tol_inf=-0.5,
                      CP=2,
                      number_samples=SAMPLES)
hole1 = PositionedHole(position=Hole_position_1, diameter=Diameter1)
hole2 = PositionedHole(position=Hole_position_2, diameter=Diameter2)
Evold_free_gap = hole1 - hole2
print(f"Mean: {Evold_free_gap.diameter.mean:.4f} mm")
print(f"Sigma: {Evold_free_gap.diameter.sigma:.4f} mm")
plt.hist(Evold_free_gap.diameter.vector_samples, bins=50, density=True)
plt.xlabel("Difference (mm)")
plt.ylabel("Density")
plt.title("Distribution of Dimensional Differences")
plt.show()
