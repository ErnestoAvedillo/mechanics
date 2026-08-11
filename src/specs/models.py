from django.db import models
from django.contrib.auth.models import User

class UserDocument(models.Model):
    """
    Represents a document uploaded by a user.
    The actual binary reference lives in MongoDB.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    mongo_id = models.CharField(max_length=100, help_text="File ID in MongoDB GridFS")
    filename = models.CharField(max_length=255)
    company = models.CharField(max_length=100, blank=True, null=True, help_text="Associated OEM (VW, BMW, etc.)")
    upload_date = models.DateTimeField(auto_now_add=True)
    is_indexed = models.BooleanField(default=False, help_text="Indicates whether the document has already been processed by the RAG")

    def __str__(self):
        return f"{self.filename} ({self.user.username})"

    class Meta:
        verbose_name = "User Document"
        verbose_name_plural = "User Documents"
