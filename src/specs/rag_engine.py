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

# New HuggingFace and FlagEmbedding imports
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from llama_index.llms.google_genai import GoogleGenAI

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from llama_parse import LlamaParse
from .models import UserDocument

# Renamed the collection to avoid clashing with Gemini's current 3072-dimension vectors
TARGET_COLLECTION = "engineering_specs_bge" 

_QDRANT_CLIENT = None

def get_qdrant_client():
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        _QDRANT_CLIENT = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return _QDRANT_CLIENT


# Global variables for in-memory persistence
_EMBED_MODEL = None
_RERANKER = None


def _configure_models():
    """Configures the LLM (Gemini) and the multilingual Embedding (BGE-M3) in Settings for use across the whole RAG."""
    # We keep Gemini or any other LLM for text generation
    if settings.GOOGLE_API_KEY:
        Settings.llm = GoogleGenAI(api_key=settings.GOOGLE_API_KEY,
                                   model=settings.GOOGLE_MODEL)
    else:
        Settings.llm = GoogleGenAI(model="models/gemini-3.1-flash-lite-preview")
        
    # Upgraded to BGE-M3 for cross-lingual retrieval
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")


def get_rag_engine(user_id):
    """
    Configures and returns the RAG query engine for a specific user,
    adding a multilingual re-ranking step.
    """
    _configure_models()
    client = get_qdrant_client()

    if not client.collection_exists(TARGET_COLLECTION):
        client.create_collection(
            collection_name=TARGET_COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)  # BGE-M3 projects to 1024 dims
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
    
    # Reranker configured with BGE-Reranker-v2-m3
    # Gives a detailed scan ("cross-encoder") to align semantics across languages
    reranker = FlagEmbeddingReranker(
        top_n=4,
        model="BAAI/bge-reranker-v2-m3"
    )
    
    # We request similarity_top_k=10 or 15 to bring in more raw candidate context,
    # letting the reranker pick the final 4 best cross-lingual results.
    return index.as_query_engine(
        filters=filters,
        similarity_top_k=15,
        node_postprocessors=[reranker]
    )

def index_document_to_rag(document_id):
    """
    Reads a document from MongoDB GridFS, processes it and indexes it using BGE-M3.
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
            print(f"Sending document to LlamaParse for processing: '{temp_path}'")
            documents = parser.load_data(temp_path)
        else:
            print(f"Processing local document: '{temp_path}'")
            from llama_index.readers.file import PDFReader
            reader = PDFReader()
            documents = reader.load_data(temp_path)
            
        os.remove(temp_path)

        if not documents:
            return False, "Error: Could not extract text from the document."

        for d in documents:
            d.metadata.update({
                "user_id": doc_ref.user.id,
                "company": doc_ref.company,
                "filename": doc_ref.filename,
                "doc_id": doc_ref.id
            })

        q_client = get_qdrant_client()

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
        return True, f"Successfully indexed ({len(documents)} pages/sections)"

    except Exception as e:
        return False, f"Error in LlamaParse/Indexing: {str(e)}"