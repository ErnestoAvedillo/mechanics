from tolerances.pymodels.dimension import GausianDimensionGenerator
from matplotlib import pyplot as plt
SAMPLES = 100000
cota1 = GausianDimensionGenerator(nominal=12,
                           tol_sup=1,
                           tol_inf=-1,
                           CP=3,
                           number_samples=SAMPLES)
cota2 = GausianDimensionGenerator(nominal=12,
                           tol_sup=2,
                           tol_inf=-3,
                           CP=3,
                           number_samples=SAMPLES)

result = cota2.vector_samples + cota1.vector_samples
for i in range(10):
    print(f"{cota2.vector_samples[i]:.4f} - {cota1.vector_samples[i]:.4f} = {result[i]:.4f} mm")
print(f"Mean: {cota2.vector_samples.mean():.4f} mm")
print(f"Sigma: {cota2.vector_samples.std():.4f} mm")
plt.hist(cota2.vector_samples, bins=10, density=True)
plt.xlabel("Difference (mm)")
plt.ylabel("Density")
plt.title("Distribution of Agujero Differences")
plt.show()
print(f"Mean: {cota1.vector_samples.mean():.4f} mm")
print(f"Sigma: {cota1.vector_samples.std():.4f} mm")
plt.hist(cota1.vector_samples, bins=10, density=True)
plt.xlabel("Difference (mm)")
plt.ylabel("Density")
plt.title("Distribution of pin Differences")
plt.show()
print(f"Mean: {result.mean():.4f} mm")
print(f"Sigma: {result.std():.4f} mm")
plt.hist(result, bins=10, density=True)
plt.xlabel("Difference (mm)")
plt.ylabel("Density")
plt.title("Distribution of Differences")
plt.show()
