from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from pymongo import MongoClient
import gridfs
from .models import UserDocument
from .forms import DocumentUploadForm
from .rag_engine import get_rag_engine, index_document_to_rag

def index(request):
    """Redirige a la página principal de specs."""
    return render(request, 'specs/index.html')

@login_required
def document_list(request):
    """Lista de documentos subidos por el usuario."""
    documents = UserDocument.objects.filter(user=request.user).order_by('-upload_date')
    return render(request, 'specs/document_list.html', {'documents': documents})

@login_required
def document_delete(request, doc_id):
    """Elimina un documento."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        # Nota: Aquí también deberías eliminar de MongoDB y ChromaDB si corresponde
        doc.delete()
        messages.success(request, f'Documento {doc.filename} eliminado.')
    return redirect('specs:handling')

@login_required
def document_update(request, doc_id):
    """Actualiza el título (filename) de un documento."""
    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        new_filename = request.POST.get('filename')
        if new_filename:
            doc.filename = new_filename
            doc.save()
            messages.success(request, 'Nombre del documento actualizado.')
    return redirect('specs:handling')

@login_required
def chat_view(request):
    """Renderiza la página principal del chat."""
    return render(request, 'specs/chat.html')

@login_required
def chat_query(request):
    """Endpoint API para procesar preguntas al RAG."""
    if request.method == 'POST':
        query_text = request.POST.get('query')
        if not query_text:
            return JsonResponse({'error': 'No se proporcionó ninguna pregunta'}, status=400)

        try:
            # Obtener el motor RAG filtrado para este usuario
            query_engine = get_rag_engine(request.user.id)
            print(f"Ejecutando consulta RAG para usuario {request.user.id}: '{query_text}'")
            # Ejecutar consulta
            response = query_engine.query(query_text)
            print(f"Respuesta RAG obtenida: '{response}'")
            # Formatear fuentes (opcional, para dar trazabilidad)
            sources = []
            for node in response.source_nodes:
                print(f"Fuente candidata: '{node.node.get_content()[:100]}...' con metadatos: {node.node.metadata} y score: {node.score}")
                sources.append({
                    'filename': node.metadata.get('filename', 'Desconocido'),
                    'score': float(node.score or 0)
                })
            print (f"Respuesta: '{response}' con fuentes: {sources}")
            return JsonResponse({
                'response': str(response),
                'sources': sources
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def upload_document(request):
    """
    Renderiza o procesa la subida de documentos.
    """
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_files = request.FILES.getlist('pdf_file')
            
            try:
                # Guardar en MongoDB
                client = MongoClient(settings.MONGO_URL)
                db = client[settings.MONGO_DB_NAME]
                fs = gridfs.GridFS(db)
                
                success_count = 0
                error_messages = []
                
                for pdf_file in pdf_files:
                    mongo_id = fs.put(pdf_file.read(), filename=pdf_file.name)
                    
                    # Guardar en Postgres (Django)
                    doc = UserDocument.objects.create(
                        user=request.user,
                        mongo_id=str(mongo_id),
                        filename=pdf_file.name,
                        company=form.cleaned_data.get('company', '')
                    )
                    
                    # Indexar documento
                    success, msg = index_document_to_rag(doc.id)
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(f"{pdf_file.name} ({msg})")
                        
                if success_count > 0:
                    if len(pdf_files) == 1:
                        messages.success(request, f'Documento {pdf_files[0].name} subido y analizado con éxito.')
                    else:
                        messages.success(request, f'{success_count} documentos subidos y analizados con éxito.')
                        
                if error_messages:
                    messages.error(request, f'Errores en el análisis: {", ".join(error_messages)}')
                    
                return redirect('specs:handling')

            except Exception as e:
                messages.error(request, f'Error general durante la subida: {str(e)}')
                return redirect('specs:upload_document')
    else:
        form = DocumentUploadForm()

    return render(request, 'specs/upload.html', {'form': form})