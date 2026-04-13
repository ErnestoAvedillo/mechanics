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


def pivot_bushing_hole_radial_pdf(request):
    if request.method != "POST":
        return HttpResponse("Usa el formulario de pivot-bushing-hole para generar el PDF.", status=405)

    values = {
        "support_height_nominal": _to_float(request.POST.get("support_height_nominal"), values["support_height_nominal"]),
        "support_height_tol_sup": _to_float(request.POST.get("support_height_tol_sup"), values["support_height_tol_sup"]),
        "support_height_tol_inf": _to_float(request.POST.get("support_height_tol_inf"), values["support_height_tol_inf"]),
        "spacer_height_nominal": _to_float(request.POST.get("spacer_height_nominal"), values["spacer_height_nominal"]),
        "spacer_height_tol_sup": _to_float(request.POST.get("spacer_height_tol_sup"), values["spacer_height_tol_sup"]),
        "spacer_height_tol_inf": _to_float(request.POST.get("spacer_height_tol_inf"), values["spacer_height_tol_inf"]),
        "support_diameter_nominal": _to_float(request.POST.get("support_diameter_nominal"), values["support_diameter_nominal"]),
        "support_diameter_tol_sup": _to_float(request.POST.get("support_diameter_tol_sup"), values["support_diameter_tol_sup"]),
        "support_diameter_tol_inf": _to_float(request.POST.get("support_diameter_tol_inf"), values["support_diameter_tol_inf"]),
        "spacer_diameter_nominal": _to_float(request.POST.get("spacer_diameter_nominal"), values["spacer_diameter_nominal"]),
        "spacer_diameter_tol_sup": _to_float(request.POST.get("spacer_diameter_tol_sup"), values["spacer_diameter_tol_sup"]),
        "spacer_diameter_tol_inf": _to_float(request.POST.get("spacer_diameter_tol_inf"), values["spacer_diameter_tol_inf"]),
        "cp": _to_float(request.POST.get("cp"), values["cp"]),
        "samples": int(_to_float(request.POST.get("samples"), values["samples"])),
    }
    try:
        pin = GausianDimensionGenerator(
            nominal=values["support_height_nominal"],
            tol_sup=values["support_height_tol_sup"],
            tol_inf=values["support_height_tol_inf"],
            CP=values["cp"],
            number_samples=values["samples"],
        )
        hole = GausianDimensionGenerator(
            nominal=values["spacer_height_nominal"],
            tol_sup=values["spacer_height_tol_sup"],
            tol_inf=values["spacer_height_tol_inf"],
            CP=values["cp"],
            number_samples=values["samples"],
        )
        inner_bushing = GausianDimensionGenerator(
            nominal=values["support_diameter_nominal"],
            tol_sup=values["support_diameter_tol_sup"],
            tol_inf=values["support_diameter_tol_inf"],
            CP=values["cp"],
            number_samples=values["samples"],
        )
        outer_bushing = GausianDimensionGenerator(
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
        hist_diameter_interference_b64 = histogram.plot_to_base64_png()
        hist_diameter_interference_bytes = base64.b64decode(hist_diameter_interference_b64)

        histogram = Hystogram(
            dimension=clearance_height,
            bins=50,
            xlabel="Espesor de pared (mm)",
            ylabel="Densidad",
            title="Histograma de espesor de pared",
        )
        hist_clearance_b64 = histogram.plot_to_base64_png()
        hist_clearance_bytes = base64.b64decode(hist_clearance_b64)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="pivot_bushing_hole_radial_report.pdf"'

        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Página 1
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, height - 40, "Reporte de Tolerancia Pivot-Bushing-Hole")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(40, height - 62, f"Cp: {values['cp']:.3f} | Samples: {values['samples']}")

        y = height - 95
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Datos de Entrada")
        y -= 16

        pdf.setFont("Helvetica", 9)
        lines = [
            f"Pin - Nominal: {values['pin_nominal']:.3f} mm | Tol. Sup: {values['pin_tol_sup']:.3f} mm | Tol. Inf: {values['pin_tol_inf']:.3f} mm",
            f"Hole - Nominal: {values['hole_nominal']:.3f} mm | Tol. Sup: {values['hole_tol_sup']:.3f} mm | Tol. Inf: {values['hole_tol_inf']:.3f} mm",
            f"Inner Bushing - Nominal: {values['inner_bushing_nominal']:.3f} mm | Tol. Sup: {values['inner_bushing_tol_sup']:.3f} mm | Tol. Inf: {values['inner_bushing_tol_inf']:.3f} mm",
            f"Outer Bushing - Nominal: {values['outer_bushing_nominal']:.3f} mm | Tol. Sup: {values['outer_bushing_tol_sup']:.3f} mm | Tol. Inf: {values['outer_bushing_tol_inf']:.3f} mm",
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
            f"Support Height - Max: {_to_magnitude(support_height.nominal + support_height.tol_sup):.3f} mm | Min: {_to_magnitude(support_height.nominal + support_height.tol_inf):.3f} mm | Mean: {_to_magnitude(support_height.mean):.3f} mm | Sigma: {_to_magnitude(support_height.sigma):.3f} mm",
            f"Spacer Height - Max: {_to_magnitude(spacer_height.nominal + spacer_height.tol_sup):.3f} mm | Min: {_to_magnitude(spacer_height.nominal + spacer_height.tol_inf):.3f} mm | Mean: {_to_magnitude(spacer_height.mean):.3f} mm | Sigma: {_to_magnitude(spacer_height.sigma):.3f} mm",
            f"Support Diameter - Max: {_to_magnitude(support_diameter.nominal + support_diameter.tol_sup):.3f} mm | Min: {_to_magnitude(support_diameter.nominal + support_diameter.tol_inf):.3f} mm | Mean: {_to_magnitude(support_diameter.mean):.3f} mm | Sigma: {_to_magnitude(support_diameter.sigma):.3f} mm",
            f"Spacer Diameter - Max: {_to_magnitude(spacer_diameter.nominal + spacer_diameter.tol_sup):.3f} mm | Min: {_to_magnitude(spacer_diameter.nominal + spacer_diameter.tol_inf):.3f} mm | Mean: {_to_magnitude(spacer_diameter.mean):.3f} mm | Sigma: {_to_magnitude(spacer_diameter.sigma):.3f} mm",
            "",
            f"Clearance Height - Nominal: {_to_magnitude(clearance_height.nominal):.3f} mm | Tol. Sup: {_to_magnitude(clearance_height.tol_sup):.3f} mm | Tol. Inf: {_to_magnitude(clearance_height.tol_inf):.3f} mm",
            f"Clearance Height - Mean: {clearance_height.vector_samples.mean():.3f} mm | Sigma: {clearance_height.vector_samples.std():.3f} mm",
            "",
            f"Interferencia Casquillo soporte - Nominal: {_to_magnitude(interference_diameter.nominal):.3f} mm",
            f"Interferencia Casquillo soporte - Mean: {interference_diameter.vector_samples.mean():.3f} mm | Sigma: {interference_diameter.vector_samples.std():.3f} mm",
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

        # Histograma 1
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, height - 70, "Interferencia Casquillo soporte")
        hist_stream = io.BytesIO(hist_interf_bytes)
        hist_img = ImageReader(hist_stream)
        pdf.drawImage(
            hist_img,
            40,
            height - 300,
            width=width - 80,
            height=200,
            preserveAspectRatio=True,
            mask='auto',
        )

        # Página 2: Histograma Sistema
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, height - 40, "Histograma Clearance System")

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
