import os
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from llama_parse import LlamaParse
from .models import UserDocument
import io
import tempfile

def get_rag_engine(user_id):
    """
    Configura y devuelve el motor de consulta RAG para un usuario específico.
    """
    client = QdrantClient(url=settings.QDRANT_URL)
    vector_store = QdrantVectorStore(client=client, collection_name="engineering_specs")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    return index.as_query_engine(filters={"user_id": user_id})

def index_document_to_rag(document_id):
    """
    Lee un documento de MongoDB GridFS, lo procesa con LlamaParse (para tablas complejas)
    y lo indexa en Qdrant.
    """
    try:
        doc_ref = UserDocument.objects.get(id=document_id)
        
        # 1. Recuperar binario de MongoDB
        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        pdf_data = fs.get(ObjectId(doc_ref.mongo_id)).read()

        # 2. Procesar con LlamaParse (Optimizado para tablas de ingeniería)
        # Necesitamos guardar temporalmente el archivo para LlamaParse
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(pdf_data)
            temp_path = tf.name

        parser = LlamaParse(
            api_key=settings.LLAMA_CLOUD_API_KEY,
            result_type="markdown",  # Markdown preserva mejor la estructura de tablas
            verbose=True,
            language="es"
        )
        
        # Extraemos los documentos procesados por LlamaParse
        documents = parser.load_data(temp_path)
        
        # Limpiar archivo temporal
        os.remove(temp_path)

        # 3. Añadir metadatos de aislamiento a cada chunk procesado
        for d in documents:
            d.metadata.update({
                "user_id": doc_ref.user.id,
                "company": doc_ref.company,
                "filename": doc_ref.filename,
                "doc_id": doc_ref.id
            })

        # 4. Indexar en Qdrant
        q_client = QdrantClient(url=settings.QDRANT_URL)
        vector_store = QdrantVectorStore(client=q_client, collection_name="engineering_specs")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context,
            show_progress=True
        )

        # 5. Marcar como indexado
        doc_ref.is_indexed = True
        doc_ref.save()
        return True, f"Indexado con éxito ({len(documents)} páginas/secciones)"

    except Exception as e:
        return False, f"Error en LlamaParse/Indexación: {str(e)}"
