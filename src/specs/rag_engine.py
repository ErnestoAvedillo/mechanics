import os
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from .models import UserDocument
import io
import PyPDF2 # Asegurémonos de tener una forma de leer el PDF

def get_rag_engine(user_id):
    """
    Configura y devuelve el motor de consulta RAG para un usuario específico.
    Utiliza Qdrant como base de datos vectorial con filtrado por metadatos.
    """
    client = QdrantClient(url=settings.QDRANT_URL)
    vector_store = QdrantVectorStore(client=client, collection_name="engineering_specs")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # El índice se construye o carga. Aquí lo inicializamos para consulta.
    # Nota: En una app real, el índice suele persistir y solo lo cargamos.
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    return index.as_query_engine(filters={"user_id": user_id})

def index_document_to_rag(document_id):
    """
    Lee un documento de MongoDB GridFS, extrae su texto y lo indexa en Qdrant.
    """
    try:
        doc_ref = UserDocument.objects.get(id=document_id)
        
        # 1. Recuperar binario de MongoDB
        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        pdf_data = fs.get(ObjectId(doc_ref.mongo_id)).read()

        # 2. Extraer texto (Simplificado para el script inicial)
        # Nota: Para producción recomendamos LlamaParse o Unstructured
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()

        # 3. Crear documento de LlamaIndex con metadatos de aislamiento
        llama_doc = Document(
            text=text,
            metadata={
                "user_id": doc_ref.user.id,
                "company": doc_ref.company,
                "filename": doc_ref.filename,
                "doc_id": doc_ref.id
            }
        )

        # 4. Indexar en Qdrant
        q_client = QdrantClient(url=settings.QDRANT_URL)
        vector_store = QdrantVectorStore(client=q_client, collection_name="engineering_specs")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Esto inserta los vectores en Qdrant
        VectorStoreIndex.from_documents(
            [llama_doc], 
            storage_context=storage_context,
            show_progress=True
        )

        # 5. Marcar como indexado en Django
        doc_ref.is_indexed = True
        doc_ref.save()
        return True, "Indexado con éxito"

    except Exception as e:
        return False, str(e)
