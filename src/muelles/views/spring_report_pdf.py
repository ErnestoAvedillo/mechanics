"""Generates the PDF report for a spring calculator from the same
`resultado` dictionary already used to render the results page
(_calculadora_results.html), avoiding repeating the calculation.

Different calculators build `resultado` with different field names (some in
Spanish, torsion reuses the English names from the springcalc model), so
each field is looked up through a list of candidate keys, the same way the
template does with `{% firstof %}`.
"""
import base64
import io

from django.http import HttpResponse
from django.utils.translation import gettext as _
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _fields():
    return [
        (_("Material"), ("material_nombre", "material")),
        (_("Modulo G"), ("modulo_corte", "shear_modulus")),
        (_("Modulo E"), ("modulo_young", "young_modulus")),
        (_("Diametro hilo"), ("diametro_hilo", "wire_diameter")),
        (_("Shot peening"), ("shot_peening",)),
        (_("Diametro medio"), ("diametro_medio", "mean_diameter")),
        (_("Diametro medio superior"), ("diametro_medio_superior",)),
        (_("Diametro medio inferior"), ("diametro_medio_inferior",)),
        (_("Diametro exterior"), ("diametro_exterior", "outer_diameter")),
        (_("Diametro interior"), ("diametro_interior", "inner_diameter")),
        (_("Longitud libre"), ("longitud_libre", "free_length")),
        (_("Longitud hilo"), ("longitud_hilo", "wire_length")),
        (_("Longitud hilo total"), ("longitud_hilo_total", "wire_length_total")),
        (_("Longitud hilo cuerpo"), ("longitud_hilo_cuerpo", "body_wire_length")),
        (_("Numero espiras"), ("numero_espiras", "nr_coils")),
        (_("Numero espiras utiles"), ("numero_espiras_utiles", "nr_active_coils")),
        (_("Pitch"), ("pitch",)),
        (_("Tramo 1 - espiras"), ("numero_espiras_1",)),
        (_("Tramo 1 - paso"), ("pitch_1",)),
        (_("Tramo 2 - espiras"), ("numero_espiras_2",)),
        (_("Tramo 2 - paso"), ("pitch_2",)),
        (_("Tramo 3 - espiras"), ("numero_espiras_3",)),
        (_("Tramo 3 - paso"), ("pitch_3",)),
        (_("Ancho muelle"), ("ancho_muelle", "spring_width")),
        (_("Longitud bloqueo"), ("longitud_bloqueo", "solid_length")),
        (_("Angulo libre"), ("angulo_libre", "free_angle")),
        (_("Angulo tangencias"), ("angulo_tangencias", "tangency_angle")),
        (_("Constante"), ("constante_muelle", "spring_constant")),
        (_("Constante K1"), ("constante_muelle_1",)),
        (_("Constante K2"), ("constante_muelle_2",)),
        (_("Indice muelle"), ("indice_muelle", "spring_index")),
        (_("Factor Wahl"), ("factor_wahl", "wahl_factor")),
        (_("Factor Wahl eval"), ("factor_wahl_eval", "wahl_factor_eval")),
        (_("Categoria Wahl"), ("factor_wahl_category", "wahl_factor_category")),
        (_("Tension inicial"), ("tension_inicial", "initial_stress")),
        (_("Momento resistente"), ("momento_resistente", "resisting_moment")),
        (_("Radio pata fija"), ("radious_leg_fija", "fixed_leg_radius")),
        (_("Longitud pata fija"), ("long_leg_fija", "fixed_leg_length")),
        (_("Radio pata movil"), ("radious_leg_movil", "mobile_leg_radius")),
        (_("Longitud pata movil"), ("long_leg_movil", "mobile_leg_length")),
        (_("Numero de ciclos"), ("numero_ciclos", "number_cycles")),
    ]


def _image_sections():
    return [
        (_("Curva de Esfuerzos"), "curva_esfuerzos", "imagen"),
        (_("Curva de Recorrido"), "curva_recorrido", "imagen"),
        (_("Curva de Diametros"), "curva_diametros", "imagen"),
        (_("Curva de Compresion Progresiva (2K)"), "curva_progresiva", "imagen"),
        (_("Diagrama de Goodman"), "diagrama_goodman", "image"),
    ]


def _first_value(resultado, keys):
    for key in keys:
        value = resultado.get(key)
        if value not in (None, ""):
            return value
    return None


def _format_value(value):
    if isinstance(value, bool):
        return _("Si") if value else _("No")
    return str(value)


def build_spring_report_pdf_response(titulo, resultado, filename):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, titulo)

    if resultado.get("error"):
        pdf.setFont("Helvetica", 11)
        pdf.drawString(40, height - 70, _("Error en los calculos:"))
        text_obj = pdf.beginText(40, height - 88)
        text_obj.setFont("Helvetica", 9)
        for line in str(resultado["error"]).splitlines() or [""]:
            text_obj.textLine(line[:110])
        pdf.drawText(text_obj)
        pdf.showPage()
        pdf.save()
        return response

    y = height - 70
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, _("Resultados"))
    y -= 18

    pdf.setFont("Helvetica", 9)
    for label, keys in _fields():
        value = _first_value(resultado, keys)
        if value is None:
            continue
        pdf.drawString(40, y, f"{label}: {_format_value(value)}"[:110])
        y -= 13
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = height - 60

    for title, section_key, image_key in _image_sections():
        section = resultado.get(section_key) or {}
        image_b64 = section.get(image_key)
        if not image_b64:
            continue
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(40, height - 40, title)
        if not isinstance(image_b64, str):
            continue
        image_stream = io.BytesIO(base64.b64decode(image_b64))
        image = ImageReader(image_stream)
        pdf.drawImage(
            image,
            40,
            60,
            width=width - 80,
            height=height - 140,
            preserveAspectRatio=True,
            mask="auto",
        )

    pdf.showPage()
    pdf.save()
    return response
