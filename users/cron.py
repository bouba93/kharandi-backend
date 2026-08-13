import logging
from django.utils import timezone
logger = logging.getLogger(__name__)
def cleanup_expired_otps():
    from .models import OTPRecord
    deleted, _ = OTPRecord.objects.filter(expires_at__lt=timezone.now(), verified=False).delete()
    logger.info("[CRON] %d OTP(s) expirés supprimés.", deleted)
