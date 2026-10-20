from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Document(models.Model):
    """
    One physical file (one edition of a specification), stored once.
    The PDF lives in MongoDB (GridFS); its vectors live once in Qdrant, tagged with this id.
    Several users can have access to the same Document through UserDocument.
    """
    CURRENT = 'current'
    OBSOLETE = 'obsolete'
    STATUS_CHOICES = [(CURRENT, 'Current'), (OBSOLETE, 'Obsolete')]

    # An indexing run that started more than this long ago is considered dead and may be retried
    INDEXING_TIMEOUT_MINUTES = 30

    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 of the PDF content")
    mongo_id = models.CharField(max_length=100, help_text="File ID in MongoDB GridFS")
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=CURRENT)
    is_indexed = models.BooleanField(default=False, help_text="The RAG has processed this file")
    indexing_started_at = models.DateTimeField(null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    # Who uploaded it first: the only user who can review and correct its metadata
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_documents')

    # Metadata of the standard: extracted by the LLM at indexing time, then confirmed by the uploader
    METADATA_NONE = 'none'
    METADATA_PENDING = 'pending_review'
    METADATA_CONFIRMED = 'confirmed'
    METADATA_FAILED = 'failed'
    METADATA_STATUS_CHOICES = [
        (METADATA_NONE, 'Not extracted'), (METADATA_PENDING, 'Pending review'),
        (METADATA_CONFIRMED, 'Confirmed'), (METADATA_FAILED, 'Extraction failed'),
    ]
    metadata_status = models.CharField(max_length=15, choices=METADATA_STATUS_CHOICES, default=METADATA_NONE)
    spec_issuer = models.CharField(max_length=100, blank=True)   # normalised short name: VW, BMW, ISO...
    spec_number = models.CharField(max_length=100, blank=True)   # normalised identifier without edition
    title = models.CharField(max_length=300, blank=True)
    edition_date = models.DateField(null=True, blank=True)       # first day of the edition month
    language = models.CharField(max_length=5, blank=True)
    original_language = models.CharField(max_length=5, blank=True)  # language that prevails; empty = same as language
    supersedes = models.JSONField(default=list, blank=True)      # editions this document replaces
    copyright_notice = models.CharField(max_length=300, blank=True)

    class Meta:
        indexes = [models.Index(fields=['spec_issuer', 'spec_number'], name='doc_spec_issuer_number_idx')]

    def __str__(self):
        return f"{self.filename} [{self.status}]"

    @property
    def is_translation(self):
        """True when the document is not written in the language that prevails for the standard."""
        return bool(self.language and self.original_language and self.language != self.original_language)

    def can_be_edited_by(self, user):
        """Only the uploader reviews the metadata; if that account is gone, the first user with access takes over."""
        owner_id = self.uploaded_by_id or self.accesses.order_by('id').values_list('user_id', flat=True).first()
        return owner_id is not None and owner_id == user.id

    @classmethod
    def claim_indexing(cls, pk):
        """
        Atomically marks the document as being indexed. Returns False if it is already
        indexed or another run is in progress, so two uploads of the same new file
        cannot create duplicate vectors.
        """
        stale = timezone.now() - timedelta(minutes=cls.INDEXING_TIMEOUT_MINUTES)
        free = models.Q(indexing_started_at__isnull=True) | models.Q(indexing_started_at__lt=stale)
        return cls.objects.filter(free, pk=pk, is_indexed=False).update(indexing_started_at=timezone.now()) == 1


class UserDocument(models.Model):
    """
    A user's access entry to a Document (the user's library).
    Deleting it removes the user's access; the Document itself is deleted only
    when no other user has access to it.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document = models.ForeignKey(Document, null=True, on_delete=models.CASCADE, related_name='accesses')
    filename = models.CharField(max_length=255)
    company = models.CharField(max_length=100, blank=True, null=True, help_text="Associated OEM (VW, BMW, etc.)")
    upload_date = models.DateTimeField(auto_now_add=True)

    # LEGACY: replaced by document.mongo_id / document.is_indexed; removed after the backfill is verified
    mongo_id = models.CharField(max_length=100, help_text="LEGACY: use document.mongo_id")
    is_indexed = models.BooleanField(default=False, help_text="LEGACY: use document.is_indexed")

    def __str__(self):
        return f"{self.filename} ({self.user.username})"

    class Meta:
        verbose_name = "User Document"
        verbose_name_plural = "User Documents"
        constraints = [
            models.UniqueConstraint(fields=['user', 'document'], name='unique_user_document'),
        ]


class DemoSession(models.Model):
    """
    Marks a throwaway user created by the public demo ("Try the demo" button).
    The user only has access to the shared demo documents and is deleted after a day.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='demo_session')
    created_at = models.DateTimeField(auto_now_add=True)
    queries_used = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} ({self.queries_used} queries)"
