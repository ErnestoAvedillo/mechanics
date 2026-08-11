from django.shortcuts import render
from django.utils.translation import gettext as _

from tolerances.classes.hystogram import Hystogram
from tolerances.pymodels.dimension import GausianDimensionGenerator

from tolerances.tools.conversion import _to_float, _to_magnitude
from tolerances.tools.get_fit_type import get_fit_type


def pivot_bushing_hole_axial_calculator(request):
    values = {
        "tube_length_nominal": 0,
        "tube_length_tol_sup": 0,
        "tube_length_tol_inf": 0,
        "bushing_flange_1_nominal": 0,
        "bushing_flange_1_tol_sup": 0,
        "bushing_flange_1_tol_inf": 0,
        "bushing_flange_2_nominal": 0,
        "bushing_flange_2_tol_sup": 0,
        "bushing_flange_2_tol_inf": 0,
        "wall_distance_nominal": 0,
        "wall_distance_tol_sup": 0,
        "wall_distance_tol_inf": 0,
        "cp": 1.33,
        "samples": 100000,
    }

    result = None
    error = None
    hist_system_clearance_base64 = None


    if request.method == "POST":
        values = {
            "tube_length_nominal": _to_float(request.POST.get("tube_length_nominal"), values["tube_length_nominal"]),
            "tube_length_tol_sup": _to_float(request.POST.get("tube_length_tol_sup"), values["tube_length_tol_sup"]),
            "tube_length_tol_inf": _to_float(request.POST.get("tube_length_tol_inf"), values["tube_length_tol_inf"]),
            "bushing_flange_1_nominal": _to_float(request.POST.get("bushing_flange_1_nominal"), values["bushing_flange_1_nominal"]),
            "bushing_flange_1_tol_sup": _to_float(request.POST.get("bushing_flange_1_tol_sup"), values["bushing_flange_1_tol_sup"]),
            "bushing_flange_1_tol_inf": _to_float(request.POST.get("bushing_flange_1_tol_inf"), values["bushing_flange_1_tol_inf"]),
            "bushing_flange_2_nominal": _to_float(request.POST.get("bushing_flange_2_nominal"), values["bushing_flange_2_nominal"]),
            "bushing_flange_2_tol_sup": _to_float(request.POST.get("bushing_flange_2_tol_sup"), values["bushing_flange_2_tol_sup"]),
            "bushing_flange_2_tol_inf": _to_float(request.POST.get("bushing_flange_2_tol_inf"), values["bushing_flange_2_tol_inf"]),
            "wall_distance_nominal": _to_float(request.POST.get("wall_distance_nominal"), values["wall_distance_nominal"]),
            "wall_distance_tol_sup": _to_float(request.POST.get("wall_distance_tol_sup"), values["wall_distance_tol_sup"]),
            "wall_distance_tol_inf": _to_float(request.POST.get("wall_distance_tol_inf"), values["wall_distance_tol_inf"]),
            "cp": _to_float(request.POST.get("cp"), values["cp"]),
            "samples": int(_to_float(request.POST.get("samples"), values["samples"])),
        }

        try:
            tube = GausianDimensionGenerator(
                nominal=values["tube_length_nominal"],
                tol_sup=values["tube_length_tol_sup"],
                tol_inf=values["tube_length_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )
            bushing_flange_1 = GausianDimensionGenerator(
                nominal=values["bushing_flange_1_nominal"],
                tol_sup=values["bushing_flange_1_tol_sup"],
                tol_inf=values["bushing_flange_1_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            bushing_flange_2 = GausianDimensionGenerator(
                nominal=values["bushing_flange_2_nominal"],
                tol_sup=values["bushing_flange_2_tol_sup"],
                tol_inf=values["bushing_flange_2_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            wall_distance = GausianDimensionGenerator(
                nominal=values["wall_distance_nominal"],
                tol_sup=values["wall_distance_tol_sup"],
                tol_inf=values["wall_distance_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            system_clearance = wall_distance - tube - bushing_flange_1 - bushing_flange_2

            histogram = Hystogram(
                dimension=system_clearance,
                bins=50,
                xlabel=_("Juego del sistema (mm)"),
                ylabel=_("Densidad"),
                title=_("Histograma del juego del sistema"),
            )
            hist_system_clearance_base64 = histogram.plot_to_base64_png()


            result = {
                "tube_length": {
                    "max": _to_magnitude(tube.nominal + tube.tol_sup),
                    "min": _to_magnitude(tube.nominal + tube.tol_inf),
                    "mean": float(tube.mean.magnitude),
                    "sigma": float(tube.sigma.magnitude),
                },
                "bushing_flange_1": {
                    "max": _to_magnitude(bushing_flange_1.nominal + bushing_flange_1.tol_sup),
                    "min": _to_magnitude(bushing_flange_1.nominal + bushing_flange_1.tol_inf),
                    "mean": float(bushing_flange_1.mean.magnitude),
                    "sigma": float(bushing_flange_1.sigma.magnitude),
                },
                "bushing_flange_2": {
                    "max": _to_magnitude(bushing_flange_2.nominal + bushing_flange_2.tol_sup),
                    "min": _to_magnitude(bushing_flange_2.nominal + bushing_flange_2.tol_inf),
                    "mean": float(bushing_flange_2.mean.magnitude),
                    "sigma": float(bushing_flange_2.sigma.magnitude),
                },
                "wall_distance": {
                    "max": _to_magnitude(wall_distance.nominal + wall_distance.tol_sup),
                    "min": _to_magnitude(wall_distance.nominal + wall_distance.tol_inf),
                    "mean": float(wall_distance.mean.magnitude),
                    "sigma": float(wall_distance.sigma.magnitude),
                },
                "system_clearance": {
                    "nominal": _to_magnitude(system_clearance.nominal),
                    "tol_sup": _to_magnitude(system_clearance.tol_sup),
                    "tol_inf": _to_magnitude(system_clearance.tol_inf),
                    "mean_samples": float(system_clearance.vector_samples.mean()),
                    "sigma_samples": float(system_clearance.vector_samples.std()),
                    "fit_type": get_fit_type(system_clearance),
                    "histogram": hist_system_clearance_base64,
                },
            }

        except Exception as exc:
            error = str(exc)
            print(f"Error al calcular tolerancias: {error}")
            print(exc)
    return render(
        request,
        "tolerances/pivot_bushing_hole_axial.html",
        {
            "values": values,
            "result": result,
            "error": error,
        },
    )
