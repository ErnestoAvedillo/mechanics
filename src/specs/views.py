import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.utils.translation import gettext as _
from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs
from .models import UserDocument
from .forms import DocumentUploadForm
from .rag_engine import get_rag_engine, index_document_to_rag
from .tasks import process_document_task

logger = logging.getLogger(__name__)

def index(request):
    """Redirects to the main specs page."""
    return render(request, 'specs/index.html')

@login_required
def document_list(request):
    """List of documents uploaded by the user."""
    documents = UserDocument.objects.filter(user=request.user).order_by('-upload_date')
    return render(request, 'specs/document_list.html', {'documents': documents})

@login_required
def document_view(request, doc_id):
    """Serves a PDF document from MongoDB using GridFS."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    
    try:
        # Connect to MongoDB and retrieve the file
        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        
        # Convert mongo_id to ObjectId
        mongo_id = ObjectId(doc.mongo_id)
        
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
def document_delete(request, doc_id):
    """Deletes a document."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        # Note: You should also delete from MongoDB and ChromaDB here if applicable
        doc.delete()
        messages.success(request, _('Documento %(filename)s eliminado.') % {'filename': doc.filename})
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
            # Get the RAG engine filtered for this user
            print(f"Getting RAG engine for user {request.user.id}")
            query_engine = get_rag_engine(request.user.id)
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
            return JsonResponse({
                'response': str(response),
                'sources': sources
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
                # Save to MongoDB
                client = MongoClient(settings.MONGO_URL)
                db = client[settings.MONGO_DB_NAME]
                fs = gridfs.GridFS(db)
                
                success_count = 0
                error_messages = []
                
                for pdf_file in pdf_files:
                    mongo_id = fs.put(pdf_file.read(), filename=pdf_file.name)
                    
                    # Save to Postgres (Django)
                    doc = UserDocument.objects.create(
                        user=request.user,
                        mongo_id=str(mongo_id),
                        filename=pdf_file.name,
                        company=form.cleaned_data.get('company', '')
                    )
                    # Send the document to the task queue
                    process_document_task.delay(str(doc.id))


                #     # Index document
                #     success, msg = index_document_to_rag(doc.id)
                #     if success:
                #         success_count += 1
                #     else:
                #         error_messages.append(f"{pdf_file.name} ({msg})")
                        
                # if success_count > 0:
                #     if len(pdf_files) == 1:
                #         messages.success(request, f'Document {pdf_files[0].name} uploaded and analyzed successfully.')
                #     else:
                #         messages.success(request, f'{success_count} documents uploaded and analyzed successfully.')
                        
                # if error_messages:
                #     messages.error(request, f'Errors during analysis: {", ".join(error_messages)}')
                    
                messages.success(request, _('Tus documentos se están analizando en segundo plano. Podrás consultarlos en un par de minutos.'))
                return redirect('specs:handling')

            except Exception as e:
                import traceback; traceback.print_exc()
                messages.error(request, _('Error general durante la subida: %(error)s') % {'error': str(e)})
                return redirect('specs:upload_document')
    else:
        form = DocumentUploadForm()

    return render(request, 'specs/upload.html', {'form': form})