import hashlib
import logging
import re
import threading
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _, get_language
from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs
from .models import Document, UserDocument
from .forms import DocumentUploadForm, MetadataReviewForm
from .rag_engine import DOC_KEY, get_rag_engine, delete_document_vectors, extract_spring_design_block
from .tasks import process_document_task
from .versions import DUPLICATE, SEARCHED, SUPERSEDED, TRANSLATION, TRANSLATION_ONLY, library_state

logger = logging.getLogger(__name__)

SPRING_DESIGN_FENCE_RE = re.compile(r"```(?:spring-design)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)
SPRING_DESIGN_NUMERIC_FIELDS = {
    'diametro_hilo', 'diametro_exterior', 'diametro_medio', 'diametro_interior',
    'numero_espiras', 'longitud_libre', 'longitud_inicial', 'longitud_final',
}
SPRING_DESIGN_CHOICE_FIELDS = {
    'numero_ciclos': {'1e3', '1e4', '1e5', '1e6', '1e7'},
    'tipo_final': {'abierto', 'cerrado', 'semi-cerrado', 'rectificado'},
}


def _build_spring_link(block_text):
    """
    Turns the raw `key=value` text from rag_engine.extract_spring_design_block (optionally still
    fenced) into a link that opens the compression calculator with those fields prefilled.
    Returns None when nothing usable survives validation.
    """
    if not block_text:
        return None
    fence_match = SPRING_DESIGN_FENCE_RE.search(block_text)
    body = fence_match.group(1) if fence_match else block_text

    params = {}
    for line in body.splitlines():
        if '=' not in line:
            continue
        key, _unused, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if key in SPRING_DESIGN_NUMERIC_FIELDS:
            try:
                params[key] = f"{float(value.replace(',', '.')):g}"
            except ValueError:
                continue
        elif key in SPRING_DESIGN_CHOICE_FIELDS and value in SPRING_DESIGN_CHOICE_FIELDS[key]:
            params[key] = value
        elif key == 'material' and re.fullmatch(r'[A-Za-z0-9_-]{1,20}', value):
            params[key] = value

    if not params:
        return None
    return reverse('muelles_calculadora_compresion') + '?' + urlencode(params)


def _gridfs():
    """GridFS handle on the project's MongoDB database."""
    return gridfs.GridFS(MongoClient(settings.MONGO_URL)[settings.MONGO_DB_NAME])


def purge_document(document):
    """
    Removes a Document that nobody has access to any more: its vectors, its PDF and its row.
    Each step is logged on failure instead of raised, so deleting a user's access never fails
    because of cleanup; leftovers are orphans that do not affect anyone.
    """
    try:
        delete_document_vectors(document.pk)
    except Exception:
        logger.exception("Could not delete the vectors of document %s", document.pk)
    try:
        _gridfs().delete(ObjectId(document.mongo_id))
    except Exception:
        logger.exception("Could not delete the PDF of document %s", document.pk)
    document.delete()


def index(request):
    """Redirects to the main specs page."""
    return render(request, 'specs/index.html')

@login_required
def document_list(request):
    """List of documents uploaded by the user."""
    documents = list(UserDocument.objects.filter(user=request.user).select_related('document').order_by('-upload_date'))
    states = library_state(request.user.id)
    by_id = {entry.document_id: entry.document for entry in documents if entry.document_id}
    for entry in documents:
        state = states.get(entry.document_id)
        entry.library_label = _library_label(state, by_id.get(state.by)) if state else ''
        entry.library_hidden = bool(state) and state.state not in SEARCHED
    return render(request, 'specs/document_list.html', {'documents': documents})


def _short_name(document):
    """'VW TL 245 (2025-12, de)' - how a document is referred to in labels."""
    detail = ", ".join(part for part in (
        document.edition_date.strftime('%Y-%m') if document.edition_date else '', document.language) if part)
    return f"{document.spec_issuer} {document.spec_number}" + (f" ({detail})" if detail else "")


def _library_label(state, replacement):
    """Why a document is, or is not, used by the chat; empty when nothing needs saying."""
    by = _short_name(replacement) if replacement else ''
    if state.state == SUPERSEDED:
        return _('Obsoleta: sustituida por %(by)s') % {'by': by}
    if state.state == TRANSLATION:
        return _('Traducción: el chat usa el original %(by)s') % {'by': by}
    if state.state == DUPLICATE:
        return _('Posible duplicado de %(by)s') % {'by': by}
    if state.state == TRANSLATION_ONLY:
        return _('Solo traducción: el original puede prevalecer')
    return ''

@login_required
def document_view(request, doc_id):
    """Serves a PDF document from MongoDB using GridFS."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    
    try:
        # Connect to MongoDB and retrieve the file
        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        
        # Convert mongo_id to ObjectId (legacy rows without a linked Document use their own id)
        mongo_id = ObjectId(doc.document.mongo_id if doc.document_id else doc.mongo_id)
        
        # Get the file
        grid_out = fs.get(mongo_id)
        pdf_content = grid_out.read()
        
        # Create the HTTP response with the PDF
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{doc.filename}"'
        
        return response
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, _('Error al recuperar el documento: %(error)s') % {'error': str(e)})
        return redirect('specs:handling')

@login_required
def document_review(request, doc_id):
    """
    Shows the metadata of the standard proposed by the LLM. Only the uploader can correct and
    confirm it; the other users with access see it read-only.
    """
    entry = get_object_or_404(UserDocument.objects.select_related('document'), id=doc_id, user=request.user)
    document = entry.document
    if document is None:
        return redirect('specs:handling')
    can_edit = document.can_be_edited_by(request.user)

    if request.method == 'POST':
        if not can_edit:
            messages.error(request, _('Solo quien subió el documento puede modificar sus metadatos.'))
            return redirect('specs:document_review', doc_id=entry.id)
        form = MetadataReviewForm(request.POST, instance=document)
        if form.is_valid():
            document = form.save(commit=False)
            document.metadata_status = Document.METADATA_CONFIRMED
            document.save()
            messages.success(request, _('Metadatos confirmados.'))
            return redirect('specs:handling')
    else:
        form = MetadataReviewForm(instance=document)

    if not can_edit:
        for field in form.fields.values():
            field.disabled = True
    return render(request, 'specs/document_review.html', {
        'entry': entry, 'document': document, 'form': form, 'can_edit': can_edit,
    })


@login_required
def document_delete(request, doc_id):
    """Removes the user's access to a document; the file and its vectors go when nobody else has it."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        filename = doc.filename
        orphan = None
        with transaction.atomic():
            if doc.document_id:
                # Lock the Document so a concurrent upload of the same file cannot race the cleanup
                document = Document.objects.select_for_update().get(pk=doc.document_id)
                doc.delete()
                if not document.accesses.exists():
                    orphan = document
            else:
                doc.delete()
        if orphan is not None:
            purge_document(orphan)
        messages.success(request, _('Documento %(filename)s eliminado.') % {'filename': filename})
    return redirect('specs:handling')

@login_required
def document_update(request, doc_id):
    """Updates the title (filename) or company of a document."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        print(f"Received update for doc_id {doc_id} with data: {request.POST}")
        new_filename = request.POST.get('filename')
        new_company = request.POST.get('company')
        
        if new_filename:
            doc.filename = new_filename
            doc.company = new_company 
            doc.save()
            messages.success(request, _('Nombre del documento actualizado.'))
        elif new_company:
            doc.company = new_company
            doc.save()
            messages.success(request, _('OEM/Empresa actualizado.'))
    return redirect('specs:handling')

@login_required
def chat_view(request):
    """Renders the main chat page."""
    return render(request, 'specs/chat.html')

@login_required
def chat_query(request):
    """API endpoint to process questions to the RAG."""
    if request.method == 'POST':
        query_text = request.POST.get('query')
        if not query_text:
            return JsonResponse({'error': _('No se proporcionó ninguna pregunta')}, status=400)

        try:
            # Get the RAG engine filtered for this user, answering in the site's active language
            language_name = dict(settings.LANGUAGES).get(get_language(), get_language())
            print(f"Getting RAG engine for user {request.user.id} (answers in {language_name})")
            query_engine = get_rag_engine(request.user.id, language_name)
            print(f"Running RAG query for user {request.user.id}: '{query_text}'")
            logger.info(f"TIPO DE query_engine: {type(query_engine)}")

            response = query_engine.query(query_text)

            print(f"RAG response obtained: '{response}'")
            # Format sources (optional, for traceability)
            sources = []
            for node in response.source_nodes:
                print(f"Candidate source: '{node.node.get_content()[:100]}...' with metadata: {node.node.metadata} and score: {node.score}")
                # sources.append({
                #     'filename': node.node.metadata.get('filename', 'Unknown'),
                #     'score': float(node.score or 0)
                # })
                # The metadata lives inside node.node.metadata
                node_metadata = getattr(node.node, 'metadata', {})
                
                sources.append({
                    'filename': node_metadata.get('filename', 'Unknown'),
                    'score': float(node.score or 0)
                })
            print (f"Response: '{response}' with sources: {sources}")

            # Warn when an answer rests on a translation because the original is not in the library
            states = library_state(request.user.id)
            notes = []
            for filename, document_id in {(n.node.metadata.get('filename', ''), n.node.metadata.get(DOC_KEY))
                                          for n in response.source_nodes}:
                if document_id in states and states[document_id].state == TRANSLATION_ONLY:
                    notes.append(_('«%(filename)s» es una traducción y el original no está en tu biblioteca: '
                                   'el original puede prevalecer.') % {'filename': filename})
            response_text = str(response)
            spring_link = _build_spring_link(extract_spring_design_block(response_text))
            return JsonResponse({
                'response': response_text,
                'sources': sources,
                'notes': sorted(notes),
                'spring_link': spring_link,
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': _('Método no permitido')}, status=405)

@login_required
def upload_document(request):
    """
    Renders or processes the document upload.
    """
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_files = request.FILES.getlist('pdf_file')
            
            try:
                fs = _gridfs()
                analyzing = 0

                for pdf_file in pdf_files:
                    data = pdf_file.read()
                    file_hash = hashlib.sha256(data).hexdigest()

                    # The same file is stored and indexed only once, whoever uploads it
                    document = Document.objects.filter(file_hash=file_hash).first()
                    if document is None:
                        mongo_id = fs.put(data, filename=pdf_file.name)
                        try:
                            with transaction.atomic():
                                document = Document.objects.create(
                                    file_hash=file_hash, mongo_id=str(mongo_id), filename=pdf_file.name,
                                    uploaded_by=request.user)
                        except IntegrityError:
                            # Someone uploaded the same new file at the same moment
                            fs.delete(mongo_id)
                            document = Document.objects.get(file_hash=file_hash)

                    company = form.cleaned_data.get('company') or ''
                    if not company:
                        # Reuse the label another user already gave to this same file
                        company = (UserDocument.objects.filter(document=document)
                                   .exclude(company__isnull=True).exclude(company='')
                                   .values_list('company', flat=True).first() or '')

                    with transaction.atomic():
                        # Lock the Document so a concurrent delete of its last access cannot race this
                        document = Document.objects.select_for_update().get(pk=document.pk)
                        doc, created = UserDocument.objects.get_or_create(
                            user=request.user, document=document,
                            defaults={'filename': pdf_file.name, 'company': company, 'mongo_id': document.mongo_id},
                        )

                    if not created:
                        messages.info(request, _('El documento «%(filename)s» ya está en tu biblioteca.')
                                      % {'filename': pdf_file.name})
                        continue

                    if document.is_indexed:
                        messages.info(request, _('«%(filename)s» ya estaba analizado: se ha añadido a tu biblioteca sin volver a procesarlo.')
                                      % {'filename': pdf_file.name})
                        continue

                    # Analyze in a background thread so the request returns immediately
                    analyzing += 1
                    threading.Thread(
                        target=process_document_task,
                        args=(str(doc.id),),
                        daemon=True,
                    ).start()

                if analyzing:
                    messages.success(request, _('Tus documentos se están analizando en segundo plano. Podrás consultarlos en un par de minutos.'))
                return redirect('specs:handling')

            except Exception as e:
                import traceback; traceback.print_exc()
                messages.error(request, _('Error general durante la subida: %(error)s') % {'error': str(e)})
                return redirect('specs:upload_document')
    else:
        form = DocumentUploadForm()

    return render(request, 'specs/upload.html', {'form': form})