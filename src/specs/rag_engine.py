import os
import tempfile
import io
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings

from llama_index.core import Document, StorageContext, VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Nuevos imports de HuggingFace y FlagEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from llama_index.llms.gemini import Gemini

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from llama_parse import LlamaParse
from .models import UserDocument

# Cambiamos de nombre la colección para evitar choques con los vectores de 3072 dimensiones actuales de Gemini
TARGET_COLLECTION = "engineering_specs_bge" 

def _configure_models():
    """Configura el LLM (Gemini) y el Embedding Multilingüe (BGE-M3) en Settings para su uso en todo el RAG."""
    # Mantenemos Gemini o cualquier otro LLM para la generación de texto
    if settings.GOOGLE_API_KEY:
        Settings.llm = Gemini(api_key=settings.GOOGLE_API_KEY,
                              model_name=settings.GOOGLE_MODEL)
    else:
        Settings.llm = Gemini(model_name="models/gemini-3.1-flash-lite-preview")
        
    # Mejoramos a BGE-M3 para Cross-lingual retrieval
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")


def get_rag_engine(user_id):
    """
    Configura y devuelve el motor de consulta RAG para un usuario específico,
    añadiendo un paso de re-clasificación (reranking) multilingüe.
    """
    _configure_models()
    client = QdrantClient(url=settings.QDRANT_URL,
                          api_key=settings.QDRANT_API_KEY)
    
    if not client.collection_exists(TARGET_COLLECTION):
        client.create_collection(
            collection_name=TARGET_COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)  # BGE-M3 proyecta a 1024 dims
        )
        client.create_payload_index(
            collection_name=TARGET_COLLECTION,
            field_name="user_id",
            field_schema="integer"
        )
        
    vector_store = QdrantVectorStore(client=client, collection_name=TARGET_COLLECTION)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    
    filters = MetadataFilters(
        filters=[MetadataFilter(key="user_id", value=user_id)]
    )
    
    # Reranker configurado con BGE-Reranker-v2-m3
    # Le da un escaneo detallado ("cross-encoder") para alinear semántica en varios idiomas
    reranker = FlagEmbeddingReranker(
        top_n=4,
        model="BAAI/bge-reranker-v2-m3"
    )
    
    # Pedimos similarity_top_k=10 o 15 para traer más contexto candidato bruto, 
    # y que el reranker elija los 4 mejores definitivos cross-lingual.
    return index.as_query_engine(
        filters=filters,
        similarity_top_k=15,
        node_postprocessors=[reranker]
    )

def index_document_to_rag(document_id):
    """
    Lee un documento de MongoDB GridFS, procesa y lo indexa usando BGE-M3.
    """
    try:
        _configure_models()
        doc_ref = UserDocument.objects.get(id=document_id)
        
        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        pdf_data = fs.get(ObjectId(doc_ref.mongo_id)).read()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(pdf_data)
            temp_path = tf.name

        if settings.LLAMA_CLOUD_API_KEY:
            parser = LlamaParse(
                api_key=settings.LLAMA_CLOUD_API_KEY,
                result_type="markdown", 
                verbose=True,
                language="es"
            )
            print(f"Enviando documento a LlamaParse para procesamiento: '{temp_path}'")
            documents = parser.load_data(temp_path)
        else:
            print(f"Procesando documento local: '{temp_path}'")
            from llama_index.readers.file import PDFReader
            reader = PDFReader()
            documents = reader.load_data(temp_path)
            
        os.remove(temp_path)

        if not documents:
            return False, "Error: No se pudo extraer texto del documento."

        for d in documents:
            d.metadata.update({
                "user_id": doc_ref.user.id,
                "company": doc_ref.company,
                "filename": doc_ref.filename,
                "doc_id": doc_ref.id
            })

        q_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        if not q_client.collection_exists(TARGET_COLLECTION):
            q_client.create_collection(
                collection_name=TARGET_COLLECTION,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
            q_client.create_payload_index(
                collection_name=TARGET_COLLECTION,
                field_name="user_id",
                field_schema="integer"
            )

        vector_store = QdrantVectorStore(client=q_client, collection_name=TARGET_COLLECTION)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context,
            show_progress=True
        )

        doc_ref.is_indexed = True
        doc_ref.save()
        return True, f"Indexado con éxito ({len(documents)} páginas/secciones)"

    except Exception as e:
        return False, f"Error en LlamaParse/Indexación: {str(e)}"