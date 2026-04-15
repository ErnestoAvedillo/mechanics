from django.db import models
from django.contrib.auth.models import User

class UserDocument(models.Model):
    """
    Representa un documento subido por un usuario.
    La referencia real del binario está en MongoDB.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    mongo_id = models.CharField(max_length=100, help_text="ID del archivo en GridFS de MongoDB")
    filename = models.CharField(max_length=255)
    company = models.CharField(max_length=100, blank=True, null=True, help_text="OEM asociado (VW, BMW, etc.)")
    upload_date = models.DateTimeField(auto_now_add=True)
    is_indexed = models.BooleanField(default=False, help_text="Indica si el documento ya ha sido procesado por el RAG")

    def __str__(self):
        return f"{self.filename} ({self.user.username})"

    class Meta:
        verbose_name = "Documento de Usuario"
        verbose_name_plural = "Documentos de Usuarios"
