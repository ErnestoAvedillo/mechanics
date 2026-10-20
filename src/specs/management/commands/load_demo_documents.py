"""
Loads the PDFs of a folder into the shared demo library (see specs/demo.py): stores each file,
creates its Document for the demo owner and indexes it once. Safe to repeat: files that are
already loaded are skipped, and unfinished indexing is retried.

  docker exec -w /app/src django python manage.py load_demo_documents --dir /app/pdf
"""
import hashlib
from pathlib import Path

from bson.objectid import ObjectId
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from specs.demo import get_demo_owner
from specs.models import Document, UserDocument
from specs.rag_engine import index_document_to_rag
from specs.views import _gridfs


class Command(BaseCommand):
    help = "Load and index the demo documents. / Carga e indexa los documentos de la demo."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default="pdf", help="Folder with the PDFs. / Carpeta con los PDF.")

    def say(self, es, en):
        """Output is shown in Spanish and English."""
        self.stdout.write(f"{es} / {en}")

    def handle(self, *args, **options):
        folder = Path(options["dir"])
        files = sorted(folder.glob("*.pdf"))
        if not files:
            raise CommandError(f"No hay PDF en {folder} / No PDFs in {folder}")
        owner = get_demo_owner()
        fs = _gridfs()
        for path in files:
            data = path.read_bytes()
            file_hash = hashlib.sha256(data).hexdigest()
            document = Document.objects.filter(file_hash=file_hash).first()
            if document is None:
                mongo_id = fs.put(data, filename=path.name)
                try:
                    document = Document.objects.create(file_hash=file_hash, mongo_id=str(mongo_id),
                                                       filename=path.name, uploaded_by=owner)
                except Exception:
                    fs.delete(ObjectId(mongo_id))
                    raise
            with transaction.atomic():
                entry, _ = UserDocument.objects.get_or_create(
                    user=owner, document=document,
                    defaults={"filename": path.name, "mongo_id": document.mongo_id})
            if document.is_indexed:
                self.say(f"* {path.name}: ya indexado", f"* {path.name}: already indexed")
                continue
            ok, message = index_document_to_rag(entry.id)
            self.say(f"* {path.name}: {'OK' if ok else 'ERROR'} {message}",
                     f"* {path.name}: {'OK' if ok else 'ERROR'} {message}")
