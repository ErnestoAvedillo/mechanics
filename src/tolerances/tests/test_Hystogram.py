import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))

from tolerances.pymodels.dimension import GausianDimensionGenerator
from tolerances.classes.hystogram import Hystogram

# Crear una dimensión gaussiana
dim1 = GausianDimensionGenerator(
    nominal=24,
    tol_sup=3,
    tol_inf=-4,
    CP=1.33,
    number_samples=100000
)

# Crear una dimensión gaussiana
dim2 = GausianDimensionGenerator(
    nominal=5,
    tol_sup=1,
    tol_inf=-0.75,
    CP=1.33,
    number_samples=100000
)
# Crear una dimensión gaussiana
dim3 = GausianDimensionGenerator(
    nominal=4,
    tol_sup=0.1,
    tol_inf=-0.2,
    CP=1.33,
    number_samples=100000
)
# Crear una dimensión gaussiana
dim4 = GausianDimensionGenerator(
    nominal=3.5,
    tol_sup=0.3,
    tol_inf=-0.1,
    CP=1.33,
    number_samples=100000
)
result = dim1 - dim2 - dim3 - dim4
# Crear histograma con líneas verticales
hist = Hystogram(
    dimension=result,
    bins=50,
    xlabel="Dimension (mm)",
    ylabel="Density",
    title="Distribution with Tolerance Limits"
)
print("=" * 60)
print("HISTOGRAMA CON LÍNEAS DE REFERENCIA")
print("=" * 60)
print(f"\nDimensión:")
print(f"  Nominal: {result.nominal}")
print(f"  Tol. Sup: {result.tol_sup}")
print(f"  Tol. Inf: {result.tol_inf}")
print(f"  Media: {result.mean:.4f}")
print(f"  Sigma: {result.sigma:.6f}")
print(f"\nLímite superior (Nominal + Tol.Sup): {(result.nominal + result.tol_sup).magnitude:.4f}")
print(f"Límite inferior (Nominal + Tol.Inf): {(result.nominal + result.tol_inf).magnitude:.4f}")
print(f"\nGraficando histograma con:")
print(f"  - Línea roja (--): Media")
print(f"  - Línea verde (:): Tolerancia Superior")
print(f"  - Línea naranja (:): Tolerancia Inferior")

# Mostrar el histograma
hist.show_plot()

input("Presiona Enter para mostrar el histograma...")