"""Gestión de directorios de trabajo por sesión y de los ficheros
.reqif/.reqifz subidos. Toda la lógica de lectura/edición de ReqIF en sí
vive en la librería `pyreqif`; este módulo solo mueve bytes de sitio.
"""
import uuid
import zipfile
from pathlib import Path

from django.conf import settings

WORKDIR_ROOT = Path(settings.PROJECT_ROOT) / 'reqif_workdir'


def new_session_dir():
    session_id = uuid.uuid4().hex
    work_dir = WORKDIR_ROOT / session_id
    work_dir.mkdir(parents=True, exist_ok=True)
    return session_id, work_dir


def session_dir(session_id):
    return WORKDIR_ROOT / session_id


def extract_reqifz(uploaded_file, dest_dir):
    """Extrae el .reqifz subido en dest_dir. Devuelve las rutas (relativas
    a dest_dir) de los ficheros .reqif encontrados dentro, ordenadas."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / '_upload.zip'
    with open(zip_path, 'wb') as fh:
        for chunk in uploaded_file.chunks():
            fh.write(chunk)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()

    return sorted(
        str(p.relative_to(dest_dir)) for p in dest_dir.rglob('*.reqif')
    )


def save_plain_reqif(uploaded_file, dest_dir):
    """Guarda un .reqif suelto (sin comprimir) tal cual en dest_dir.
    Devuelve una lista con su único nombre de fichero."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(uploaded_file.name).name
    dest_path = dest_dir / filename
    with open(dest_path, 'wb') as fh:
        for chunk in uploaded_file.chunks():
            fh.write(chunk)
    return [filename]


def rezip(work_dir, out_stream):
    """Reempaqueta el contenido de work_dir en out_stream (un fichero o
    BytesIO), como .reqifz."""
    with zipfile.ZipFile(out_stream, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(work_dir.rglob('*')):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(work_dir))
