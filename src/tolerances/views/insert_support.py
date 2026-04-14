from django.shortcuts import render

from tolerances.classes.hystogram import Hystogram
from tolerances.pymodels.dimension import GausianDimensionGenerator

from tolerances.tools.conversion import _to_float, _to_magnitude
from tolerances.tools.get_fit_type import get_fit_type


def insert_support_calculator(request):
    values = {
        "support_height_nominal": 0,
        "support_height_tol_sup": 0,
        "support_height_tol_inf": 0,
        "spacer_height_nominal": 0,
        "spacer_height_tol_sup": 0,
        "spacer_height_tol_inf": 0,
        "support_diameter_nominal": 0,
        "support_diameter_tol_sup": 0,
        "support_diameter_tol_inf": 0,
        "spacer_diameter_nominal": 0,
        "spacer_diameter_tol_sup": 0,
        "spacer_diameter_tol_inf": 0,
        "cp": 1.33,
        "samples": 100000,
    }

    result = None
    error = None
    hist_clearance_height_base64 = None
    hist_diameter_interference_base64 = None


    if request.method == "POST":
        values = {
            "support_height_nominal": _to_float(request.POST.get("support_height_nominal"),
                                                values["support_height_nominal"]),
            "support_height_tol_sup": _to_float(request.POST.get("support_height_tol_sup"),
                                                values["support_height_tol_sup"]),
            "support_height_tol_inf": _to_float(request.POST.get("support_height_tol_inf"),
                                                values["support_height_tol_inf"]),
            "spacer_height_nominal": _to_float(request.POST.get("spacer_height_nominal"),
                                               values["spacer_height_nominal"]),
            "spacer_height_tol_sup": _to_float(request.POST.get("spacer_height_tol_sup"),
                                               values["spacer_height_tol_sup"]),
            "spacer_height_tol_inf": _to_float(request.POST.get("spacer_height_tol_inf"),
                                               values["spacer_height_tol_inf"]),
            "support_diameter_nominal": _to_float(request.POST.get("support_diameter_nominal"),
                                                  values["support_diameter_nominal"]),
            "support_diameter_tol_sup": _to_float(request.POST.get("support_diameter_tol_sup"),
                                                  values["support_diameter_tol_sup"]),
            "support_diameter_tol_inf": _to_float(request.POST.get("support_diameter_tol_inf"),
                                                  values["support_diameter_tol_inf"]),
            "spacer_diameter_nominal": _to_float(request.POST.get("spacer_diameter_nominal"),
                                                 values["spacer_diameter_nominal"]),
            "spacer_diameter_tol_sup": _to_float(request.POST.get("spacer_diameter_tol_sup"),
                                                 values["spacer_diameter_tol_sup"]),
            "spacer_diameter_tol_inf": _to_float(request.POST.get("spacer_diameter_tol_inf"),
                                                 values["spacer_diameter_tol_inf"]),
            "cp": _to_float(request.POST.get("cp"), values["cp"]),
            "samples": int(_to_float(request.POST.get("samples"), values["samples"])),
        }

        try:
            support_height = GausianDimensionGenerator(
                nominal=values["support_height_nominal"],
                tol_sup=values["support_height_tol_sup"],
                tol_inf=values["support_height_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )
            spacer_height = GausianDimensionGenerator(
                nominal=values["spacer_height_nominal"],
                tol_sup=values["spacer_height_tol_sup"],
                tol_inf=values["spacer_height_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            support_diameter = GausianDimensionGenerator(
                nominal=values["support_diameter_nominal"],
                tol_sup=values["support_diameter_tol_sup"],
                tol_inf=values["support_diameter_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            spacer_diameter = GausianDimensionGenerator(
                nominal=values["spacer_diameter_nominal"],
                tol_sup=values["spacer_diameter_tol_sup"],
                tol_inf=values["spacer_diameter_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            diameter_interference = spacer_height - spacer_diameter
            clearance_height = spacer_height - support_height

            histogram = Hystogram(
                dimension=diameter_interference,
                bins=50,
                xlabel="Diferencia de diametros (mm)",
                ylabel="Densidad",
                title="Histograma de interferencia Tubo Casquillo",
            )
            hist_diameter_interference_base64 = histogram.plot_to_base64_png()

            histogram = Hystogram(
                dimension=clearance_height,
                bins=50,
                xlabel="Espesor de pared (mm)",
                ylabel="Densidad",
                title="Histograma de espesor de pared",
            )
            hist_clearance_height_base64 = histogram.plot_to_base64_png()
            
            result = {
                "support_height": {
                    "max": _to_magnitude(support_height.nominal + support_height.tol_sup),
                    "min": _to_magnitude(support_height.nominal + support_height.tol_inf),
                    "mean": float(support_height.mean.magnitude),
                    "sigma": float(support_height.sigma.magnitude),
                },
                "spacer_height": {
                    "max": _to_magnitude(spacer_height.nominal + spacer_height.tol_sup),
                    "min": _to_magnitude(spacer_height.nominal + spacer_height.tol_inf),
                    "mean": float(spacer_height.mean.magnitude),
                    "sigma": float(spacer_height.sigma.magnitude),
                },
                "support_diameter": {
                    "max": _to_magnitude(support_diameter.nominal + support_diameter.tol_sup),
                    "min": _to_magnitude(support_diameter.nominal + support_diameter.tol_inf),
                    "mean": float(support_diameter.mean.magnitude),
                    "sigma": float(support_diameter.sigma.magnitude),
                },
                "spacer_diameter": {
                    "max": _to_magnitude(spacer_diameter.nominal + spacer_diameter.tol_sup),
                    "min": _to_magnitude(spacer_diameter.nominal + spacer_diameter.tol_inf),
                    "mean": float(spacer_diameter.mean.magnitude),
                    "sigma": float(spacer_diameter.sigma.magnitude),
                },
                "clearance_height": {
                    "nominal": _to_magnitude(clearance_height.nominal),
                    "tol_sup": _to_magnitude(clearance_height.tol_sup),
                    "tol_inf": _to_magnitude(clearance_height.tol_inf),
                    "mean_samples": float(clearance_height.vector_samples.mean()),
                    "sigma_samples": float(clearance_height.vector_samples.std()),
                    "fit_type": get_fit_type(clearance_height),
                    "histogram": hist_clearance_height_base64,
                },
                "diameter_interference": {
                    "nominal": _to_magnitude(diameter_interference.nominal),
                    "max_interference": _to_magnitude(diameter_interference.tol_sup + diameter_interference.nominal),
                    "min_interference": _to_magnitude(diameter_interference.tol_inf + diameter_interference.nominal),
                    "mean_samples": float(diameter_interference.vector_samples.mean()),
                    "sigma_samples": float(diameter_interference.vector_samples.std()),
                    "fit_type": get_fit_type(diameter_interference),
                    "histogram": hist_diameter_interference_base64,
                },
            }

        except Exception as exc:
            error = str(exc)
            print(f"Error al calcular tolerancias: {error}")
            print(exc)
    return render(
        request,
        "tolerances/insert_support.html",
        {
            "values": values,
            "result": result,
            "error": error,
        },
    )
