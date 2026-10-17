"""
Indexes the documents that have no vectors yet (is_indexed is False), one after the other.

Typical use after a migration: documents uploaded with an older version were indexed with other
models or in other collections, so `backfill_documents` leaves them pending. Each document takes
about a minute (OCR with LlamaParse, then embeddings with Nebius Token Factory). Indexing also
extracts the standard's metadata, which the uploader then confirms in the review screen.

  docker exec -w /app/src django python manage.py index_pending --dry-run
  docker exec -w /app/src django python manage.py index_pending
"""
from django.core.management.base import BaseCommand

from specs.models import Document
from specs.rag_engine import index_document_to_rag


class Command(BaseCommand):
    help = "Index documents that have no vectors yet. / Indexa los documentos que aún no tienen vectores."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="List what would be indexed without doing it. / Lista lo pendiente sin indexar.")

    def say(self, es, en):
        """Output is shown in Spanish and English."""
        self.stdout.write(f"{es} / {en}")

    def handle(self, *args, **options):
        pending = Document.objects.filter(is_indexed=False).order_by("id")
        self.say(f"{pending.count()} documentos pendientes", f"{pending.count()} pending documents")
        failures = 0
        for document in pending:
            entry = document.accesses.order_by("id").first()
            if entry is None:
                self.say(f"* {document.id} {document.filename[:50]}: nadie tiene acceso, se omite",
                         f"* {document.id} {document.filename[:50]}: nobody has access, skipped")
                continue
            if options["dry_run"]:
                self.say(f"* {document.id} {document.filename[:50]}: se indexaría",
                         f"* {document.id} {document.filename[:50]}: would be indexed")
                continue
            ok, message = index_document_to_rag(entry.id)
            failures += not ok
            self.say(f"* {document.id} {document.filename[:50]}: {'OK' if ok else 'ERROR'} {message}",
                     f"* {document.id} {document.filename[:50]}: {'OK' if ok else 'ERROR'} {message}")
        self.say("Simulación: no se ha indexado nada." if options["dry_run"] else
                 f"Hecho ({failures} con error).",
                 "Dry run: nothing was indexed." if options["dry_run"] else f"Done ({failures} failed).")
