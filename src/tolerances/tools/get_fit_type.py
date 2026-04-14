
from src.tolerances.pymodels.dimension import Dimension


def get_fit_type(dimension: Dimension):
    max_clearance = dimension.nominal + dimension.tol_sup
    min_clearance = dimension.nominal + dimension.tol_inf

    if max_clearance < min_clearance:
        return "Interference"
    elif max_clearance == min_clearance:
        return "Transition"
    else:
        return "Clearance"
