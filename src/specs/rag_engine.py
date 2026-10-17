import os
import tempfile
import io
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings

from llama_index.core import StorageContext, VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from llama_parse import LlamaParse
from .metadata import apply_metadata, extract_metadata
from .models import Document, UserDocument
from .versions import searched_document_ids

# Nebius Token Factory (OpenAI-compatible API, no local models). New collection: vectors are 4096-dim
TARGET_COLLECTION = "engineering_specs_nebius"
EMBED_DIM = 4096   # Qwen3-Embedding-8B

# Payload key holding the Document id. Not "document_id"/"doc_id": LlamaIndex reserves
# those for its own node ids and would overwrite them.
DOC_KEY = "specs_document_id"

_QDRANT_CLIENT = None

def get_qdrant_client():
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        _QDRANT_CLIENT = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return _QDRANT_CLIENT


def ensure_collection(client):
    """Creates the collection and its payload indexes if they do not exist yet."""
    if not client.collection_exists(TARGET_COLLECTION):
        client.create_collection(
            collection_name=TARGET_COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE)
        )
        client.create_payload_index(
            collection_name=TARGET_COLLECTION,
            field_name=DOC_KEY,
            field_schema="integer"
        )


def accessible_document_ids(user_id):
    """Ids of the documents the user's searches may use: their library resolved by edition and language."""
    return searched_document_ids(user_id)


def delete_document_vectors(document_id):
    """Removes every vector of a Document from Qdrant (before re-indexing, or when its last access is deleted)."""
    client = get_qdrant_client()
    if client.collection_exists(TARGET_COLLECTION):
        client.delete(
            collection_name=TARGET_COLLECTION,
            points_selector=Filter(must=[FieldCondition(key=DOC_KEY, match=MatchValue(value=document_id))]),
        )


def _configure_models():
    """Configures the LLM (NVIDIA Nemotron) and the multilingual Embedding (Qwen3) on Nebius Token Factory."""
    Settings.llm = OpenAILike(
        model=settings.NEBIUS_LLM_MODEL,
        api_base=settings.NEBIUS_BASE_URL,
        api_key=settings.NEBIUS_API_KEY,
        is_chat_model=True,
        context_window=262144,
    )
    Settings.embed_model = OpenAILikeEmbedding(
        model_name=settings.NEBIUS_EMBED_MODEL,
        api_base=settings.NEBIUS_BASE_URL,
        api_key=settings.NEBIUS_API_KEY,
        embed_batch_size=16,
    )


def get_rag_engine(user_id):
    """
    Configures and returns the RAG query engine for a specific user.
    The engine only sees the current documents in the user's library.
    """
    _configure_models()
    client = get_qdrant_client()
    ensure_collection(client)

    vector_store = QdrantVectorStore(client=client, collection_name=TARGET_COLLECTION)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    # Fail closed: with no accessible documents, filter on an id that matches nothing
    document_ids = accessible_document_ids(user_id) or [-1]
    filters = MetadataFilters(
        filters=[MetadataFilter(key=DOC_KEY, value=document_ids, operator=FilterOperator.IN)]
    )

    # No local reranker (it needed PyTorch); return the best matches directly
    return index.as_query_engine(
        filters=filters,
        similarity_top_k=6,
    )


def index_document_to_rag(user_document_id):
    """
    Reads the file of a user's document from MongoDB GridFS, processes it and indexes it
    using Nebius embeddings. A Document is indexed only once, however many users have it.
    Returns (success, message).
    """
    document = None
    claimed = False
    try:
        _configure_models()
        doc_ref = UserDocument.objects.select_related('document').get(id=user_document_id)
        document = doc_ref.document
        if document.is_indexed:
            return True, "Already indexed / Ya estaba indexado"
        if not Document.claim_indexing(document.pk):
            return True, "Indexing already in progress / Indexación ya en curso"
        claimed = True

        client = MongoClient(settings.MONGO_URL)
        db = client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(db)
        pdf_data = fs.get(ObjectId(document.mongo_id)).read()

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

        # One LLM call gives the OEM and the standard's metadata (a proposal until the uploader confirms it).
        # A retry must not overwrite metadata that has already been confirmed.
        metadata = None
        if document.metadata_status != Document.METADATA_CONFIRMED:
            metadata = extract_metadata("\n\n".join(d.get_content() for d in documents[:3]))
            apply_metadata(document, metadata)
        if not doc_ref.company and metadata and metadata["issuer"]:
            doc_ref.company = metadata["issuer"]
            doc_ref.save(update_fields=['company'])

        for d in documents:
            d.metadata.update({
                DOC_KEY: document.pk,
                "company": doc_ref.company,
                "filename": document.filename,
            })
            # The id is only for filtering; keep it out of the embedded text and the LLM context
            d.excluded_embed_metadata_keys = [DOC_KEY]
            d.excluded_llm_metadata_keys = [DOC_KEY]

        q_client = get_qdrant_client()
        ensure_collection(q_client)
        delete_document_vectors(document.pk)  # a retry must not leave duplicate vectors

        vector_store = QdrantVectorStore(client=q_client, collection_name=TARGET_COLLECTION)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context,
            show_progress=True
        )

        document.is_indexed = True
        document.indexing_started_at = None
        document.save(update_fields=['is_indexed', 'indexing_started_at'])
        return True, f"Successfully indexed ({len(documents)} pages/sections)"

    except Exception as e:
        if claimed:
            Document.objects.filter(pk=document.pk).update(indexing_started_at=None)  # allow a retry
        return False, f"Error in LlamaParse/Indexing: {str(e)}"