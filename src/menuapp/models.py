from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        # El código expira en 15 minutos
        return timezone.now() > self.created_at + timedelta(minutes=15)

    @staticmethod
    def generate_code():
        return ''.join(random.choices(string.digits, k=6))
