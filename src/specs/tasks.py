from celery import shared_task
from .rag_engine import index_document_to_rag
from .models import UserDocument
import logging

logging.basicConfig(level=logging.INFO)

@shared_task
def process_document_task(document_id):
    """
    Celery task to process and index the document in LlamaParse and Qdrant.
    """
    success, msg = index_document_to_rag(document_id)
    logging.info(f"Doc_id {document_id}: {'Success' if success else 'Error'} - {msg}")
    return f"Doc_id {document_id}: {'Success' if success else 'Error'} - {msg}"


@shared_task
def retry_pending_documents():
    """
    Periodic task that checks for documents pending indexing
    (documents with is_indexed=False) and processes them automatically.
    Useful for recovering from server crashes.
    """
    pending_docs = UserDocument.objects.filter(is_indexed=False).values_list('id', flat=True)

    if not pending_docs.exists():
        logging.info("No documents pending processing")
        return "No documents pending processing"
    
    results = []
    for doc_id in pending_docs:
        result = process_document_task.delay(doc_id)
        results.append({
            'doc_id': doc_id,
            'task_id': result.id
        })
        logging.info(f"Retrying document ID {doc_id} with Celery task ID {result.id}")

    return f"Started {len(results)} processing tasks for pending documents"

