"""
Tests for the per-library resolution of editions and languages (versions.py), its use by the
chat, the document list and the review form, and the original-language detection.

Run: docker exec -w /app/src django python manage.py test specs.test_versions
"""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from specs.metadata import parse_extraction
from specs.models import Document, UserDocument
from specs.rag_engine import DOC_KEY, accessible_document_ids
from specs.versions import (
    CURRENT, DUPLICATE, SUPERSEDED, TRANSLATION, TRANSLATION_ONLY, UNREVIEWED, library_state, searched_document_ids,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class LibraryMixin:
    """Helpers to build a user's library."""
    counter = 0

    def make(self, user, issuer="VW", number="TL 245", edition=date(2025, 12, 1), language="de", original=None,
             confirmed=True, minutes=0):
        """A document the user has access to. `original` defaults to the document's own language."""
        LibraryMixin.counter += 1
        document = Document.objects.create(
            file_hash=hashlib.sha256(str(LibraryMixin.counter).encode()).hexdigest(), mongo_id=str(LibraryMixin.counter),
            filename=f"{number}-{language}-{LibraryMixin.counter}.pdf", spec_issuer=issuer, spec_number=number,
            edition_date=edition, language=language,
            original_language=language if original is None else original,
            metadata_status=Document.METADATA_CONFIRMED if confirmed else Document.METADATA_PENDING)
        Document.objects.filter(pk=document.pk).update(upload_date=BASE_TIME + timedelta(minutes=minutes))
        document.refresh_from_db()
        self.give_access(user, document)
        return document

    def give_access(self, user, document):
        UserDocument.objects.get_or_create(user=user, document=document, defaults={
            "filename": document.filename, "mongo_id": document.mongo_id})

    def state(self, user, document):
        return library_state(user.id)[document.id].state


class EditionTests(LibraryMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")

    def test_a_single_document_is_current(self):
        doc = self.make(self.user)
        self.assertEqual(self.state(self.user, doc), CURRENT)

    def test_a_newer_edition_supersedes_the_older_one(self):
        old = self.make(self.user, edition=date(2018, 8, 1))
        new = self.make(self.user, edition=date(2025, 12, 1))
        states = library_state(self.user.id)
        self.assertEqual(states[new.id].state, CURRENT)
        self.assertEqual(tuple(states[old.id]), (SUPERSEDED, new.id))
        self.assertEqual(searched_document_ids(self.user.id), [new.id])

    def test_different_standards_do_not_affect_each_other(self):
        a = self.make(self.user, number="TL 245", edition=date(2018, 1, 1))
        b = self.make(self.user, number="TL 244", edition=date(2025, 1, 1))
        c = self.make(self.user, issuer="BMW", number="TL 245", edition=date(2020, 1, 1))
        self.assertEqual({self.state(self.user, d) for d in (a, b, c)}, {CURRENT})

    def test_issuer_and_number_are_compared_ignoring_case(self):
        old = self.make(self.user, issuer="vw", number="tl 245", edition=date(2018, 1, 1))
        new = self.make(self.user, issuer="VW", number="TL 245", edition=date(2025, 1, 1))
        self.assertEqual(self.state(self.user, old), SUPERSEDED)
        self.assertEqual(self.state(self.user, new), CURRENT)

    def test_unconfirmed_documents_are_always_searched_and_replace_nothing(self):
        confirmed_old = self.make(self.user, edition=date(2018, 1, 1))
        unconfirmed_new = self.make(self.user, edition=date(2025, 1, 1), confirmed=False)
        self.assertEqual(self.state(self.user, unconfirmed_new), UNREVIEWED)
        self.assertEqual(self.state(self.user, confirmed_old), CURRENT)

    def test_a_document_without_number_is_unreviewed_even_if_confirmed(self):
        doc = self.make(self.user, number="")
        self.assertEqual(self.state(self.user, doc), UNREVIEWED)

    def test_a_confirmed_document_without_date_is_never_hidden(self):
        undated = self.make(self.user, edition=None)
        dated = self.make(self.user, edition=date(2025, 1, 1))
        self.assertEqual(self.state(self.user, undated), CURRENT)
        self.assertEqual(self.state(self.user, dated), CURRENT)

    def test_only_undated_documents_are_all_current(self):
        docs = [self.make(self.user, edition=None) for _ in range(2)]
        self.assertEqual({self.state(self.user, d) for d in docs}, {CURRENT})


class LanguageTests(LibraryMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")

    def test_the_original_is_used_and_the_translation_hidden(self):
        original = self.make(self.user, language="de", original="de", minutes=5)
        translation = self.make(self.user, language="en", original="de", minutes=0)
        states = library_state(self.user.id)
        self.assertEqual(states[original.id].state, CURRENT)
        self.assertEqual(tuple(states[translation.id]), (TRANSLATION, original.id))
        self.assertEqual(searched_document_ids(self.user.id), [original.id])

    def test_an_older_translation_is_superseded_by_the_newer_original(self):
        translation = self.make(self.user, language="en", original="de", edition=date(2018, 8, 1))
        original = self.make(self.user, language="de", original="de", edition=date(2025, 12, 1))
        states = library_state(self.user.id)
        self.assertEqual(tuple(states[translation.id]), (SUPERSEDED, original.id))
        self.assertEqual(states[original.id].state, CURRENT)

    def test_without_the_original_the_translation_is_used_and_flagged(self):
        translation = self.make(self.user, language="en", original="de")
        self.assertEqual(self.state(self.user, translation), TRANSLATION_ONLY)
        self.assertEqual(searched_document_ids(self.user.id), [translation.id])

    def test_a_newer_translation_beats_an_older_original(self):
        old_original = self.make(self.user, language="de", original="de", edition=date(2018, 8, 1))
        new_translation = self.make(self.user, language="en", original="de", edition=date(2025, 12, 1))
        states = library_state(self.user.id)
        self.assertEqual(states[new_translation.id].state, TRANSLATION_ONLY)
        self.assertEqual(tuple(states[old_original.id]), (SUPERSEDED, new_translation.id))

    def test_among_several_translations_the_earliest_upload_language_is_used(self):
        first = self.make(self.user, language="en", original="de", minutes=0)
        second = self.make(self.user, language="fr", original="de", minutes=10)
        states = library_state(self.user.id)
        self.assertEqual(states[first.id].state, TRANSLATION_ONLY)
        self.assertEqual(tuple(states[second.id]), (TRANSLATION, first.id))

    def test_a_missing_original_language_counts_as_original(self):
        doc = self.make(self.user, language="de", original="")
        self.assertFalse(doc.is_translation)
        self.assertEqual(self.state(self.user, doc), CURRENT)

    def test_the_same_variant_twice_flags_a_duplicate_and_keeps_the_latest_upload(self):
        older = self.make(self.user, minutes=0)
        newer = self.make(self.user, minutes=30)
        states = library_state(self.user.id)
        self.assertEqual(states[newer.id].state, CURRENT)
        self.assertEqual(tuple(states[older.id]), (DUPLICATE, newer.id))


class PerLibraryTests(LibraryMixin, TestCase):
    """Obsolescence depends on what each user has, not on what other users upload."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")

    def test_a_newer_edition_in_another_library_does_not_hide_mine(self):
        old = self.make(self.alice, edition=date(2018, 8, 1))
        new = self.make(self.bob, edition=date(2025, 12, 1))
        self.give_access(self.bob, old)   # bob has both editions, alice only the old one

        self.assertEqual(self.state(self.alice, old), CURRENT)
        self.assertEqual(searched_document_ids(self.alice.id), [old.id])
        self.assertEqual(self.state(self.bob, old), SUPERSEDED)
        self.assertEqual(searched_document_ids(self.bob.id), [new.id])

    def test_a_translation_is_flagged_only_for_users_without_the_original(self):
        original = self.make(self.alice, language="de", original="de")
        translation = self.make(self.bob, language="en", original="de")
        self.give_access(self.alice, translation)
        self.assertEqual(self.state(self.alice, translation), TRANSLATION)
        self.assertEqual(self.state(self.bob, translation), TRANSLATION_ONLY)
        self.assertEqual(searched_document_ids(self.alice.id), [original.id])

    def test_the_chat_filter_uses_this_resolution(self):
        old = self.make(self.alice, edition=date(2018, 8, 1))
        new = self.make(self.alice, edition=date(2025, 12, 1))
        self.assertEqual(accessible_document_ids(self.alice.id), [new.id])
        self.assertNotIn(old.id, accessible_document_ids(self.alice.id))
        self.assertEqual(accessible_document_ids(self.bob.id), [])


class LibraryViewTests(LibraryMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")
        self.client.force_login(self.user)

    def test_the_list_explains_why_a_document_is_not_used(self):
        self.make(self.user, edition=date(2018, 8, 1))
        self.make(self.user, edition=date(2025, 12, 1))
        page = self.client.get("/specs/handling/").content.decode()
        self.assertIn("Obsoleta: sustituida por VW TL 245 (2025-12, de)", page)

    def test_the_list_flags_a_translation_without_original(self):
        self.make(self.user, language="en", original="de")
        page = self.client.get("/specs/handling/").content.decode()
        self.assertIn("Solo traducción: el original puede prevalecer", page)

    def test_a_normal_document_has_no_extra_label(self):
        self.make(self.user)
        page = self.client.get("/specs/handling/").content.decode()
        for text in ("Obsoleta", "Solo traducción", "Posible duplicado", "Traducción:"):
            self.assertNotIn(text, page)

    def _ask(self, documents, **post):
        nodes = []
        for document in documents:
            node = MagicMock()
            node.node.metadata = {"filename": document.filename, DOC_KEY: document.id}
            node.node.get_content.return_value = "text"
            node.score = 0.9
            nodes.append(node)
        engine = MagicMock()
        engine.query.return_value = MagicMock(source_nodes=nodes, __str__=lambda self: "answer")
        with patch("specs.views.get_rag_engine", return_value=engine):
            self.engine = engine
            return self.client.post("/specs/chat/query/", {"query": "salt spray?", **post}).json()

    def test_the_chat_warns_when_an_answer_rests_on_a_translation(self):
        translation = self.make(self.user, language="en", original="de")
        data = self._ask([translation])
        self.assertEqual(len(data["notes"]), 1)
        self.assertIn(translation.filename, data["notes"][0])

    def test_the_chat_does_not_warn_for_an_original(self):
        original = self.make(self.user)
        self.assertEqual(self._ask([original])["notes"], [])

    def test_each_source_links_to_the_users_copy_of_the_document(self):
        document = self.make(self.user)
        entry = UserDocument.objects.get(user=self.user, document=document)
        source = self._ask([document])["sources"][0]
        self.assertEqual(source["url"], f"/specs/handling/view/{entry.id}/")

    def test_an_attached_file_is_sent_to_the_model_with_the_question(self):
        document = self.make(self.user)
        attachment = SimpleUploadedFile("pliego.txt", b"salt spray 240 h")
        data = self._ask([document], attachment=attachment)
        prompt = self.engine.query.call_args[0][0].query_str
        self.assertIn("salt spray?", prompt)
        self.assertIn("salt spray 240 h", prompt)
        self.assertEqual(data["response"], "answer")

    def test_an_unsupported_attachment_is_rejected(self):
        response = self.client.post("/specs/chat/query/", {
            "query": "q", "attachment": SimpleUploadedFile("virus.exe", b"x")})
        self.assertEqual(response.status_code, 400)


class ReviewFormTests(LibraryMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="x")
        self.document = self.make(self.user, confirmed=False)
        Document.objects.filter(pk=self.document.pk).update(uploaded_by=self.user)
        self.entry = UserDocument.objects.get(user=self.user, document=self.document)
        self.client.force_login(self.user)
        self.data = {"spec_issuer": "VW", "spec_number": "TL 245", "title": "t", "edition_date": "2025-12-01",
                     "language": "en", "original_language": "de"}

    def post(self, **changes):
        return self.client.post(f"/specs/handling/review/{self.entry.id}/", {**self.data, **changes})

    def test_a_translation_is_saved_with_its_original_language(self):
        self.assertEqual(self.post().status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual((self.document.language, self.document.original_language), ("en", "de"))
        self.assertTrue(self.document.is_translation)

    def test_an_empty_original_language_defaults_to_the_documents_own(self):
        self.post(original_language="", language="de")
        self.document.refresh_from_db()
        self.assertEqual(self.document.original_language, "de")
        self.assertFalse(self.document.is_translation)

    def test_the_language_is_required(self):
        response = self.post(language="")
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)

    def test_an_invalid_language_code_is_rejected(self):
        for bad in ("deutsch", "d", "12"):
            self.assertEqual(self.post(language=bad).status_code, 200, bad)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)


class OriginalLanguageDetectionTests(TestCase):
    def parse(self, **fields):
        base = {"issuer": "VW", "number": "TL 245", "language": "en"}
        return parse_extraction(json.dumps({**base, **fields}))

    def test_the_language_stated_in_the_document_wins(self):
        self.assertEqual(self.parse(is_translation=True, original_language="fr")["original_language"], "fr")

    def test_a_translation_without_a_stated_original_uses_the_issuers_home_language(self):
        self.assertEqual(self.parse(is_translation=True)["original_language"], "de")
        self.assertEqual(self.parse(issuer="BYD", is_translation=True)["original_language"], "zh")
        self.assertEqual(self.parse(issuer="Toyota", is_translation=True)["original_language"], "ja")

    def test_a_translation_from_an_unknown_issuer_has_no_original(self):
        self.assertEqual(self.parse(issuer="Some GmbH", is_translation=True)["original_language"], "")

    def test_a_document_that_is_not_a_translation_is_its_own_original(self):
        self.assertEqual(self.parse(is_translation=False, language="de")["original_language"], "de")
        self.assertEqual(self.parse(language="de")["original_language"], "de")

    def test_the_model_answering_true_as_text_is_understood(self):
        self.assertEqual(self.parse(is_translation="true")["original_language"], "de")


class LanguageSelectorTests(LibraryMixin, TestCase):
    """The language fields are selectors showing full names; only the ISO code is stored."""

    def setUp(self):
        self.user = User.objects.create_user("owner", password="x")
        self.document = self.make(self.user, confirmed=False, language="de", original="de")
        Document.objects.filter(pk=self.document.pk).update(uploaded_by=self.user)
        self.entry = UserDocument.objects.get(user=self.user, document=self.document)
        self.client.force_login(self.user)
        self.url = f"/specs/handling/review/{self.entry.id}/"

    def page(self, accept_language=None):
        extra = {"HTTP_ACCEPT_LANGUAGE": accept_language} if accept_language else {}
        return self.client.get(self.url, **extra).content.decode()

    def test_the_language_fields_are_selectors_not_text_inputs(self):
        html = self.page()
        for name in ("language", "original_language"):
            self.assertIn(f'<select name="{name}"', html)
            self.assertNotIn(f'type="text" name="{name}"', html)

    def test_options_show_the_full_name_and_store_the_code(self):
        html = self.page()
        self.assertIn('<option value="de" selected>Alemán</option>', html)
        self.assertIn('<option value="en">Inglés</option>', html)
        self.assertIn('<option value="zh">Chino</option>', html)

    def test_the_names_follow_the_interface_language(self):
        html = self.page(accept_language="en")
        self.assertIn('<option value="de" selected>German</option>', html)
        self.assertIn('<option value="es">Spanish</option>', html)
        self.assertIn('<option value="zh">Chinese</option>', html)

    def test_a_language_detected_outside_the_list_stays_selectable(self):
        Document.objects.filter(pk=self.document.pk).update(language="xx", original_language="xx")
        self.assertIn('<option value="xx" selected>xx</option>', self.page())

    def test_the_form_rejects_a_code_that_is_not_an_option(self):
        data = {"spec_issuer": "VW", "spec_number": "TL 245", "title": "", "edition_date": "2025-12-01",
                "language": "zz", "original_language": ""}
        self.assertEqual(self.client.post(self.url, data).status_code, 200)
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_PENDING)

    def test_choosing_a_name_saves_its_code(self):
        data = {"spec_issuer": "VW", "spec_number": "TL 245", "title": "", "edition_date": "2025-12-01",
                "language": "en", "original_language": "de"}
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual((self.document.language, self.document.original_language), ("en", "de"))

    def test_common_languages_come_first_and_the_rest_are_alphabetical(self):
        from specs.languages import COMMON, language_choices
        codes = [code for code, _name in language_choices()]
        self.assertEqual(codes[:len(COMMON)], COMMON)
        rest = [name for code, name in language_choices() if code not in COMMON]
        self.assertEqual(rest, sorted(rest, key=str.lower))

    def test_every_language_has_a_translated_name(self):
        from django.utils import translation
        from specs.languages import LANGUAGE_NAMES
        with translation.override("en"):
            names = {code: str(name) for code, name in LANGUAGE_NAMES.items()}
        spanish_looking = [c for c, n in names.items() if n != "Hindi" and n == str(n) and any(ch in n for ch in "áéíóúñ")]
        self.assertEqual(spanish_looking, [], "these names are not translated into English")
