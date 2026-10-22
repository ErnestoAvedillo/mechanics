import os
import re
import tempfile
import io
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from django.conf import settings

from llama_index.core import StorageContext, VectorStoreIndex, Settings, PromptTemplate
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


def _qa_template(language_name):
    """Default QA prompt, pinned to answer in the site's current language rather than the spec's."""
    return PromptTemplate(
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Given the context information and not prior knowledge, answer the query.\n"
        f"Answer always in {language_name}, regardless of the language of the context or of the query.\n"
        "Query: {query_str}\n"
        "Answer: "
    )


def _refine_template(language_name):
    """Default refine prompt, pinned the same way as _qa_template."""
    return PromptTemplate(
        "The original query is as follows: {query_str}\n"
        "We have provided an existing answer: {existing_answer}\n"
        "We have the opportunity to refine the existing answer (only if needed) with some more context below.\n"
        "------------\n"
        "{context_msg}\n"
        "------------\n"
        "Given the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.\n"
        f"Answer always in {language_name}, regardless of the language of the context or of the query.\n"
        "Refined Answer: "
    )


# Asking the main RAG prompt to both write a long technical answer AND remember to append a
# structured block at the end was not reliable: on longer, more elaborate answers the model
# dropped the block entirely (it has too much else competing for attention - RAG context, the
# language rule, the query itself). So this runs as a second, narrowly-scoped call whose only job
# is extracting the block from the already-written answer - nothing else to get distracted by.
# The chat view (_build_spring_link in views.py) turns a successful extraction into a link to the
# compression calculator with those fields prefilled; the keys below are literal tokens it parses.
_SPRING_DESIGN_EXTRACTION_PROMPT = (
    "You extract structured data; you do not write explanations or repeat the answer.\n"
    "Below is an ANSWER that may or may not propose concrete numeric values to design a "
    "mechanical compression spring.\n"
    "If it does, output ONLY a fenced code block tagged spring-design with one key=value pair "
    "per line, using only these literal keys (do not translate them) and only the ones the "
    "answer actually gives a numeric value for: material (a short code such as SH, SM or SL), "
    "diametro_hilo, diametro_exterior, diametro_medio, diametro_interior, numero_espiras, "
    "longitud_libre, longitud_inicial, longitud_final, numero_ciclos (one of 1e3, 1e4, 1e5, 1e6, "
    "1e7), tipo_final (one of abierto, cerrado, semi-cerrado, rectificado). Convert every "
    "diameter and length to millimeters.\n"
    "If the answer does NOT propose a spring design, output exactly NONE and nothing else.\n"
    "Output nothing besides that code block (or NONE): no commentary, no markdown around it.\n\n"
    "ANSWER:\n{answer}\n"
)

# Cheap pre-filter so the extraction call above only runs for answers that plausibly describe a
# spring, instead of on every chat query.
_SPRING_HINT_RE = re.compile(
    r"spring|muelle|resorte|wire diameter|coil|espira|free length|longitud libre",
    re.IGNORECASE,
)


def extract_spring_design_block(answer_text):
    """
    Pulls the spring's parameters out of `answer_text` as raw `key=value` text (possibly still
    fenced), via a dedicated LLM call - see the module comment above for why this is separate
    from the main RAG answer. Returns '' when there's nothing to extract, including on any
    failure: this must never break the chat response.
    """
    if not _SPRING_HINT_RE.search(answer_text):
        return ''
    try:
        _configure_models()
        completion = Settings.llm.complete(_SPRING_DESIGN_EXTRACTION_PROMPT.format(answer=answer_text))
        text = str(completion).strip()
        return '' if text.upper() == 'NONE' else text
    except Exception:
        return ''


def get_rag_engine(user_id, language_name="español", top_k=6):
    """
    Configures and returns the RAG query engine for a specific user.
    The engine only sees the current documents in the user's library, and answers
    in `language_name` (the site's active language) even when the specs it cites are in another one.
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
        similarity_top_k=top_k,
        text_qa_template=_qa_template(language_name),
        refine_template=_refine_template(language_name),
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