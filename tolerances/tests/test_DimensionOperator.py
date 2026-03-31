import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))

from tolerances.pymodels.dimension import GausianDimensionGenerator, DimensionOperator

# Crear dos dimensiones gaussianas
dim1 = GausianDimensionGenerator(
    nominal=10,
    tol_sup=0.5,
    tol_inf=-0.5,
    CP=2,
    number_samples=100000
)

dim2 = GausianDimensionGenerator(
    nominal=15,
    tol_sup=0.3,
    tol_inf=-0.3,
    CP=2,
    number_samples=100000
)

# Suma de dimensiones
dim_sum = DimensionOperator.add(dim1, dim2)

print("=" * 60)
print("SUMA DE DIMENSIONES")
print("=" * 60)
print(f"\nDimensión 1:")
print(f"  Nominal: {dim1.nominal}")
print(f"  Tolerancia Superior: {dim1.tol_sup}")
print(f"  Tolerancia Inferior: {dim1.tol_inf}")
print(f"  Media: {dim1.mean:.4f}")
print(f"  Sigma: {dim1.sigma:.6f}")

print(f"\nDimensión 2:")
print(f"  Nominal: {dim2.nominal}")
print(f"  Tolerancia Superior: {dim2.tol_sup}")
print(f"  Tolerancia Inferior: {dim2.tol_inf}")
print(f"  Media: {dim2.mean:.4f}")
print(f"  Sigma: {dim2.sigma:.6f}")

print(f"\nResultado SUMA:")
print(f"  Nominal: {dim_sum.nominal}")
print(f"  Tolerancia Superior: {dim_sum.tol_sup}")
print(f"  Tolerancia Inferior: {dim_sum.tol_inf}")
print(f"  Media: {dim_sum.mean:.4f}")
print(f"  Sigma: {dim_sum.sigma:.6f}")
print(f"  Media de muestras: {dim_sum.vector_samples.mean():.4f}")
print(f"  Desv. Est. de muestras: {dim_sum.vector_samples.std():.6f}")

# Resta de dimensiones
print("\n" + "=" * 60)
print("RESTA DE DIMENSIONES (dim1 - dim2)")
print("=" * 60)

dim_sub = DimensionOperator.subtract(dim1, dim2)
print(f"\nResultado RESTA:")
print(f"  Nominal: {dim_sub.nominal}")
print(f"  Tolerancia Superior: {dim_sub.tol_sup}")
print(f"  Tolerancia Inferior: {dim_sub.tol_inf}")
print(f"  Media: {dim_sub.mean:.4f}")
print(f"  Sigma: {dim_sub.sigma:.6f}")
print(f"  Media de muestras: {dim_sub.vector_samples.mean():.4f}")
print(f"  Desv. Est. de muestras: {dim_sub.vector_samples.std():.6f}")
