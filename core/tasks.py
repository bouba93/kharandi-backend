"""
core/tasks.py - Taches Celery automatiques Kharandi
"""
import logging
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

CACHE_DOCS_LEVEL = 'kharandi:docs:level:{level}'
CACHE_STATS      = 'kharandi:stats:global'
TTL_DOCS         = 3600 * 2
TTL_STATS        = 3600


@shared_task(name='core.warmup_subjects_cache', bind=True, max_retries=2)
def warmup_subjects_cache(self):
    try:
        from learning.models import Subject, Document
        subjects = list(Subject.objects.values('id', 'name', 'icon'))
        cache.set('kharandi:subjects:all', subjects, 3600 * 6)
        for level in ['Terminale', '3eme', '6eme']:
            docs = list(Document.objects.filter(level=level, content__gt='')
                        .values('id', 'title', 'subject_id', 'level', 'is_free')
                        .order_by('-created_at')[:500])
            cache.set(CACHE_DOCS_LEVEL.format(level=level), docs, TTL_DOCS)
        stats = {
            'total_documents': Document.objects.filter(content__gt='').count(),
            'bac_count':       Document.objects.filter(level='Terminale').count(),
            'bepc_count':      Document.objects.filter(level='3eme').count(),
            'entree7_count':   Document.objects.filter(level='6eme').count(),
            'updated_at':      timezone.now().isoformat(),
        }
        cache.set(CACHE_STATS, stats, TTL_STATS)
        logger.info("Cache warmup OK - %d documents", stats['total_documents'])
        return f"OK - {stats['total_documents']} documents"
    except Exception as exc:
        logger.error("Cache warmup error: %s", exc)
        raise self.retry(exc=exc, countdown=300)


@shared_task(name='core.auto_scrape', bind=True, max_retries=1)
def auto_scrape(self):
    try:
        from django.core.management import call_command
        import io
        out = io.StringIO()
        call_command('scrape_bac_subjects', '--type', 'all', '--delay', '2.0', stdout=out)
        warmup_subjects_cache.delay()
        return "Scraping OK"
    except Exception as exc:
        logger.error("Auto-scrape error: %s", exc)
        raise self.retry(exc=exc, countdown=3600)


@shared_task(name='core.auto_clean_content', bind=True, max_retries=1)
def auto_clean_content(self):
    try:
        from django.core.management import call_command
        import io
        call_command('clean_bac_content', stdout=io.StringIO())
        warmup_subjects_cache.delay()
        return "Nettoyage OK"
    except Exception as exc:
        logger.error("Auto-clean error: %s", exc)
        raise self.retry(exc=exc, countdown=3600)


@shared_task(name='core.check_expired_subscriptions')
def check_expired_subscriptions():
    try:
        from payments.models import Subscription
        expired = Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            end_date__lt=timezone.now(),
        )
        count = expired.count()
        if count:
            for sub in expired:
                cache.delete(f"sub:user:{sub.user_id}")
            expired.update(status=Subscription.Status.EXPIRED)
        return f"{count} abonnements expires"
    except Exception as exc:
        return f"Erreur: {exc}"


@shared_task(name='core.cleanup_expired_otps')
def cleanup_expired_otps():
    try:
        from users.models import OTPRecord
        deleted, _ = OTPRecord.objects.filter(expires_at__lt=timezone.now()).delete()
        return f"{deleted} OTP supprimes"
    except Exception as exc:
        return f"Erreur: {exc}"
