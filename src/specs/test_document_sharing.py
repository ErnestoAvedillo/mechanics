"""
Tests for shared documents: one file stored and indexed once, per-user access,
isolation between users, and cleanup when the last access is removed.

Run: docker exec -w /app/src django python manage.py test specs.test_document_sharing
MongoDB, Qdrant and the indexing thread are mocked; only the database is real (a test database).
"""
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from specs.models import Document, UserDocument
from specs.rag_engine import DOC_KEY
from specs.rag_engine import accessible_document_ids

PDF_A = b"%PDF-1.4 content of the first file"
PDF_B = b"%PDF-1.4 content of the second file"


def make_document(content=b"x", **kwargs):
    import hashlib
    defaults = dict(file_hash=hashlib.sha256(content).hexdigest(), mongo_id=str(ObjectId()), filename="f.pdf")
    defaults.update(kwargs)
    return Document.objects.create(**defaults)


class UploadSharingTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        fs_patch = patch("specs.views._gridfs")
        self.fs = fs_patch.start().return_value
        self.fs.put.side_effect = lambda *a, **k: ObjectId()
        thread_patch = patch("specs.views.threading.Thread")
        self.thread = thread_patch.start()
        self.addCleanup(patch.stopall)

    def upload(self, user, content, name="spec.pdf"):
        self.client.force_login(user)
        response = self.client.post("/specs/upload/", {
            "pdf_file": [SimpleUploadedFile(name, content, content_type="application/pdf")],
            "company": "",
        })
        self.assertEqual(response.status_code, 302)
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_new_file_creates_one_document_and_starts_indexing(self):
        self.upload(self.alice, PDF_A)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(UserDocument.objects.filter(user=self.alice).count(), 1)
        self.assertEqual(self.thread.return_value.start.call_count, 1)
        self.assertEqual(self.fs.put.call_count, 1)

    def test_same_file_from_another_user_is_shared_not_reprocessed(self):
        self.upload(self.alice, PDF_A)
        Document.objects.update(is_indexed=True)  # alice's indexing finished
        messages = self.upload(self.bob, PDF_A, name="other-name.pdf")

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(UserDocument.objects.count(), 2)
        self.assertEqual(self.fs.put.call_count, 1, "the PDF must not be stored twice")
        self.assertEqual(self.thread.return_value.start.call_count, 1, "it must not be indexed twice")
        self.assertTrue(any("ya estaba analizado" in m for m in messages))

    def test_same_user_uploading_again_is_ignored(self):
        self.upload(self.alice, PDF_A)
        messages = self.upload(self.alice, PDF_A)
        self.assertEqual(UserDocument.objects.filter(user=self.alice).count(), 1)
        self.assertEqual(self.thread.return_value.start.call_count, 1)
        self.assertTrue(any("ya está en tu biblioteca" in m for m in messages))

    def test_company_label_is_reused_for_the_same_file(self):
        self.upload(self.alice, PDF_A)
        UserDocument.objects.filter(user=self.alice).update(company="VW")
        self.upload(self.bob, PDF_A)
        self.assertEqual(UserDocument.objects.get(user=self.bob).company, "VW")


class AccessIsolationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.doc_a = make_document(b"a")
        self.doc_b = make_document(b"b")
        self.shared = make_document(b"shared")
        for user, doc in ((self.alice, self.doc_a), (self.bob, self.doc_b),
                          (self.alice, self.shared), (self.bob, self.shared)):
            UserDocument.objects.create(user=user, document=doc, filename=doc.filename, mongo_id=doc.mongo_id)

    def test_each_user_only_sees_their_own_documents(self):
        self.assertEqual(set(accessible_document_ids(self.alice.id)), {self.doc_a.id, self.shared.id})
        self.assertEqual(set(accessible_document_ids(self.bob.id)), {self.doc_b.id, self.shared.id})

    def test_user_without_documents_sees_nothing(self):
        carol = User.objects.create_user("carol", password="x")
        self.assertEqual(accessible_document_ids(carol.id), [])

    def test_unlinked_legacy_rows_are_not_searchable(self):
        UserDocument.objects.create(user=self.alice, document=None, filename="old.pdf", mongo_id="1" * 24)
        self.assertEqual(set(accessible_document_ids(self.alice.id)), {self.doc_a.id, self.shared.id})

    def test_user_cannot_view_or_delete_another_users_entry(self):
        entry = UserDocument.objects.get(user=self.alice, document=self.doc_a)
        self.client.force_login(self.bob)
        self.assertEqual(self.client.post(f"/specs/handling/delete/{entry.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/specs/handling/view/{entry.id}/").status_code, 404)
        self.assertTrue(UserDocument.objects.filter(pk=entry.pk).exists())


class DeleteTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.doc = make_document(b"shared")
        self.entry_a = UserDocument.objects.create(user=self.alice, document=self.doc, filename="s.pdf", mongo_id=self.doc.mongo_id)
        self.entry_b = UserDocument.objects.create(user=self.bob, document=self.doc, filename="s.pdf", mongo_id=self.doc.mongo_id)

    def test_document_survives_until_the_last_access_is_removed(self):
        with patch("specs.views.purge_document") as purge:
            self.client.force_login(self.alice)
            self.client.post(f"/specs/handling/delete/{self.entry_a.id}/")
            self.assertTrue(Document.objects.filter(pk=self.doc.pk).exists())
            purge.assert_not_called()

            self.client.force_login(self.bob)
            self.client.post(f"/specs/handling/delete/{self.entry_b.id}/")
            purge.assert_called_once()
            self.assertEqual(purge.call_args[0][0].pk, self.doc.pk)

    def test_purge_removes_vectors_pdf_and_row(self):
        from specs.views import purge_document
        pk = self.doc.pk  # Django clears the instance's pk when it deletes the row
        with patch("specs.views.delete_document_vectors") as vectors, patch("specs.views._gridfs") as fs:
            purge_document(self.doc)
        vectors.assert_called_once_with(pk)
        fs.return_value.delete.assert_called_once()
        self.assertFalse(Document.objects.filter(pk=pk).exists())

    def test_purge_still_deletes_the_row_if_cleanup_fails(self):
        from specs.views import purge_document
        pk = self.doc.pk
        with patch("specs.views.delete_document_vectors", side_effect=RuntimeError("qdrant down")), \
                patch("specs.views._gridfs", side_effect=RuntimeError("mongo down")), \
                self.assertLogs("specs.views", level="ERROR"):
            purge_document(self.doc)
        self.assertFalse(Document.objects.filter(pk=pk).exists())


class IndexingClaimTests(TestCase):
    def test_only_one_run_can_claim_a_document(self):
        doc = make_document(b"c")
        self.assertTrue(Document.claim_indexing(doc.pk))
        self.assertFalse(Document.claim_indexing(doc.pk))

    def test_an_indexed_document_cannot_be_claimed(self):
        doc = make_document(b"d", is_indexed=True)
        self.assertFalse(Document.claim_indexing(doc.pk))

    def test_a_stale_claim_can_be_retaken(self):
        old = timezone.now() - timedelta(minutes=Document.INDEXING_TIMEOUT_MINUTES + 1)
        doc = make_document(b"e", indexing_started_at=old)
        self.assertTrue(Document.claim_indexing(doc.pk))

    def test_a_failed_run_releases_the_claim_for_a_retry(self):
        from specs.rag_engine import index_document_to_rag
        doc = make_document(b"f")
        user = User.objects.create_user("dave", password="x")
        entry = UserDocument.objects.create(user=user, document=doc, filename="f.pdf", mongo_id=doc.mongo_id)
        with patch("specs.rag_engine._configure_models"), patch("specs.rag_engine.MongoClient"), \
                patch("specs.rag_engine.gridfs.GridFS") as grid:
            grid.return_value.get.side_effect = RuntimeError("mongo down")
            ok, _msg = index_document_to_rag(entry.id)
        self.assertFalse(ok)
        doc.refresh_from_db()
        self.assertIsNone(doc.indexing_started_at)
        self.assertFalse(doc.is_indexed)
        self.assertTrue(Document.claim_indexing(doc.pk))


class BackfillTests(TestCase):
    """The backfill links legacy rows to Documents, merging identical files and repeated entries."""

    def run_backfill(self, files, apply=True):
        from io import StringIO
        from django.core.management import call_command
        grid = MagicMock()
        grid.get.side_effect = lambda oid: MagicMock(read=lambda: files[str(oid)])
        qdrant = MagicMock()
        qdrant.collection_exists.return_value = False  # skip the Qdrant part
        out = StringIO()
        with patch("specs.management.commands.backfill_documents.MongoClient"), \
                patch("specs.management.commands.backfill_documents.gridfs.GridFS", return_value=grid), \
                patch("specs.management.commands.backfill_documents.get_qdrant_client", return_value=qdrant):
            call_command("backfill_documents", *(["--apply"] if apply else []), stdout=out)
        return out.getvalue()

    def legacy(self, user, mongo_id, name="a.pdf", company="", indexed=True):
        return UserDocument.objects.create(user=user, filename=name, company=company,
                                           mongo_id=mongo_id, is_indexed=indexed)

    def setUp(self):
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.m1, self.m2, self.m3 = (str(ObjectId()) for _ in range(3))

    def test_repeated_entries_of_the_same_user_are_merged(self):
        first = self.legacy(self.alice, self.m1)
        self.legacy(self.alice, self.m2, company="VW")  # same file uploaded twice by the same user
        self.run_backfill({self.m1: PDF_A, self.m2: PDF_A})

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(UserDocument.objects.filter(user=self.alice).count(), 1)
        first.refresh_from_db()
        self.assertEqual(first.document, Document.objects.get())
        self.assertEqual(first.company, "VW", "the label of the removed entry is kept")

    def test_same_file_of_two_users_shares_one_document(self):
        self.legacy(self.alice, self.m1)
        self.legacy(self.bob, self.m2)
        self.run_backfill({self.m1: PDF_A, self.m2: PDF_A})
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.get().accesses.count(), 2)

    def test_different_files_get_different_documents(self):
        self.legacy(self.alice, self.m1)
        self.legacy(self.alice, self.m3, name="b.pdf")
        self.run_backfill({self.m1: PDF_A, self.m3: PDF_B})
        self.assertEqual(Document.objects.count(), 2)

    def test_dry_run_changes_nothing_and_reports_the_merge(self):
        self.legacy(self.alice, self.m1)
        self.legacy(self.alice, self.m2)
        report = self.run_backfill({self.m1: PDF_A, self.m2: PDF_A}, apply=False)
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(UserDocument.objects.filter(document__isnull=True).count(), 2)
        self.assertIn("entrada repetida del mismo usuario", report)

    def test_running_it_twice_is_harmless(self):
        self.legacy(self.alice, self.m1)
        self.run_backfill({self.m1: PDF_A})
        self.run_backfill({self.m1: PDF_A})
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(UserDocument.objects.count(), 1)


class BackfillVectorsTests(BackfillTests):
    """The legacy `is_indexed` flag is not trusted: only vectors found in the current collection count."""

    def run_backfill_with_vectors(self, files, vectors_by_legacy_id, apply=True):
        """Like run_backfill, but the Qdrant collection exists and holds the given legacy vectors."""
        from io import StringIO
        from django.core.management import call_command
        grid = MagicMock()
        grid.get.side_effect = lambda oid: MagicMock(read=lambda: files[str(oid)])
        qdrant = MagicMock()
        qdrant.collection_exists.return_value = True
        points = []
        for legacy_id, point_ids in vectors_by_legacy_id.items():
            for point_id in point_ids:
                points.append(MagicMock(id=point_id, payload={"_node_content": json.dumps({"metadata": {"doc_id": legacy_id}})}))
        qdrant.scroll.return_value = (points, None)
        out = StringIO()
        with patch("specs.management.commands.backfill_documents.MongoClient"), \
                patch("specs.management.commands.backfill_documents.gridfs.GridFS", return_value=grid), \
                patch("specs.management.commands.backfill_documents.get_qdrant_client", return_value=qdrant):
            call_command("backfill_documents", *(["--apply"] if apply else []), stdout=out)
        return qdrant, out.getvalue()

    def test_a_legacy_row_flagged_indexed_without_vectors_stays_pending(self):
        self.legacy(self.alice, self.m1, indexed=True)  # flag says indexed, but no vectors exist
        _qdrant, report = self.run_backfill_with_vectors({self.m1: PDF_A}, {})
        self.assertFalse(Document.objects.get().is_indexed)
        self.assertIn("index_pending", report)

    def test_a_legacy_row_with_vectors_is_indexed_and_its_vectors_are_tagged(self):
        entry = self.legacy(self.alice, self.m1, indexed=False)  # even if the flag says otherwise
        qdrant, report = self.run_backfill_with_vectors({self.m1: PDF_A}, {entry.id: ["p1", "p2"]})
        document = Document.objects.get()
        self.assertTrue(document.is_indexed)
        self.assertNotIn("index_pending", report)
        payload_call = qdrant.set_payload.call_args
        self.assertEqual(payload_call.kwargs["points"], ["p1", "p2"])
        self.assertEqual(payload_call.kwargs["payload"], {DOC_KEY: document.pk})

    def test_the_duplicate_without_vectors_does_not_become_the_vectors_owner(self):
        first = self.legacy(self.alice, self.m1, indexed=True)
        second = self.legacy(self.bob, self.m2, indexed=True)
        qdrant, _report = self.run_backfill_with_vectors({self.m1: PDF_A, self.m2: PDF_A}, {second.id: ["p9"]})
        self.assertTrue(Document.objects.get().is_indexed)
        self.assertEqual(qdrant.set_payload.call_args.kwargs["points"], ["p9"])
        qdrant.delete.assert_not_called()


class IndexPendingTests(TestCase):
    def run_command(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        with patch("specs.management.commands.index_pending.index_document_to_rag", return_value=(True, "ok")) as index:
            call_command("index_pending", *args, stdout=out)
        return index, out.getvalue()

    def setUp(self):
        self.user = User.objects.create_user("u", password="x")
        self.pending = make_document(b"p")
        self.indexed = make_document(b"i", is_indexed=True)
        self.orphan = make_document(b"o")
        self.entry = UserDocument.objects.create(user=self.user, document=self.pending, filename="p.pdf", mongo_id="1")
        UserDocument.objects.create(user=self.user, document=self.indexed, filename="i.pdf", mongo_id="2")

    def test_only_pending_documents_with_an_owner_are_indexed(self):
        index, report = self.run_command()
        index.assert_called_once_with(self.entry.id)
        self.assertIn("nobody has access", report)

    def test_dry_run_indexes_nothing(self):
        index, report = self.run_command("--dry-run")
        index.assert_not_called()
        self.assertIn("would be indexed", report)
