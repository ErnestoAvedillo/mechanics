""" draws an image in the PDF if the file is present,
otherwise it just skips it. This is used to draw the histograms
in the PDF report. """
import io
from django.utils.translation import gettext as _
from reportlab.lib.utils import ImageReader


def _draw_image_if_present(pdf, uploaded_file, x, y, width, height, label):
    if not uploaded_file:
        return

    try:
        image_bytes = uploaded_file.read()
        image_stream = io.BytesIO(image_bytes)
        image = ImageReader(image_stream)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, y + height + 6, label)
        pdf.drawImage(image,
                      x,
                      y,
                      width=width,
                      height=height,
                      preserveAspectRatio=True, mask='auto')
    except Exception:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y + height + 6, f"{label} ({_('no se pudo renderizar')})")
