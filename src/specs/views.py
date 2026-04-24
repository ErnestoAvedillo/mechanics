from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from .models import UserDocument
from .rag_engine import get_rag_engine

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

            # Ejecutar consulta
            response = query_engine.query(query_text)

            # Formatear fuentes (opcional, para dar trazabilidad)
            sources = []
            for node in response.source_nodes:
                sources.append({
                    'filename': node.metadata.get('filename', 'Desconocido'),
                    'score': float(node.score or 0)
                })

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
    (Debes adaptarlo según el template html que vayas a usar)
    """
    # O el nombre del archivo HTML que corresponda
    return render(request, 'specs/upload.html')