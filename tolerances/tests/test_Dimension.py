from tolerances.pymodels.dimension import GausianDimensionGenerator
from matplotlib import pyplot as plt
SAMPLES = 100000
cota1 = GausianDimensionGenerator(nominal=10,
                           tol_sup=0.5,
                           tol_inf=0,
                           CP=2,
                           number_samples=SAMPLES)
cota2 = GausianDimensionGenerator(nominal=11,
                           tol_sup=0,
                           tol_inf=-0.5,
                           CP=2,
                           number_samples=SAMPLES)

result = cota1.vector_samples - cota2.vector_samples
print(f"Mean: {result.mean():.4f} mm")
print(f"Sigma: {result.std():.4f} mm")
plt.hist(result, bins=50, density=True)
plt.xlabel("Difference (mm)")
plt.ylabel("Density")
plt.title("Distribution of Dimensional Differences")
plt.show()