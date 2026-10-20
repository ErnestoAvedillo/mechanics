"""
Tests for the public demo: a visitor gets a throwaway user with access to the shared demo
documents only, cannot upload, has a limited number of questions, and expired users are purged.

Run: docker exec -w /app/src django python manage.py test specs.test_demo
"""
import hashlib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from specs import demo
from specs.models import DemoSession, Document, UserDocument


class DemoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = demo.get_demo_owner()
        self.document = Document.objects.create(
            file_hash=hashlib.sha256(b"semver").hexdigest(), mongo_id=str(ObjectId()),
            filename="semver.pdf", is_indexed=True, uploaded_by=self.owner)
        UserDocument.objects.create(user=self.owner, document=self.document, filename="semver.pdf",
                                    mongo_id=self.document.mongo_id, is_indexed=True)

    def start(self):
        return self.client.post(reverse('specs:demo_start'))

    def test_start_creates_a_demo_user_with_the_demo_documents(self):
        response = self.start()
        self.assertRedirects(response, reverse('specs:handling'), fetch_redirect_response=False)
        user = DemoSession.objects.get().user
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(list(UserDocument.objects.filter(user=user).values_list('document_id', flat=True)),
                         [self.document.id])

    def test_demo_users_are_isolated_from_each_other(self):
        self.start()
        first = DemoSession.objects.get().user
        stranger = User.objects.create_user("stranger", password="x")
        UserDocument.objects.create(user=stranger, document=Document.objects.create(
            file_hash="b" * 64, mongo_id=str(ObjectId()), filename="private.pdf"), filename="private.pdf", mongo_id="x")
        self.assertEqual(UserDocument.objects.filter(user=first).count(), 1)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse('specs:demo_start')).status_code, 405)

    def test_start_without_demo_documents_does_not_create_a_user(self):
        UserDocument.objects.all().delete()
        self.start()
        self.assertFalse(DemoSession.objects.exists())

    def test_start_is_limited_per_ip(self):
        for _ in range(demo.MAX_STARTS_PER_HOUR + 3):
            self.client.logout()
            self.start()
        self.assertEqual(DemoSession.objects.count(), demo.MAX_STARTS_PER_HOUR)

    def test_demo_user_cannot_upload(self):
        self.start()
        response = self.client.post(reverse('specs:upload_document'))
        self.assertRedirects(response, reverse('specs:handling'), fetch_redirect_response=False)
        self.assertFalse(Document.objects.exclude(pk=self.document.pk).exists())

    def test_demo_user_cannot_delete_or_update(self):
        self.start()
        entry = UserDocument.objects.get(user=DemoSession.objects.get().user)
        self.client.post(reverse('specs:document_delete', args=[entry.id]))
        self.client.post(reverse('specs:document_update', args=[entry.id]), {'filename': 'x.pdf', 'company': 'X'})
        entry.refresh_from_db()
        self.assertEqual(entry.filename, 'semver.pdf')

    def test_demo_can_confirm_unconfirmed_metadata(self):
        self.start()
        entry = UserDocument.objects.get(user=DemoSession.objects.get().user)
        url = reverse('specs:document_review', args=[entry.id])
        self.assertContains(self.client.get(url), 'Confirmar metadatos')
        self.client.post(url, {'spec_issuer': 'SemVer', 'spec_number': '2.0.0', 'title': 't', 'language': 'en'})
        self.document.refresh_from_db()
        self.assertEqual(self.document.metadata_status, Document.METADATA_CONFIRMED)
        self.assertEqual(self.document.spec_number, '2.0.0')

    def test_demo_cannot_change_confirmed_metadata(self):
        Document.objects.filter(pk=self.document.pk).update(metadata_status=Document.METADATA_CONFIRMED)
        self.start()
        entry = UserDocument.objects.get(user=DemoSession.objects.get().user)
        url = reverse('specs:document_review', args=[entry.id])
        self.assertNotContains(self.client.get(url), 'Confirmar metadatos')
        self.client.post(url, {'spec_issuer': 'XYZ', 'spec_number': '1', 'title': 't', 'language': 'en'})
        self.document.refresh_from_db()
        self.assertNotEqual(self.document.spec_issuer, 'XYZ')

    def test_questions_are_limited(self):
        self.start()
        engine = MagicMock()
        engine.query.return_value = MagicMock(source_nodes=[], __str__=lambda self: "answer")
        with patch("specs.views.get_rag_engine", return_value=engine):
            for _ in range(demo.MAX_QUERIES):
                self.assertEqual(self.client.post(reverse('specs:chat_query'), {'query': 'q'}).status_code, 200)
            self.assertEqual(self.client.post(reverse('specs:chat_query'), {'query': 'q'}).status_code, 429)
        self.assertEqual(engine.query.call_count, demo.MAX_QUERIES)

    def test_regular_users_have_no_limit(self):
        User.objects.create_user("alice", password="x")
        self.client.login(username="alice", password="x")
        engine = MagicMock()
        engine.query.return_value = MagicMock(source_nodes=[], __str__=lambda self: "answer")
        with patch("specs.views.get_rag_engine", return_value=engine):
            for _ in range(demo.MAX_QUERIES + 2):
                self.assertEqual(self.client.post(reverse('specs:chat_query'), {'query': 'q'}).status_code, 200)

    def test_purge_deletes_only_expired_demo_users(self):
        old, recent = demo.create_demo_user(), demo.create_demo_user()
        DemoSession.objects.filter(user=old).update(created_at=timezone.now() - timedelta(hours=demo.LIFETIME_HOURS + 1))
        call_command('purge_demo_users')
        self.assertFalse(User.objects.filter(pk=old.pk).exists())
        self.assertTrue(User.objects.filter(pk=recent.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(Document.objects.filter(pk=self.document.pk).exists())
