from django.shortcuts import render
from django.utils.translation import gettext as _

from tolerances.classes.hystogram import Hystogram
from tolerances.pymodels.dimension import GausianDimensionGenerator

from tolerances.tools.conversion import _to_float, _to_magnitude
from tolerances.tools.get_fit_type import get_fit_type


def pivot_bushing_hole_radial_calculator(request):
    values = {
        "pin_nominal": 0,
        "pin_tol_sup": 0,
        "pin_tol_inf": 0,
        "hole_nominal": 0,
        "hole_tol_sup": 0,
        "hole_tol_inf": 0,
        "inner_bushing_nominal": 0,
        "inner_bushing_tol_sup": 0,
        "inner_bushing_tol_inf": 0,
        "outer_bushing_nominal": 0,
        "outer_bushing_tol_sup": 0,
        "outer_bushing_tol_inf": 0,
        "cp": 1.33,
        "samples": 100000,
    }

    result = None
    error = None
    hist_interf_tube_bushing_base64 = None
    hist_wall_thickness_base64 = None
    hist_system_clearance_base64 = None

    if request.method == "POST":
        values = {
            "pin_nominal": _to_float(request.POST.get("pin_nominal"),
                                     values["pin_nominal"]),
            "pin_tol_sup": _to_float(request.POST.get("pin_tol_sup"),
                                     values["pin_tol_sup"]),
            "pin_tol_inf": _to_float(request.POST.get("pin_tol_inf"),
                                     values["pin_tol_inf"]),
            "hole_nominal": _to_float(request.POST.get("hole_nominal"),
                                      values["hole_nominal"]),
            "hole_tol_sup": _to_float(request.POST.get("hole_tol_sup"),
                                      values["hole_tol_sup"]),
            "hole_tol_inf": _to_float(request.POST.get("hole_tol_inf"),
                                      values["hole_tol_inf"]),
            "inner_bushing_nominal": _to_float(request.POST.get("inner_bushing_nominal"),
                                               values["inner_bushing_nominal"]),
            "inner_bushing_tol_sup": _to_float(request.POST.get("inner_bushing_tol_sup"),
                                               values["inner_bushing_tol_sup"]),
            "inner_bushing_tol_inf": _to_float(request.POST.get("inner_bushing_tol_inf"),
                                               values["inner_bushing_tol_inf"]),
            "outer_bushing_nominal": _to_float(request.POST.get("outer_bushing_nominal"),
                                               values["outer_bushing_nominal"]),
            "outer_bushing_tol_sup": _to_float(request.POST.get("outer_bushing_tol_sup"),
                                               values["outer_bushing_tol_sup"]),
            "outer_bushing_tol_inf": _to_float(request.POST.get("outer_bushing_tol_inf"),
                                               values["outer_bushing_tol_inf"]),
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
            tube = GausianDimensionGenerator(
                nominal=values["hole_nominal"],
                tol_sup=values["hole_tol_sup"],
                tol_inf=values["hole_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            inner_bushing = GausianDimensionGenerator(
                nominal=values["inner_bushing_nominal"],
                tol_sup=values["inner_bushing_tol_sup"],
                tol_inf=values["inner_bushing_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            outer_bushing = GausianDimensionGenerator(
                nominal=values["outer_bushing_nominal"],
                tol_sup=values["outer_bushing_tol_sup"],
                tol_inf=values["outer_bushing_tol_inf"],
                CP=values["cp"],
                number_samples=values["samples"],
            )

            interf_tube_bushing = tube - outer_bushing
            wall_thickness = (outer_bushing - inner_bushing) / 2
            system_clearance = tube - pin -(outer_bushing - inner_bushing)

            histogram = Hystogram(
                dimension=interf_tube_bushing,
                bins=50,
                xlabel=_("Diferencia de diametros (mm)"),
                ylabel=_("Densidad"),
                title=_("Histograma de interferencia Tubo Casquillo"),
            )
            hist_interf_tube_bushing_base64 = histogram.plot_to_base64_png()

            histogram = Hystogram(
                dimension=wall_thickness,
                bins=50,
                xlabel=_("Espesor de pared (mm)"),
                ylabel=_("Densidad"),
                title=_("Histograma de espesor de pared"),
            )
            hist_wall_thickness_base64 = histogram.plot_to_base64_png()
            
            histogram = Hystogram(
                dimension=system_clearance,
                bins=50,
                xlabel=_("Juego del sistema (mm)"),
                ylabel=_("Densidad"),
                title=_("Histograma del juego del sistema"),
            )
            hist_system_clearance_base64 = histogram.plot_to_base64_png()


            result = {
                "pin": {
                    "max": _to_magnitude(pin.nominal + pin.tol_sup),
                    "min": _to_magnitude(pin.nominal + pin.tol_inf),
                    "mean": float(pin.mean.magnitude),
                    "sigma": float(pin.sigma.magnitude),
                },
                "hole": {
                    "max": _to_magnitude(tube.nominal + tube.tol_sup),
                    "min": _to_magnitude(tube.nominal + tube.tol_inf),
                    "mean": float(tube.mean.magnitude),
                    "sigma": float(tube.sigma.magnitude),
                },
                "inner_bushing": {
                    "max": _to_magnitude(inner_bushing.nominal + inner_bushing.tol_sup),
                    "min": _to_magnitude(inner_bushing.nominal + inner_bushing.tol_inf),
                    "mean": float(inner_bushing.mean.magnitude),
                    "sigma": float(inner_bushing.sigma.magnitude),
                },
                "outer_bushing": {
                    "max": _to_magnitude(outer_bushing.nominal + outer_bushing.tol_sup),
                    "min": _to_magnitude(outer_bushing.nominal + outer_bushing.tol_inf),
                    "mean": float(outer_bushing.mean.magnitude),
                    "sigma": float(outer_bushing.sigma.magnitude),
                },
                "wall_thickness": {
                    "nominal": _to_magnitude(wall_thickness.nominal),
                    "tol_sup": _to_magnitude(wall_thickness.tol_sup),
                    "tol_inf": _to_magnitude(wall_thickness.tol_inf),
                    "mean_samples": float(wall_thickness.vector_samples.mean()),
                    "sigma_samples": float(wall_thickness.vector_samples.std()),
                    "fit_type": get_fit_type(wall_thickness),
                    "histogram": hist_wall_thickness_base64,
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
                "interf_tube_bushing": {
                    "nominal": _to_magnitude(interf_tube_bushing.nominal),
                    "max_interference": _to_magnitude(interf_tube_bushing.tol_sup + interf_tube_bushing.nominal),
                    "min_interference": _to_magnitude(interf_tube_bushing.tol_inf + interf_tube_bushing.nominal),
                    "mean_samples": float(interf_tube_bushing.vector_samples.mean()),
                    "sigma_samples": float(interf_tube_bushing.vector_samples.std()),
                    "fit_type": get_fit_type(interf_tube_bushing),
                    "histogram": hist_interf_tube_bushing_base64,
                },
            }

        except Exception as exc:
            error = str(exc)
            print(f"Error al calcular tolerancias: {error}")
            print(exc)
    return render(
        request,
        "tolerances/pivot_bushing_hole_radial.html",
        {
            "values": values,
            "result": result,
            "error": error,
        },
    )
