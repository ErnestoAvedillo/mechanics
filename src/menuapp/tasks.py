from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()

@shared_task
def remove_pending_registration():
    """
    Celery task to delete pending registrations of users who did not complete
    verification and whose email code has already expired.
    """
    expiration_threshold = timezone.now() - timedelta(minutes=15)
    User.objects.filter(
        is_active=False,
        emailverification__created_at__lt=expiration_threshold,
    ).delete()
    logger.info("Pending registrations have been deleted.")
    return "Pending registrations have been deleted."
