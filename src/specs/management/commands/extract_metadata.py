"""
Extracts the standard's metadata (issuer, number, title, edition, ...) for documents that were
indexed before the extraction existed.

The text comes from the chunks already stored in Qdrant (the ones that look like a cover page),
so the PDFs are not parsed again. Results are stored as a proposal pending the uploader's review.

  docker exec -w /app/src django python manage.py extract_metadata --dry-run
  docker exec -w /app/src django python manage.py extract_metadata
"""
import json
import re

from django.core.management.base import BaseCommand
from qdrant_client.models import FieldCondition, Filter, MatchValue

from specs.metadata import apply_metadata, extract_metadata
from specs.models import Document
from specs.rag_engine import DOC_KEY, TARGET_COLLECTION, _configure_models, get_qdrant_client

# Words that appear on a standard's cover page, in German, English and Spanish
COVER_CUES = re.compile(
    r"Ausgabe|Edition|Issue|Ersatz|Ersetzt|supersede|replaces|Konzernnorm|Group Standard|"
    r"©|Copyright|Alle Rechte|All rights|Freigegeben|Klass|Norma|Reemplaza", re.I)


def cover_text(document, client, max_chunks=3, limit=6000):
    """The stored chunks of a document that most look like its cover page, joined."""
    points, _ = client.scroll(
        TARGET_COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key=DOC_KEY, match=MatchValue(value=document.pk))]),
        limit=200, with_payload=True,
    )
    chunks = [json.loads(p.payload["_node_content"]).get("text", "") for p in points if "_node_content" in p.payload]
    chunks.sort(key=lambda text: -len(COVER_CUES.findall(text)))
    return "\n\n".join(chunks[:max_chunks])[:limit]


class Command(BaseCommand):
    help = "Extract standard metadata for indexed documents. / Extrae los metadatos de las normas ya indexadas."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show the results without saving. / Muestra los resultados sin guardar.")
        parser.add_argument("--all", action="store_true",
                            help="Also redo documents already extracted but not confirmed. / Rehace también los no confirmados.")

    def say(self, es, en):
        """Output is shown in Spanish and English."""
        self.stdout.write(f"{es} / {en}")

    def handle(self, *args, **options):
        _configure_models()
        client = get_qdrant_client()
        documents = Document.objects.filter(is_indexed=True)
        if options["all"]:
            documents = documents.exclude(metadata_status=Document.METADATA_CONFIRMED)
        else:
            documents = documents.filter(metadata_status=Document.METADATA_NONE)

        self.say(f"{documents.count()} documentos por procesar", f"{documents.count()} documents to process")
        for document in documents.order_by("id"):
            text = cover_text(document, client)
            metadata = extract_metadata(text) if text else None
            if metadata:
                self.say(f"* {document.id} {document.filename[:50]}: {metadata['issuer']} {metadata['number']} "
                         f"({metadata['edition_date'] or 'sin fecha'})",
                         f"* {document.id} {document.filename[:50]}: {metadata['issuer']} {metadata['number']} "
                         f"({metadata['edition_date'] or 'no date'})")
            else:
                self.say(f"* {document.id} {document.filename[:50]}: no se pudo extraer",
                         f"* {document.id} {document.filename[:50]}: extraction failed")
            if not options["dry_run"]:
                apply_metadata(document, metadata)
        self.say("Simulación: no se ha guardado nada." if options["dry_run"] else "Hecho.",
                 "Dry run: nothing was saved." if options["dry_run"] else "Done.")
