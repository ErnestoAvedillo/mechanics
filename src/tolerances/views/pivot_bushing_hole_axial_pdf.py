import base64
import io

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from tolerances.classes.hystogram import Hystogram
from tolerances.pymodels.dimension import GausianDimensionGenerator


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_magnitude(value):
    try:
        return float(value.magnitude)
    except AttributeError:
        return float(value)


def _draw_image_if_present(pdf, uploaded_file, x, y, width, height, label):
    if not uploaded_file:
        return

    try:
        image_bytes = uploaded_file.read()
        image_stream = io.BytesIO(image_bytes)
        image = ImageReader(image_stream)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, y + height + 6, label)
        pdf.drawImage(image, x, y, width=width, height=height, preserveAspectRatio=True, mask='auto')
    except Exception:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y + height + 6, f"{label} (no se pudo renderizar)")


def pivot_bushing_hole_axial_pdf(request):
    if request.method != "POST":
        return HttpResponse("Usa el formulario de pivot-bushing-hole-axial para generar el PDF.", status=405)

    values = {
        "tube_nominal": _to_float(request.POST.get("tube_nominal"), 0.0),
        "tube_tol_sup": _to_float(request.POST.get("tube_tol_sup"), 0.0),
        "tube_tol_inf": _to_float(request.POST.get("tube_tol_inf"), 0.0),
        "bushing_flange_1_nominal": _to_float(request.POST.get("bushing_flange_1_nominal"), 0.0),
        "bushing_flange_1_tol_sup": _to_float(request.POST.get("bushing_flange_1_tol_sup"), 0.0),
        "bushing_flange_1_tol_inf": _to_float(request.POST.get("bushing_flange_1_tol_inf"), 0.0),
        "bushing_flange_2_nominal": _to_float(request.POST.get("bushing_flange_2_nominal"), 0.0),
        "bushing_flange_2_tol_sup": _to_float(request.POST.get("bushing_flange_2_tol_sup"), 0.0),
        "bushing_flange_2_tol_inf": _to_float(request.POST.get("bushing_flange_2_tol_inf"), 0.0),
        "waal_distance_nominal": _to_float(request.POST.get("waal_distance_nominal"), 0.0),
        "waal_distance_tol_sup": _to_float(request.POST.get("waal_distance_tol_sup"), 0.0),
        "waal_distance_tol_inf": _to_float(request.POST.get("waal_distance_tol_inf"), 0.0),
        "cp": _to_float(request.POST.get("cp"), 1.33),
        "samples": int(_to_float(request.POST.get("samples"), 100000)),
    }

    try:
        tube = GausianDimensionGenerator(
            nominal=values["tube_nominal"],
            tol_sup=values["tube_tol_sup"],
            tol_inf=values["tube_tol_inf"],
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
        waal_distance = GausianDimensionGenerator(
            nominal=values["waal_distance_nominal"],
            tol_sup=values["waal_distance_tol_sup"],
            tol_inf=values["waal_distance_tol_inf"],
            CP=values["cp"],
            number_samples=values["samples"],
        )

        system_clearance = waal_distance - tube - bushing_flange_1 - bushing_flange_2

        histogram = Hystogram(
            dimension=system_clearance,
            bins=50,
            xlabel="Juego del sistema (mm)",
            ylabel="Densidad",
            title="Histograma del juego del sistema",
        )
        hist_system_b64 = histogram.plot_to_base64_png()
        hist_system_bytes = base64.b64decode(hist_system_b64)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="pivot_bushing_hole_axial_report.pdf"'

        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Página 1
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, height - 40, "Reporte de Tolerancia Pivot-Bushing-Waal Axial")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(40, height - 62, f"Cp: {values['cp']:.3f} | Samples: {values['samples']}")

        y = height - 95
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Datos de Entrada")
        y -= 16

        pdf.setFont("Helvetica", 9)
        lines = [
            f"Tube - Nominal: {values['tube_nominal']:.3f} mm | Tol. Sup: {values['tube_tol_sup']:.3f} mm | Tol. Inf: {values['tube_tol_inf']:.3f} mm",
            f"Bushing Flange 1 - Nominal: {values['bushing_flange_1_nominal']:.3f} mm | Tol. Sup: {values['bushing_flange_1_tol_sup']:.3f} mm | Tol. Inf: {values['bushing_flange_1_tol_inf']:.3f} mm",
            f"Bushing Flange 2 - Nominal: {values['bushing_flange_2_nominal']:.3f} mm | Tol. Sup: {values['bushing_flange_2_tol_sup']:.3f} mm | Tol. Inf: {values['bushing_flange_2_tol_inf']:.3f} mm",
            f"Waal Distance - Nominal: {values['waal_distance_nominal']:.3f} mm | Tol. Sup: {values['waal_distance_tol_sup']:.3f} mm | Tol. Inf: {values['waal_distance_tol_inf']:.3f} mm",
        ]

        for line in lines:
            pdf.drawString(40, y, line)
            y -= 12

        y -= 8
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Resultados Calculados")
        y -= 16

        pdf.setFont("Helvetica", 9)
        result_lines = [
            f"Tube - Max: {_to_magnitude(tube.nominal + tube.tol_sup):.3f} mm | Min: {_to_magnitude(tube.nominal + tube.tol_inf):.3f} mm | Mean: {_to_magnitude(tube.mean):.3f} mm | Sigma: {_to_magnitude(tube.sigma):.3f} mm",
            f"Bushing Flange 1 - Max: {_to_magnitude(bushing_flange_1.nominal + bushing_flange_1.tol_sup):.3f} mm | Min: {_to_magnitude(bushing_flange_1.nominal + bushing_flange_1.tol_inf):.3f} mm | Mean: {_to_magnitude(bushing_flange_1.mean):.3f} mm | Sigma: {_to_magnitude(bushing_flange_1.sigma):.3f} mm",
            f"Bushing Flange 2 - Max: {_to_magnitude(bushing_flange_2.nominal + bushing_flange_2.tol_sup):.3f} mm | Min: {_to_magnitude(bushing_flange_2.nominal + bushing_flange_2.tol_inf):.3f} mm | Mean: {_to_magnitude(bushing_flange_2.mean):.3f} mm | Sigma: {_to_magnitude(bushing_flange_2.sigma):.3f} mm",
            f"Waal Distance - Max: {_to_magnitude(waal_distance.nominal + waal_distance.tol_sup):.3f} mm | Min: {_to_magnitude(waal_distance.nominal + waal_distance.tol_inf):.3f} mm | Mean: {_to_magnitude(waal_distance.mean):.3f} mm | Sigma: {_to_magnitude(waal_distance.sigma):.3f} mm",
            "",
            f"System Clearance - Nominal: {_to_magnitude(system_clearance.nominal):.3f} mm | Tol. Sup: {_to_magnitude(system_clearance.tol_sup):.3f} mm | Tol. Inf: {_to_magnitude(system_clearance.tol_inf):.3f} mm",
            f"System Clearance - Mean: {system_clearance.vector_samples.mean():.3f} mm | Sigma: {system_clearance.vector_samples.std():.3f} mm",
            f"System Clearance - Sigma: {system_clearance.vector_samples.std():.3f} mm | Sigma: {system_clearance.vector_samples.std():.3f} mm",

        ]

        for line in result_lines:
            pdf.drawString(40, y, line)
            y -= 12

        y -= 8
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, "Imagenes adjuntas")

        image_1 = request.FILES.get("image_1")
        image_2 = request.FILES.get("image_2")

        image_width = (width - 120) / 2
        image_height = 100
        image_y = y - 120

        _draw_image_if_present(pdf, image_1, 40, image_y, image_width, image_height, "Imagen 1")
        _draw_image_if_present(pdf, image_2, 40 + image_width + 40, image_y, image_width, image_height, "Imagen 2")

        # Página 2: Histogramas
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, height - 40, "Histogramas")


        # Página 3: Histograma Sistema
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, height - 40, "Histograma del Sistema")

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, height - 70, "Juego del Sistema")
        hist_stream = io.BytesIO(hist_system_bytes)
        hist_img = ImageReader(hist_stream)
        pdf.drawImage(
            hist_img,
            40,
            height - 400,
            width=width - 80,
            height=300,
            preserveAspectRatio=True,
            mask='auto',
        )

        pdf.showPage()
        pdf.save()
        return response

    except Exception as exc:
        return HttpResponse(f"Error al generar PDF: {str(exc)}", status=500)
