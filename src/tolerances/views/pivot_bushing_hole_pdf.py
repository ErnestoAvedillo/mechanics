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


def pivot_bushing_hole_pdf(request):
    if request.method != "POST":
        return HttpResponse("Usa el formulario de pivot-bushing-hole para generar el PDF.", status=405)

    values = {
        "pin_nominal": _to_float(request.POST.get("pin_nominal"), 0.0),
        "pin_tol_sup": _to_float(request.POST.get("pin_tol_sup"), 0.0),
        "pin_tol_inf": _to_float(request.POST.get("pin_tol_inf"), 0.0),
        "hole_nominal": _to_float(request.POST.get("hole_nominal"), 0.0),
        "hole_tol_sup": _to_float(request.POST.get("hole_tol_sup"), 0.0),
        "hole_tol_inf": _to_float(request.POST.get("hole_tol_inf"), 0.0),
        "inner_bushing_nominal": _to_float(request.POST.get("inner_bushing_nominal"), 0.0),
        "inner_bushing_tol_sup": _to_float(request.POST.get("inner_bushing_tol_sup"), 0.0),
        "inner_bushing_tol_inf": _to_float(request.POST.get("inner_bushing_tol_inf"), 0.0),
        "outer_bushing_nominal": _to_float(request.POST.get("outer_bushing_nominal"), 0.0),
        "outer_bushing_tol_sup": _to_float(request.POST.get("outer_bushing_tol_sup"), 0.0),
        "outer_bushing_tol_inf": _to_float(request.POST.get("outer_bushing_tol_inf"), 0.0),
        "cp": _to_float(request.POST.get("cp"), 1.33),
        "samples": int(_to_float(request.POST.get("samples"), 100000)),
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

        interf_tube_bushing = hole - inner_bushing
        wall_thickness = (outer_bushing - inner_bushing) / 2
        system_clearance = hole - pin - (outer_bushing - inner_bushing)

        # Generar histogramas
        histogram = Hystogram(
            dimension=interf_tube_bushing,
            bins=50,
            xlabel="Interferencia Tubo-Casquillo (mm)",
            ylabel="Densidad",
            title="Histograma de Interferencia Tubo-Casquillo",
        )
        hist_interf_b64 = histogram.plot_to_base64_png()
        hist_interf_bytes = base64.b64decode(hist_interf_b64)

        histogram = Hystogram(
            dimension=wall_thickness,
            bins=50,
            xlabel="Espesor de pared (mm)",
            ylabel="Densidad",
            title="Histograma de espesor de pared",
        )
        hist_wall_b64 = histogram.plot_to_base64_png()
        hist_wall_bytes = base64.b64decode(hist_wall_b64)

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
        response["Content-Disposition"] = 'attachment; filename="pivot_bushing_hole_report.pdf"'

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
            f"Pin - Max: {_to_magnitude(pin.nominal + pin.tol_sup):.3f} mm | Min: {_to_magnitude(pin.nominal + pin.tol_inf):.3f} mm | Mean: {_to_magnitude(pin.mean):.3f} mm | Sigma: {_to_magnitude(pin.sigma):.3f} mm",
            f"Hole - Max: {_to_magnitude(hole.nominal + hole.tol_sup):.3f} mm | Min: {_to_magnitude(hole.nominal + hole.tol_inf):.3f} mm | Mean: {_to_magnitude(hole.mean):.3f} mm | Sigma: {_to_magnitude(hole.sigma):.3f} mm",
            f"Inner Bushing - Max: {_to_magnitude(inner_bushing.nominal + inner_bushing.tol_sup):.3f} mm | Min: {_to_magnitude(inner_bushing.nominal + inner_bushing.tol_inf):.3f} mm | Mean: {_to_magnitude(inner_bushing.mean):.3f} mm | Sigma: {_to_magnitude(inner_bushing.sigma):.3f} mm",
            f"Outer Bushing - Max: {_to_magnitude(outer_bushing.nominal + outer_bushing.tol_sup):.3f} mm | Min: {_to_magnitude(outer_bushing.nominal + outer_bushing.tol_inf):.3f} mm | Mean: {_to_magnitude(outer_bushing.mean):.3f} mm | Sigma: {_to_magnitude(outer_bushing.sigma):.3f} mm",
            "",
            f"Wall Thickness - Nominal: {_to_magnitude(wall_thickness.nominal):.3f} mm | Tol. Sup: {_to_magnitude(wall_thickness.tol_sup):.3f} mm | Tol. Inf: {_to_magnitude(wall_thickness.tol_inf):.3f} mm",
            f"Wall Thickness - Mean: {wall_thickness.vector_samples.mean():.3f} mm | Sigma: {wall_thickness.vector_samples.std():.3f} mm",
            "",
            f"System Clearance - Nominal: {_to_magnitude(system_clearance.nominal):.3f} mm | Tol. Sup: {_to_magnitude(system_clearance.tol_sup):.3f} mm | Tol. Inf: {_to_magnitude(system_clearance.tol_inf):.3f} mm",
            f"System Clearance - Mean: {system_clearance.vector_samples.mean():.3f} mm | Sigma: {system_clearance.vector_samples.std():.3f} mm",
            "",
            f"Interf. Tube-Bushing - Nominal: {_to_magnitude(interf_tube_bushing.nominal):.3f} mm",
            f"Interf. Tube-Bushing - Mean: {interf_tube_bushing.vector_samples.mean():.3f} mm | Sigma: {interf_tube_bushing.vector_samples.std():.3f} mm",
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
        pdf.drawString(40, height - 70, "Interferencia Tubo-Casquillo")
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

        # Histograma 2
        pdf.drawString(40, height - 330, "Espesor de Pared")
        hist_stream = io.BytesIO(hist_wall_bytes)
        hist_img = ImageReader(hist_stream)
        pdf.drawImage(
            hist_img,
            40,
            height - 560,
            width=width - 80,
            height=200,
            preserveAspectRatio=True,
            mask='auto',
        )

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
