from tolerances.classes.PinHoleTol import PinHoleTol

# Example: H7/g6 fit (Clearance fit)
pin_hole = PinHoleTol(
    pin_nominal=10,
    pin_tol_sup=0,
    pin_tol_inf=-0.025,
    hole_nominal=10,
    hole_tol_sup=0.025,
    hole_tol_inf=0
)

print("Pin-Hole Tolerance Analysis")
print("=" * 50)
summary = pin_hole.get_summary()

print(f"\nPin:")
print(f"  Nominal: {summary['pin']['nominal']}")
print(f"  Max: {summary['pin']['max']}")
print(f"  Min: {summary['pin']['min']}")

print(f"\nHole:")
print(f"  Nominal: {summary['hole']['nominal']}")
print(f"  Max: {summary['hole']['max']}")
print(f"  Min: {summary['hole']['min']}")

print(f"\nFit Analysis:")
print(f"  Max Clearance: {summary['fit']['max_clearance']}")
print(f"  Min Clearance: {summary['fit']['min_clearance']}")
print(f"  Fit Type: {summary['fit']['fit_type']}")
