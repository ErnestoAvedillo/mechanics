from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .rag_engine import get_rag_engine

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
