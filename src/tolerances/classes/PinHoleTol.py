from pydantic import model_validator, field_validator
from pint import UnitRegistry
from typing import Optional
from tolerances.pymodels.dimension import Dimension, GausianDimensionGenerator
from tolerances.classes.hystogram import Hystogram
unit = UnitRegistry()


class PinHoleTol():
    """Class to calculate pin and hole tolerance and fit analysis."""
    pin: Optional[GausianDimensionGenerator] = None
    hole:Optional[GausianDimensionGenerator] = None
    gap_result: Optional[Dimension] = None

    def __init__(self, pin_nominal: float, pin_tol_sup: float, pin_tol_inf: float,
                 hole_nominal: float, hole_tol_sup: float, hole_tol_inf: float):
        self.pin = GausianDimensionGenerator(Nominal=pin_nominal * unit.mm, TolSup=pin_tol_sup * unit.mm, TolInf=pin_tol_inf * unit.mm)
        self.hole = GausianDimensionGenerator(Nominal=hole_nominal * unit.mm, TolSup=hole_tol_sup * unit.mm, TolInf=hole_tol_inf * unit.mm)

    @model_validator(mode='after')
    def calculate_fit(self):
        """Calculate fit characteristics automatically."""

        # Calculate max and min dimensions
        self.gap_result = self.hole - self.pin
        
        # Determine fit type
        if self.max_clearance < 0 * unit.mm and self.min_clearance < 0 * unit.mm:
            self.fit_type = "Interference (Apriete)"
        elif self.max_clearance > 0 * unit.mm and self.min_clearance > 0 * unit.mm:
            self.fit_type = "Clearance (Juego)"
        else:
            self.fit_type = "Transition (Ajuste de Transición)"
        
        return self
    
    def get_summary(self) -> dict:
        """Return a summary of the pin-hole tolerance calculation."""
        return {
            "pin": {
                "nominal": self.pin_nominal,
                "tolerance_sup": self.pin_tol_sup,
                "tolerance_inf": self.pin_tol_inf,
                "max": self.max_pin,
                "min": self.min_pin,
            },
            "hole": {
                "nominal": self.hole_nominal,
                "tolerance_sup": self.hole_tol_sup,
                "tolerance_inf": self.hole_tol_inf,
                "max": self.max_hole,
                "min": self.min_hole,
            },
            "fit": {
                "max_clearance": self.max_clearance,
                "min_clearance": self.min_clearance,
                "fit_type": self.fit_type,
            }
        }
