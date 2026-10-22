"""
Files attached to a chat question (a bill of requirements, a drawing...).

They are read once, for that question only: nothing is stored or indexed. Text-based files are
turned into text locally; a drawing (image) is described by a vision model, because the text LLM
cannot see images.
"""
import base64
import io
import logging
import os

from django.conf import settings
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
# What reaches the LLM prompt; the rest of a very long file is cut (and the user is told)
MAX_ATTACHMENT_CHARS = 30000

TEXT_EXTENSIONS = {'.txt', '.md', '.csv'}
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
ACCEPTED_EXTENSIONS = {'.pdf'} | TEXT_EXTENSIONS | set(IMAGE_TYPES)

_DRAWING_PROMPT = (
    "You are reading an engineering drawing. Transcribe everything that specifies the part: title "
    "block, material, standards and specification numbers, dimensions, tolerances, surface finish, "
    "coatings, heat treatment, notes and revisions, and also describe the geometry shown. Use the "
    "drawing's own wording and units. Do not invent anything that is not visible; write "
    "[illegible] where you cannot read something."
)


class AttachmentError(Exception):
    """The attached file cannot be used; the message is already translated for the user."""


def read_attachment(uploaded_file):
    """
    Returns (text, truncated) for an uploaded file, or raises AttachmentError.
    `truncated` is True when the text was cut to MAX_ATTACHMENT_CHARS.
    """
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ACCEPTED_EXTENSIONS:
        raise AttachmentError(_('Formato no admitido. Adjunta un PDF, una imagen (PNG, JPG, WEBP) o un archivo de texto.'))
    if uploaded_file.size > MAX_ATTACHMENT_BYTES:
        raise AttachmentError(_('El archivo es demasiado grande (máximo %(mb)s MB).')
                              % {'mb': MAX_ATTACHMENT_BYTES // (1024 * 1024)})
    data = uploaded_file.read()

    if extension == '.pdf':
        text = _pdf_text(data)
    elif extension in TEXT_EXTENSIONS:
        text = data.decode('utf-8', errors='replace')
    else:
        text = _describe_drawing(data, IMAGE_TYPES[extension])

    text = text.strip()
    if not text:
        raise AttachmentError(_('No se ha podido extraer texto del archivo adjunto.'))
    return text[:MAX_ATTACHMENT_CHARS], len(text) > MAX_ATTACHMENT_CHARS


def _pdf_text(data):
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n\n".join(page.extract_text() or '' for page in reader.pages)
    except Exception:
        logger.exception("Could not read the attached PDF")
        raise AttachmentError(_('No se ha podido leer el PDF adjunto.'))
    if not text.strip():
        # Scanned PDFs have no text layer; they would need OCR
        raise AttachmentError(_('El PDF adjunto no contiene texto (¿es un escaneo?). Adjúntalo como imagen.'))
    return text


def _describe_drawing(data, mime_type):
    from openai import OpenAI
    image_url = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
    try:
        client = OpenAI(base_url=settings.NEBIUS_BASE_URL, api_key=settings.NEBIUS_API_KEY)
        completion = client.chat.completions.create(
            model=settings.NEBIUS_VISION_MODEL,
            messages=[{'role': 'user', 'content': [
                {'type': 'text', 'text': _DRAWING_PROMPT},
                {'type': 'image_url', 'image_url': {'url': image_url}},
            ]}],
        )
        return completion.choices[0].message.content or ''
    except Exception:
        logger.exception("Could not read the attached drawing")
        raise AttachmentError(_('No se ha podido analizar la imagen adjunta.'))
