import io
import mimetypes
import zipfile
from pathlib import Path

from django.core.paginator import Paginator
from django.http import HttpResponse, Http404, FileResponse
from django.shortcuts import render, redirect

from pyreqif import Reqif

from . import storage

# Nº de requisitos por página del editor. Cada fila manda 3 campos al
# guardar (id, comentario, estado); documentos reales pueden tener 800+
# requisitos, y en un único POST superarían DATA_UPLOAD_MAX_NUMBER_FIELDS.
PAGE_SIZE = 200


def _get_session_workdir(request):
    session_id = request.session.get('reqif_session_id')
    if not session_id:
        return None, None
    work_dir = storage.session_dir(session_id)
    if not work_dir.exists():
        return None, None
    return session_id, work_dir


def _edit_page_context(request, index, doc_name, reqif_path, **extra):
    doc = Reqif(reqif_path)
    paginator = Paginator(doc.requirements, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'index': index,
        'doc_name': doc_name,
        'requirements': page_obj.object_list,
        'page_obj': page_obj,
        'page_size': PAGE_SIZE,
        'status_options': doc.status_options,
    }
    context.update(extra)
    return context


def upload_view(request):
    if request.method == 'POST' and request.FILES.get('reqifz_file'):
        uploaded = request.FILES['reqifz_file']
        suffix = Path(uploaded.name).suffix.lower()
        _session_id, work_dir = storage.new_session_dir()

        if suffix == '.reqif':
            # Fichero .reqif suelto: se guarda tal cual, sin descomprimir.
            reqif_files = storage.save_plain_reqif(uploaded, work_dir)
            original_kind = 'reqif'
        else:
            try:
                reqif_files = storage.extract_reqifz(uploaded, work_dir)
            except zipfile.BadZipFile:
                return render(request, 'reqif/upload.html', {
                    'error': 'El fichero no es un .reqifz/.zip ni un .reqif válido.',
                })

            if not reqif_files:
                return render(request, 'reqif/upload.html', {
                    'error': 'No se ha encontrado ningún fichero .reqif dentro del archivo subido.',
                })
            original_kind = 'reqifz'

        request.session['reqif_session_id'] = work_dir.name
        request.session['reqif_files'] = reqif_files
        request.session['reqif_original_name'] = uploaded.name
        request.session['reqif_original_kind'] = original_kind
        return redirect('reqif:documents')

    return render(request, 'reqif/upload.html')


def documents_view(request):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        return redirect('reqif:upload')

    reqif_files = request.session.get('reqif_files', [])
    docs = [
        {
            'index': idx,
            'name': Path(rel_path).name,
            'count': len(Reqif(work_dir / rel_path)),
        }
        for idx, rel_path in enumerate(reqif_files)
    ]
    return render(request, 'reqif/documents.html', {'docs': docs})


def edit_document_view(request, index):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        return redirect('reqif:upload')

    reqif_files = request.session.get('reqif_files', [])
    if index < 0 or index >= len(reqif_files):
        raise Http404('Documento no encontrado en esta sesión')

    reqif_path = work_dir / reqif_files[index]
    saved = False

    if request.method == 'POST':
        doc = Reqif(reqif_path)
        updates = [
            (
                req_id,
                request.POST.get(f'comment_{req_id}', ''),
                request.POST.get(f'status_{req_id}', ''),
            )
            for req_id in request.POST.getlist('requirement_id')
        ]
        doc.update_many(updates)
        doc.save()
        saved = True

    context = _edit_page_context(request, index, Path(reqif_files[index]).name, reqif_path, saved=saved)
    return render(request, 'reqif/edit.html', context)


def export_excel_view(request, index):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        return redirect('reqif:upload')

    reqif_files = request.session.get('reqif_files', [])
    if index < 0 or index >= len(reqif_files):
        raise Http404('Documento no encontrado en esta sesión')

    reqif_path = work_dir / reqif_files[index]
    doc = Reqif(reqif_path)
    buffer = io.BytesIO()
    doc.to_excel(buffer, image_resolver=lambda rel_path: work_dir / rel_path)
    buffer.seek(0)

    download_name = Path(reqif_files[index]).stem + '.xlsx'
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    return response


def import_excel_view(request, index):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        return redirect('reqif:upload')

    reqif_files = request.session.get('reqif_files', [])
    if index < 0 or index >= len(reqif_files):
        raise Http404('Documento no encontrado en esta sesión')

    reqif_path = work_dir / reqif_files[index]
    excel_error = None
    excel_updated = None

    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            doc = Reqif(reqif_path)
            excel_updated = doc.update_from_excel(request.FILES['excel_file'])
            doc.save()
        except Exception:
            excel_error = (
                'No se ha podido leer el Excel. Comprueba que es el mismo fichero '
                'descargado desde aquí y que no has cambiado sus columnas.'
            )

    context = _edit_page_context(
        request, index, Path(reqif_files[index]).name, reqif_path,
        excel_error=excel_error, excel_updated=excel_updated,
    )
    return render(request, 'reqif/edit.html', context)


def download_view(request):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        return redirect('reqif:upload')

    original_name = request.session.get('reqif_original_name', 'documento.reqifz')
    original_kind = request.session.get('reqif_original_kind', 'reqifz')

    if original_kind == 'reqif':
        reqif_files = request.session.get('reqif_files', [])
        if not reqif_files:
            raise Http404('No hay ningún fichero .reqif en esta sesión')

        reqif_path = work_dir / reqif_files[0]
        download_name = Path(original_name).stem + '_editado.reqif'
        response = HttpResponse(reqif_path.read_bytes(), content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{download_name}"'
        return response

    buffer = io.BytesIO()
    storage.rezip(work_dir, buffer)
    buffer.seek(0)

    download_name = Path(original_name).stem + '_editado.reqifz'
    response = HttpResponse(buffer.getvalue(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    return response


def attachment_view(request, rel_path):
    _session_id, work_dir = _get_session_workdir(request)
    if work_dir is None:
        raise Http404('No hay ninguna sesión activa')

    work_dir = work_dir.resolve()
    target = (work_dir / rel_path).resolve()
    try:
        target.relative_to(work_dir)
    except ValueError:
        raise Http404('Ruta no válida')

    if not target.is_file():
        raise Http404('Fichero no encontrado')

    content_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(open(target, 'rb'), content_type=content_type or 'application/octet-stream')
