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


def pin_hole_pdf(request):
    if request.method != "POST":
        return HttpResponse("Usa el formulario de pin-hole para generar el PDF.", status=405)

    values = {
        "pin_nominal": _to_float(request.POST.get("pin_nominal"), 0.0),
        "pin_tol_sup": _to_float(request.POST.get("pin_tol_sup"), 0.0),
        "pin_tol_inf": _to_float(request.POST.get("pin_tol_inf"), 0.0),
        "outer_bushing_nominal": _to_float(request.POST.get("outer_bushing_nominal"), 0.0),
        "outer_bushing_tol_sup": _to_float(request.POST.get("outer_bushing_tol_sup"), 0.0),
        "outer_bushing_tol_inf": _to_float(request.POST.get("outer_bushing_tol_inf"), 0.0),
        "inner_bushing_nominal": _to_float(request.POST.get("inner_bushing_nominal"), 0.0),
        "inner_bushing_tol_sup": _to_float(request.POST.get("inner_bushing_tol_sup"), 0.0),
        "inner_bushing_tol_inf": _to_float(request.POST.get("inner_bushing_tol_inf"), 0.0),
        "hole_nominal": _to_float(request.POST.get("hole_nominal"), 0.0),
        "hole_tol_sup": _to_float(request.POST.get("hole_tol_sup"), 0.0),
        "hole_tol_inf": _to_float(request.POST.get("hole_tol_inf"), 0.0),
        "cp": _to_float(request.POST.get("cp"), 1.33),
        "samples": int(_to_float(request.POST.get("samples"), 100000)),
    }

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
    gap = (hole - pin) - (outer_bushing - inner_bushing)

    max_pin = values["pin_nominal"] + values["pin_tol_sup"]
    min_pin = values["pin_nominal"] + values["pin_tol_inf"]
    max_hole = values["hole_nominal"] + values["hole_tol_sup"]
    min_hole = values["hole_nominal"] + values["hole_tol_inf"]
    max_inner_bushing = values["inner_bushing_nominal"] + values["inner_bushing_tol_sup"]
    min_inner_bushing = values["inner_bushing_nominal"] + values["inner_bushing_tol_inf"]
    max_outer_bushing = values["outer_bushing_nominal"] + values["outer_bushing_tol_sup"]
    min_outer_bushing = values["outer_bushing_nominal"] + values["outer_bushing_tol_inf"]
    max_clearance = gap.mean.magnitude + 4 * gap.sigma.magnitude
    min_clearance = gap.mean.magnitude - 4 * gap.sigma.magnitude

    if max_clearance < 0 and min_clearance < 0:
        fit_type = "Apriete (Interference fit)"
    elif max_clearance > 0 and min_clearance > 0:
        fit_type = "Juego (Clearance fit)"
    else:
        fit_type = "Transicion (Transition fit)"

    histogram = Hystogram(
        dimension=gap,
        bins=50,
        xlabel="Diferencia de diametros (mm)",
        ylabel="Densidad",
        title="Histograma de (Agujero - Pin)",
    )
    histogram_b64 = histogram.plot_to_base64_png()
    histogram_bytes = base64.b64decode(histogram_b64)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="pin_hole_report.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, "Reporte de Tolerancia Pin-Hole")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, height - 62, f"Cp: {values['cp']:.3f} | Samples: {values['samples']}")

    y = height - 95
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Resultados")
    y -= 16

    pdf.setFont("Helvetica", 10)
    lines = [
        f"Pin - Max: {max_pin:.3f} mm | Min: {min_pin:.3f} mm | Mean: {pin.mean.magnitude:.3f} mm | Sigma: {pin.sigma.magnitude:.3f} mm",
        f"Hole - Max: {max_hole:.3f} mm | Min: {min_hole:.3f} mm | Mean: {hole.mean.magnitude:.3f} mm | Sigma: {hole.sigma.magnitude:.3f} mm",
        f"Inner Bushing - Max: {max_inner_bushing:.3f} mm | Min: {min_inner_bushing:.3f} mm | Mean: {inner_bushing.mean.magnitude:.3f} mm | Sigma: {inner_bushing.sigma.magnitude:.3f} mm",
        f"Outer Bushing - Max: {max_outer_bushing:.3f} mm | Min: {min_outer_bushing:.3f} mm | Mean: {outer_bushing.mean.magnitude:.3f} mm | Sigma: {outer_bushing.sigma.magnitude:.3f} mm",
        f"Ajuste: {fit_type}",
        f"Holgura maxima: {max_clearance:.3f} mm | Holgura minima: {min_clearance:.3f} mm",
        f"Gap samples - Mean: {gap.vector_samples.mean():.3f} mm | Sigma: {gap.vector_samples.std():.3f} mm",
    ]

    for line in lines:
        pdf.drawString(40, y, line)
        y -= 14

    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Imagenes adjuntas")

    image_1 = request.FILES.get("image_1")
    image_2 = request.FILES.get("image_2")

    image_width = (width - 120) / 2
    image_height = 120
    image_y = y - 130

    _draw_image_if_present(pdf, image_1, 40, image_y, image_width, image_height, "Imagen 1")
    _draw_image_if_present(pdf, image_2, 40 + image_width + 40, image_y, image_width, image_height, "Imagen 2")

    hist_title_y = image_y - 20
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, hist_title_y, "Histograma (Agujero - Pin)")

    hist_stream = io.BytesIO(histogram_bytes)
    hist_img = ImageReader(hist_stream)
    pdf.drawImage(
        hist_img,
        40,
        60,
        width=width - 80,
        height=hist_title_y - 80,
        preserveAspectRatio=True,
        mask='auto',
    )

    pdf.showPage()
    pdf.save()
    return response
