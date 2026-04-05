from django.shortcuts import render

from tolerances.classes.hystogram import Hystogram
from tolerances.pymodels.dimension import GausianDimensionGenerator


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pin_hole_calculator(request):
    values = {
        "pin_nominal": 10.0,
        "pin_tol_sup": 0.0,
        "pin_tol_inf": -0.025,
        "hole_nominal": 10.0,
        "hole_tol_sup": 0.025,
        "hole_tol_inf": 0.0,
        "cp": 1.33,
        "samples": 100000,
    }

    result = None
    histogram_base64 = None
    error = None

    if request.method == "POST":
        values = {
            "pin_nominal": _to_float(request.POST.get("pin_nominal"), values["pin_nominal"]),
            "pin_tol_sup": _to_float(request.POST.get("pin_tol_sup"), values["pin_tol_sup"]),
            "pin_tol_inf": _to_float(request.POST.get("pin_tol_inf"), values["pin_tol_inf"]),
            "hole_nominal": _to_float(request.POST.get("hole_nominal"), values["hole_nominal"]),
            "hole_tol_sup": _to_float(request.POST.get("hole_tol_sup"), values["hole_tol_sup"]),
            "hole_tol_inf": _to_float(request.POST.get("hole_tol_inf"), values["hole_tol_inf"]),
            "cp": _to_float(request.POST.get("cp"), values["cp"]),
            "samples": int(_to_float(request.POST.get("samples"), values["samples"])),
        }

        try:
            pin = GausianDimensionGenerator(
                nominal=values["pin_nominal"],
                tol_sup=values["pin_tol_sup"],
                tol_inf=values["pin_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )
            hole = GausianDimensionGenerator(
                nominal=values["hole_nominal"],
                tol_sup=values["hole_tol_sup"],
                tol_inf=values["hole_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            gap = hole - pin

            max_pin = values["pin_nominal"] + values["pin_tol_sup"]
            min_pin = values["pin_nominal"] + values["pin_tol_inf"]
            max_hole = values["hole_nominal"] + values["hole_tol_sup"]
            min_hole = values["hole_nominal"] + values["hole_tol_inf"]
            max_clearance = gap.mean.magnitude + 4 * gap.sigma.magnitude
            min_clearance = gap.mean.magnitude - 4 * gap.sigma.magnitude

            if max_clearance < 0 and min_clearance < 0:
                fit_type = "Apriete (Interference fit)"
            elif max_clearance > 0 and min_clearance > 0:
                fit_type = "Juego (Clearance fit)"
            else:
                fit_type = "Transicion (Transition fit)"

            result = {
                "pin": {
                    "max": max_pin,
                    "min": min_pin,
                    "mean": float(pin.mean.magnitude),
                    "sigma": float(pin.sigma.magnitude),
                },
                "hole": {
                    "max": max_hole,
                    "min": min_hole,
                    "mean": float(hole.mean.magnitude),
                    "sigma": float(hole.sigma.magnitude),
                },
                "gap": {
                    "nominal": gap.nominal,
                    "tol_sup": gap.tol_sup,
                    "tol_inf": gap.tol_inf,
                    "mean_samples": float(gap.vector_samples.mean()),
                    "sigma_samples": float(gap.vector_samples.std()),
                    "max_clearance": float(max_clearance),
                    "min_clearance": float(min_clearance),
                    "fit_type": fit_type,
                },
            }
            histogram = Hystogram(
                dimension=gap,
                bins=50,
                xlabel="Diferencia de diametros (mm)",
                ylabel="Densidad",
                title="Histograma de (Agujero - Pin)",
            )
            histogram_base64 = histogram.plot_to_base64_png()
        except Exception as exc:
            error = str(exc)

    return render(
        request,
        "tolerances/pin_hole.html",
        {
            "values": values,
            "result": result,
            "histogram_base64": histogram_base64,
            "error": error,
        },
    )
