import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))

from tolerances.pymodels.dimension import GausianDimensionGenerator
from tolerances.classes.hystogram import Hystogram

# Crear una dimensión gaussiana
dim = GausianDimensionGenerator(
    nominal=10,
    tol_sup=0,
    tol_inf=-0.5,
    CP=1.33,
    number_samples=100000
)

# Crear histograma con líneas verticales
hist = Hystogram(
    dimension=dim,
    bins=50,
    xlabel="Dimension (mm)",
    ylabel="Density",
    title="Distribution with Tolerance Limits"
)

print("=" * 60)
print("HISTOGRAMA CON LÍNEAS DE REFERENCIA")
print("=" * 60)
print(f"\nDimensión:")
print(f"  Nominal: {dim.nominal}")
print(f"  Tol. Sup: {dim.tol_sup}")
print(f"  Tol. Inf: {dim.tol_inf}")
print(f"  Media: {dim.mean:.4f}")
print(f"  Sigma: {dim.sigma:.6f}")
print(f"\nLímite superior (Nominal + Tol.Sup): {(dim.nominal + dim.tol_sup).magnitude:.4f}")
print(f"Límite inferior (Nominal + Tol.Inf): {(dim.nominal + dim.tol_inf).magnitude:.4f}")
print(f"\nGraficando histograma con:")
print(f"  - Línea roja (--): Media")
print(f"  - Línea verde (:): Tolerancia Superior")
print(f"  - Línea naranja (:): Tolerancia Inferior")

# Mostrar el histograma
hist.plot()
