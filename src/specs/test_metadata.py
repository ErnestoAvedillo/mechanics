"""
Tests for the standard's metadata: normalisation, validation of the LLM answer, the review screen
and the guarantee that a failed extraction never blocks indexing.

Run: docker exec -w /app/src django python manage.py test specs.test_metadata
The LLM, MongoDB and Qdrant are mocked; only the database is real (a test database).
"""
import json
from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from specs.metadata import (
    apply_metadata, extract_metadata, normalize_issuer, normalize_number, parse_edition_date, parse_extraction,
)
from specs.models import Document, UserDocument
from specs.test_document_sharing import make_document


class NormalizationTests(TestCase):
    def test_number_loses_the_edition_but_keeps_the_part(self):
        cases = {
            "gs90010-1:2023-05": "GS 90010-1",
            "TL  245 : 2025-12": "TL 245",
            "GS 90010-1": "GS 90010-1",
            "DIN EN ISO 6892-1:2019-12": "DIN EN ISO 6892-1",
            "ISO 6892-1": "ISO 6892-1",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_number(raw), expected, raw)

    def test_chinese_standards_lose_the_trailing_year(self):
        cases = {
            "GB/T 10125—2021": "GB/T 10125",       # em dash, as printed in Chinese standards
            "GB / T 2423.17-2008": "GB/T 2423.17",
            "QC/T 413-2002": "QC/T 413",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_number(raw), expected, raw)

    def test_issuer_aliases_including_chinese_oems(self):
        cases = {
            "Volkswagen AG": "VW", "BMW Group": "BMW", "Mercedes-Benz": "MB",
            "byd": "BYD", "BYD Auto": "BYD", "比亚迪": "BYD",
            "Great Wall Motor": "GWM", "Geely Automobile": "Geely", "SAIC Motor": "SAIC",
            "ISO": "ISO", "din": "DIN", "gb": "GB",
            "Some Unknown Company GmbH": "Some Unknown Company GmbH",
            "": "",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_issuer(raw), expected, raw)

    def test_edition_dates(self):
        self.assertEqual(parse_edition_date("2023-04"), date(2023, 4, 1))
        self.assertEqual(parse_edition_date("2025"), date(2025, 1, 1))
        self.assertEqual(parse_edition_date("2024-02-15"), date(2024, 2, 15))
        self.assertEqual(parse_edition_date("2023/4"), date(2023, 4, 1))
        for bad in ("13-2020", "2023-13", "abc", "", None):
            self.assertIsNone(parse_edition_date(bad), bad)


class ParseExtractionTests(TestCase):
    GOOD = {"issuer": "Volkswagen AG", "number": "TL 245:2025-12", "title": "Zinc flake", "edition_date": "2025-12",
            "supersedes": ["TL 245:2018-08"], "language": "DE", "copyright_notice": "© Volkswagen AG"}

    def test_a_good_answer_is_normalised(self):
        meta = parse_extraction(json.dumps(self.GOOD))
        self.assertEqual(meta["issuer"], "VW")
        self.assertEqual(meta["number"], "TL 245")
        self.assertEqual(meta["edition_date"], date(2025, 12, 1))
        self.assertEqual(meta["language"], "de")
        self.assertEqual(meta["supersedes"], ["TL 245:2018-08"])

    def test_json_surrounded_by_text_is_found(self):
        self.assertEqual(parse_extraction("Sure! Here you go:\n```json\n" + json.dumps(self.GOOD) + "\n```")["number"], "TL 245")

    def test_unusable_answers_return_none(self):
        for bad in ("", "I cannot do that", "{not json}", "[1, 2]", None):
            self.assertIsNone(parse_extraction(bad), bad)

    def test_null_like_values_become_empty(self):
        meta = parse_extraction(json.dumps({"issuer": "VW", "number": "TL 1", "title": "null", "language": "n/a",
                                            "copyright_notice": None, "supersedes": "none", "edition_date": "soon"}))
        self.assertEqual((meta["title"], meta["language"], meta["copyright_notice"]), ("", "", ""))
        self.assertEqual(meta["supersedes"], [])
        self.assertIsNone(meta["edition_date"])

    def test_a_failing_llm_gives_none_instead_of_raising(self):
        with patch("specs.metadata.Settings") as settings:
            settings.llm.complete.side_effect = RuntimeError("API down")
            with self.assertLogs("specs.metadata", level="ERROR"):
                self.assertIsNone(extract_metadata("some text"))

    def test_extraction_asks_for_temperature_zero(self):
        with patch("specs.metadata.Settings") as settings:
            settings.llm.complete.return_value = json.dumps(self.GOOD)
            extract_metadata("some text")
        self.assertEqual(settings.llm.complete.call_args.kwargs.get("temperature"), 0)


class ApplyMetadataTests(TestCase):
    def test_a_proposal_is_stored_as_pending_review(self):
        document = make_document(b"a")
        ok = apply_metadata(document, parse_extraction(json.dumps(ParseExtractionTests.GOOD)))
        document.refresh_from_db()
        self.assertTrue(ok)
        self.assertEqual((document.spec_issuer, document.spec_number), ("VW", "TL 245"))
        self.assertEqual(document.metadata_status, Document.METADATA_PENDING)

    def test_nothing_usable_marks_the_extraction_as_failed(self):
        for metadata in (None, {"issuer": "", "number": "TL 1"}, {"issuer": "VW", "number": ""}):
            document = make_document(b"b" + str(metadata).encode())
            self.assertFalse(apply_metadata(document, metadata))
            document.refresh_from_db()
            self.assertEqual(document.metadata_status, Document.METADATA_FAILED)
            self.assertEqual(document.spec_number, "")


class ReviewViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.document = make_document(b"r", uploaded_by=self.owner, spec_issuer="VW", spec_number="TL 245",
                                      metadata_status=Document.METADATA_PENDING)
        self.owner_entry = UserDocument.objects.create(user=self.owner, document=self.document, filename="r.pdf", mongo_id="1")
        self.other_entry = UserDocument.objects.create(user=self.other, document=self.document, filename="r.pdf", mongo_id="1")
        self.data = {"spec_issuer": "Volkswagen AG", "spec_number": "tl245:2025-12", "title": "Zinc flake",
                     "edition_date": "2025-12-01", "language": "de"}

    def post(self, user, entry, data=None):
        self.client.force_login(user)
        return self.client.post(f"/specs/handling/review/{entry.id}/", data or self.data)

    def test_owner_confirms_and_the_values_are_normalised(self):
        response = self.post(self.owner, self.owner_entry)
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_CONFIRMED)
        self.assertEqual((self.document.spec_issuer, self.document.spec_number, self.document.language), ("VW", "TL 245", "de"))
        self.assertEqual(self.document.edition_date, date(2025, 12, 1))

    def test_another_user_with_access_cannot_change_it(self):
        self.post(self.other, self.other_entry)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)
        self.assertEqual(self.document.spec_number, "TL 245")
        self.assertEqual(self.document.title, "")

    def test_another_user_sees_it_read_only(self):
        self.client.force_login(self.other)
        page = self.client.get(f"/specs/handling/review/{self.other_entry.id}/").content.decode()
        self.assertIn("disabled", page)
        self.assertNotIn("Confirmar metadatos", page)

    def test_issuer_and_number_are_required(self):
        response = self.post(self.owner, self.owner_entry, {**self.data, "spec_number": "", "spec_issuer": ""})
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)

    def test_a_user_cannot_open_another_users_entry(self):
        stranger = User.objects.create_user("stranger", password="x")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(f"/specs/handling/review/{self.owner_entry.id}/").status_code, 404)

    def test_if_the_uploader_account_is_gone_the_first_user_with_access_takes_over(self):
        self.owner.delete()
        self.document.refresh_from_db()
        self.assertIsNone(self.document.uploaded_by_id)
        self.assertTrue(self.document.can_be_edited_by(self.other))


class IndexingMetadataTests(TestCase):
    """index_document_to_rag stores the metadata proposal and never lets it break indexing."""

    def setUp(self):
        from llama_index.core import Document as LlamaDocument
        self.user = User.objects.create_user("uploader", password="x")
        self.document = make_document(b"i", uploaded_by=self.user)
        self.entry = UserDocument.objects.create(user=self.user, document=self.document, filename="i.pdf", mongo_id="1")
        self.pages = [LlamaDocument(text="Konzernnorm TL 245 Ausgabe 2025-12")]
        self.addCleanup(patch.stopall)
        patch("specs.rag_engine._configure_models").start()
        patch("specs.rag_engine.MongoClient").start()
        patch("specs.rag_engine.gridfs.GridFS").start().return_value.get.return_value.read.return_value = b"%PDF"
        parser = patch("specs.rag_engine.LlamaParse").start()
        parser.return_value.load_data.side_effect = lambda path: self.pages
        for name in ("get_qdrant_client", "ensure_collection", "delete_document_vectors",
                     "QdrantVectorStore", "StorageContext", "VectorStoreIndex"):
            patch(f"specs.rag_engine.{name}").start()
        self.extract = patch("specs.rag_engine.extract_metadata").start()
        self.extract.return_value = parse_extraction(json.dumps(ParseExtractionTests.GOOD))

    def index(self):
        from specs.rag_engine import index_document_to_rag
        with override_settings(LLAMA_CLOUD_API_KEY="test"):
            return index_document_to_rag(self.entry.id)

    def test_metadata_and_company_are_filled_after_indexing(self):
        ok, _msg = self.index()
        self.assertTrue(ok)
        self.document.refresh_from_db()
        self.entry.refresh_from_db()
        self.assertTrue(self.document.is_indexed)
        self.assertEqual((self.document.spec_issuer, self.document.spec_number), ("VW", "TL 245"))
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)
        self.assertEqual(self.entry.company, "VW")

    def test_a_company_typed_by_the_user_is_kept(self):
        UserDocument.objects.filter(pk=self.entry.pk).update(company="My company")
        self.index()
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.company, "My company")

    def test_a_failed_extraction_does_not_block_indexing(self):
        self.extract.return_value = None
        ok, _msg = self.index()
        self.assertTrue(ok)
        self.document.refresh_from_db()
        self.assertTrue(self.document.is_indexed)
        self.assertEqual(self.document.metadata_status, Document.METADATA_FAILED)

    def test_confirmed_metadata_is_never_overwritten_by_a_retry(self):
        Document.objects.filter(pk=self.document.pk).update(
            metadata_status=Document.METADATA_CONFIRMED, spec_issuer="BMW", spec_number="GS 1")
        self.index()
        self.document.refresh_from_db()
        self.assertEqual((self.document.spec_issuer, self.document.spec_number), ("BMW", "GS 1"))
        self.assertEqual(self.document.metadata_status, Document.METADATA_CONFIRMED)
        self.extract.assert_not_called()
