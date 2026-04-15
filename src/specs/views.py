import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from pymongo import MongoClient
import gridfs
from .forms import DocumentUploadForm
from .models import UserDocument

@login_required
def upload_document(request):
    """
    Gestiona la subida de un PDF: lo guarda en MongoDB (GridFS) 
    y crea la referencia en el modelo Django del usuario.
    """
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['pdf_file']
            company = form.cleaned_data.get('company')

            try:
                # 1. Conexión a MongoDB
                client = MongoClient(settings.MONGO_URL)
                db = client[settings.MONGO_DB_NAME]
                fs = gridfs.GridFS(db)

                # 2. Guardar binario en GridFS
                mongo_id = fs.put(
                    pdf_file.read(),
                    filename=pdf_file.name,
                    content_type='application/pdf',
                    company=company,
                    user_id=request.user.id
                )

                # 3. Crear referencia en Django
                doc = UserDocument.objects.create(
                    user=request.user,
                    mongo_id=str(mongo_id),
                    filename=pdf_file.name,
                    company=company
                )

                # 4. Lanzar indexación RAG (En background sería ideal, aquí síncrono para el MVP)
                from .rag_engine import index_document_to_rag
                success, msg = index_document_to_rag(doc.id)

                if success:
                    messages.success(request, f"¡'{pdf_file.name}' subido e indexado en el RAG!")
                else:
                    messages.warning(request, f"Subido a MongoDB, pero fallo al indexar: {msg}")
                
                return redirect('specs:document_list')

            except Exception as e:
                messages.error(request, f"Error al subir a MongoDB: {str(e)}")
    else:
        form = DocumentUploadForm()

    return render(request, 'specs/upload.html', {'form': form})

@login_required
def document_list(request):
    """
    Lista los documentos del usuario actual.
    """
    documents = UserDocument.objects.filter(user=request.user).order_by('-upload_date')
    return render(request, 'specs/document_list.html', {'documents': documents})
