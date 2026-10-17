"""
Links the legacy UserDocument rows to the new Document model.

For every UserDocument without a Document it computes the SHA-256 of the PDF stored in
MongoDB, groups identical files into a single Document, and tags the existing Qdrant
vectors with the new `specs_document_id` so the access filter finds them. Vectors of
duplicate copies are removed. Nothing is deleted from MongoDB: duplicate PDFs are only reported.

Legacy vectors are identified through the JSON stored in each point (`_node_content`),
because LlamaIndex overwrites the top-level `doc_id` payload key with its own node id.

Dry run by default. Make a backup first (make backup), then run with --apply:
  docker exec -w /app/src django python manage.py backfill_documents
  docker exec -w /app/src django python manage.py backfill_documents --apply
"""
import hashlib
import json

import gridfs
from bson import ObjectId
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from pymongo import MongoClient
from qdrant_client.models import PointIdsList

from specs.models import Document, UserDocument
from specs.rag_engine import DOC_KEY, TARGET_COLLECTION, get_qdrant_client


def legacy_points(qdrant):
    """Maps each legacy UserDocument id to the ids of its not yet tagged Qdrant points."""
    mapping = {}
    offset = None
    while True:
        points, offset = qdrant.scroll(TARGET_COLLECTION, limit=256, offset=offset, with_payload=True)
        for point in points:
            if DOC_KEY in point.payload:
                continue  # already tagged
            node = json.loads(point.payload.get("_node_content") or "{}")
            legacy_id = (node.get("metadata") or {}).get("doc_id")
            if isinstance(legacy_id, int):
                mapping.setdefault(legacy_id, []).append(point.id)
        if offset is None:
            return mapping


class Command(BaseCommand):
    help = "Link legacy UserDocument rows to Document and tag Qdrant vectors. / Vincula UserDocument antiguos a Document."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Apply the changes (default is a dry run). / Aplicar cambios (por defecto solo informa).")

    def say(self, es, en):
        """Output is shown in Spanish and English."""
        self.stdout.write(f"{es} / {en}")

    def handle(self, *args, **options):
        apply = options["apply"]
        fs = gridfs.GridFS(MongoClient(settings.MONGO_URL)[settings.MONGO_DB_NAME])
        qdrant = get_qdrant_client()
        has_collection = qdrant.collection_exists(TARGET_COLLECTION)
        points_by_legacy_id = legacy_points(qdrant) if has_collection else {}

        pending = list(UserDocument.objects.filter(document__isnull=True).order_by("id"))
        self.say(f"{'APLICANDO' if apply else 'SIMULACIÓN'}: {len(pending)} documentos sin vincular",
                 f"{'APPLYING' if apply else 'DRY RUN'}: {len(pending)} unlinked documents")

        groups = {}
        for ud in pending:
            try:
                data = fs.get(ObjectId(ud.mongo_id)).read()
            except Exception as exc:
                self.say(f"  OMITIDO id={ud.id} ({ud.filename}): no se pudo leer de MongoDB: {exc}",
                         f"  SKIPPED id={ud.id} ({ud.filename}): could not read from MongoDB: {exc}")
                continue
            groups.setdefault(hashlib.sha256(data).hexdigest(), []).append(ud)

        unknown = set(points_by_legacy_id) - {ud.id for ud in pending}
        if unknown:
            total = sum(len(points_by_legacy_id[i]) for i in unknown)
            self.say(f"  aviso: {total} vectores pertenecen a entradas que ya no existen (ids {sorted(unknown)}); no se tocan",
                     f"  note: {total} vectors belong to entries that no longer exist (ids {sorted(unknown)}); left untouched")

        if has_collection and apply:
            try:
                qdrant.create_payload_index(TARGET_COLLECTION, DOC_KEY, "integer")
            except Exception as exc:  # already exists
                self.say(f"  (índice {DOC_KEY}: {exc})", f"  ({DOC_KEY} index: {exc})")

        needs_indexing = 0
        for file_hash, rows in groups.items():
            existing = Document.objects.filter(file_hash=file_hash).first()
            names = ", ".join(f"id={r.id}" for r in rows)

            # Which legacy row's vectors become the document's vectors. Only vectors that really exist
            # in the current collection count: the old `is_indexed` flag cannot be trusted, because
            # older deployments indexed into other collections (other models, other vector sizes).
            with_vectors = [r for r in rows if points_by_legacy_id.get(r.id)]
            if existing and existing.is_indexed:
                keeper = None
            else:
                keeper = with_vectors[0] if with_vectors else None
            if not keeper and not (existing and existing.is_indexed):
                needs_indexing += 1
            primary_row = keeper or rows[0]
            primary_mongo_id = existing.mongo_id if existing else primary_row.mongo_id

            self.say(f"* archivo {file_hash[:12]}…: {len(rows)} entrada(s) [{names}]",
                     f"* file {file_hash[:12]}…: {len(rows)} entr{'y' if len(rows) == 1 else 'ies'} [{names}]")
            for r in rows:
                count = len(points_by_legacy_id.get(r.id, []))
                if r is keeper:
                    action_es, action_en = "conserva sus vectores", "keeps its vectors"
                elif count:
                    action_es, action_en = "se eliminan sus vectores", "its vectors are removed"
                else:
                    action_es, action_en = "sin vectores en la colección actual", "no vectors in the current collection"
                self.say(f"    id={r.id} {r.filename}: {count} vectores, {action_es}",
                         f"    id={r.id} {r.filename}: {count} vectors, {action_en}")
                if r.mongo_id != primary_mongo_id:
                    self.say(f"    aviso: PDF duplicado en MongoDB ({r.mongo_id}); no se borra",
                             f"    note: duplicate PDF in MongoDB ({r.mongo_id}); it is not deleted")

            # A user can hold a document only once: repeated entries of the same user are merged
            ordered = [primary_row] + [r for r in rows if r is not primary_row]
            kept_by_user = {}
            merged = []
            for r in ordered:
                if r.user_id in kept_by_user:
                    merged.append((r, kept_by_user[r.user_id]))
                else:
                    kept_by_user[r.user_id] = r
            for dup, kept in merged:
                self.say(f"    entrada repetida del mismo usuario: se elimina id={dup.id} y se conserva id={kept.id}",
                         f"    repeated entry of the same user: id={dup.id} is removed and id={kept.id} is kept")
            if not apply:
                continue

            document = existing
            if document is None:
                document = Document.objects.create(
                    file_hash=file_hash, mongo_id=primary_row.mongo_id, filename=primary_row.filename,
                    is_indexed=bool(keeper))
            elif keeper and not document.is_indexed:
                document.is_indexed = True
                document.save(update_fields=["is_indexed"])

            # Qdrant first (idempotent), then the database
            if has_collection:
                for r in rows:
                    ids = points_by_legacy_id.get(r.id, [])
                    if not ids:
                        continue
                    if r is keeper:
                        qdrant.set_payload(TARGET_COLLECTION, payload={DOC_KEY: document.pk}, points=ids)
                    else:
                        qdrant.delete(TARGET_COLLECTION, points_selector=PointIdsList(points=ids))
            with transaction.atomic():
                for dup, kept in merged:
                    if not kept.company and dup.company:
                        kept.company = dup.company  # keep the label the user had given
                    dup.delete()
                for kept in kept_by_user.values():
                    kept.document = document
                    kept.save(update_fields=["document", "company"])

        if needs_indexing:
            self.say(f"{needs_indexing} documento(s) no tienen vectores en la colección actual: "
                     f"ejecuta 'manage.py index_pending' para indexarlos.",
                     f"{needs_indexing} document(s) have no vectors in the current collection: "
                     f"run 'manage.py index_pending' to index them.")
        self.say("Hecho." if apply else "Simulación terminada: no se ha cambiado nada. Usa --apply para aplicar.",
                 "Done." if apply else "Dry run finished: nothing was changed. Use --apply to apply.")
