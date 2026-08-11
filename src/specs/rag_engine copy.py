import os
import tempfile
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings

from llama_index.core import StorageContext, VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from llama_index.llms.google_genai import GoogleGenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from llama_parse import LlamaParse
from .models import UserDocument

TARGET_COLLECTION = "engineering_specs_bge" 

# --- SINGLETON PATTERN: Variables globales persistentes ---
_QDRANT_CLIENT = None
_IS_INITIALIZED = False

def initialize_global_models():
    """Se llama una sola vez al inicio de la app."""
    global _IS_INITIALIZED, _QDRANT_CLIENT
    if _IS_INITIALIZED:
        return

    print("--- Inicializando modelos RAG en memoria ---")
    
    # 1. Configurar LLM
    Settings.llm = GoogleGenAI(
        api_key=settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else None,
        model=settings.GOOGLE_MODEL if hasattr(settings, 'GOOGLE_MODEL') else "models/gemini-3.1-flash-lite-preview"
    )
        
    # 2. Configurar Embeddings (BGE-M3)
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")
    
    # 3. Inicializar Qdrant Client
    _QDRANT_CLIENT = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    
    _IS_INITIALIZED = True
    print("--- Modelos cargados exitosamente ---")

# Llamar a la inicialización al importar el módulo o al inicio del proceso
initialize_global_models()

def get_rag_engine(user_id):
    """Motor de consulta ultrarrápido porque los modelos ya están en RAM."""
    global _QDRANT_CLIENT
    
    vector_store = QdrantVectorStore(client=_QDRANT_CLIENT, collection_name=TARGET_COLLECTION)
    index = VectorStoreIndex.from_vector_store(vector_store)
    
    filters = MetadataFilters(
        filters=[MetadataFilter(key="user_id", value=user_id)]
    )
    
    # El reranker también se carga una sola vez, no aquí dentro
    reranker = FlagEmbeddingReranker(
        top_n=4,
        model="BAAI/bge-reranker-v2-m3"
    )
    
    return index.as_query_engine(
        filters=filters,
        similarity_top_k=15,
        node_postprocessors=[reranker]
    )