"""
Public demo: anyone can try the specs chat without creating an account.

A visitor gets a throwaway user (DemoSession) with access to the shared demo library, which is
owned by a regular user (DEMO_OWNER_USERNAME) and loaded once with `load_demo_documents`. The
documents are indexed once; each demo user only receives a UserDocument pointing at them, so the
usual per-user isolation of the RAG applies unchanged. Demo users cannot upload files and have a
limited number of questions; `purge_demo_users` deletes the expired ones.
"""
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import DemoSession, Document, UserDocument

DEMO_OWNER_USERNAME = 'demo_library'
MAX_QUERIES = 15              # questions per demo user
LIFETIME_HOURS = 24           # a demo user is deleted after this long
MAX_STARTS_PER_HOUR = 10      # demo users that one IP may create per hour


def client_ip(request):
    """The client address: nginx appends it as the last X-Forwarded-For entry."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


def is_demo(user):
    return user.is_authenticated and DemoSession.objects.filter(user=user).exists()


def get_demo_owner():
    """The user that owns the shared demo documents; it cannot log in."""
    owner, created = User.objects.get_or_create(username=DEMO_OWNER_USERNAME)
    if created:
        owner.set_unusable_password()
        owner.save(update_fields=['password'])
    return owner


def demo_documents():
    """Indexed documents of the shared demo library."""
    return Document.objects.filter(accesses__user__username=DEMO_OWNER_USERNAME, is_indexed=True).distinct()


def allow_start(ip):
    """Counts one demo start for this IP; False once it exceeds MAX_STARTS_PER_HOUR."""
    key = f'demo-starts:{ip}'
    cache.add(key, 0, timeout=3600)
    try:
        return cache.incr(key) <= MAX_STARTS_PER_HOUR
    except ValueError:   # the key expired between add and incr
        cache.set(key, 1, timeout=3600)
        return True


def create_demo_user():
    """Creates a demo user with access to every demo document."""
    with transaction.atomic():
        user = User.objects.create(username=f'demo_{secrets.token_hex(6)}')
        user.set_unusable_password()
        user.save(update_fields=['password'])
        DemoSession.objects.create(user=user)
        owner_entries = {e.document_id: e for e in
                         UserDocument.objects.filter(user__username=DEMO_OWNER_USERNAME, document__is_indexed=True)}
        UserDocument.objects.bulk_create([
            UserDocument(user=user, document_id=document_id, filename=entry.filename,
                         company=entry.company, mongo_id=entry.mongo_id, is_indexed=True)
            for document_id, entry in owner_entries.items()
        ])
    return user


def consume_query(user):
    """Counts a question of a demo user; False when the demo user has used all of them."""
    return DemoSession.objects.filter(user=user, queries_used__lt=MAX_QUERIES).update(
        queries_used=F('queries_used') + 1) == 1


def queries_left(user):
    session = DemoSession.objects.filter(user=user).first()
    return max(0, MAX_QUERIES - session.queries_used) if session else None


def expired_demo_users():
    return User.objects.filter(demo_session__created_at__lt=timezone.now() - timedelta(hours=LIFETIME_HOURS))
