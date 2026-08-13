"""
core/redis_utils.py — Utilitaires Redis pour Kharandi
────────────────────────────────────────────────────────
Centralise toutes les interactions avec le cache Redis :
  - Quota Karamo (messages IA par jour)
  - OTP (code + verificationid avec TTL)
  - Cache abonnement utilisateur
  - Cache sujets BAC
  - Rate limiting API
"""
from datetime import date
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
KARAMO_FREE_DAILY_LIMIT = 5       # messages gratuits / jour
OTP_TTL                 = 300     # 5 minutes
SUBSCRIPTION_TTL        = 600     # 10 minutes
BAC_SUBJECTS_TTL        = 3600    # 1 heure
RATE_LIMIT_TTL          = 60      # 1 minute


# ══════════════════════════════════════════════════════════════════════════════
#  QUOTA KARAMO
# ══════════════════════════════════════════════════════════════════════════════

def karamo_check_quota(user, cost: int = 1) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut envoyer un message à Karamo.
    Retourne (autorisé: bool, message_erreur: str).
    """
    if _is_subscribed(user):
        return True, ""

    cost = max(int(cost), 1)

    key   = _karamo_key(user.id)
    count = cache.get(key, 0)

    if count + cost > KARAMO_FREE_DAILY_LIMIT:
        return False, (
            f"Vous avez atteint votre limite de {KARAMO_FREE_DAILY_LIMIT} messages "
            f"gratuits par jour. Abonnez-vous à Kharandi Premium pour un accès "
            f"illimité à Karamo !"
        )

    # Incrémenter — TTL jusqu'à minuit (secondes restantes dans la journée)
    cache.set(key, count + cost, timeout=_seconds_until_midnight())
    return True, ""


def karamo_refund_quota(user, cost: int = 1):
    """Rembourse une réservation lorsque le fournisseur IA échoue."""
    if _is_subscribed(user):
        return
    key = _karamo_key(user.id)
    count = cache.get(key, 0)
    cache.set(
        key,
        max(0, count - max(int(cost), 1)),
        timeout=_seconds_until_midnight(),
    )


def karamo_get_remaining(user) -> int:
    """Retourne le nombre de messages restants aujourd'hui (-1 = illimité)."""
    if _is_subscribed(user):
        return -1
    count = cache.get(_karamo_key(user.id), 0)
    return max(0, KARAMO_FREE_DAILY_LIMIT - count)


def karamo_reset_quota(user_id: str):
    """Réinitialise manuellement le quota d'un utilisateur (admin)."""
    cache.delete(_karamo_key(user_id))
    logger.info("Quota Karamo réinitialisé pour user=%s", user_id)


# ══════════════════════════════════════════════════════════════════════════════
#  OTP
# ══════════════════════════════════════════════════════════════════════════════

def otp_store(phone: str, verificationid: str, code: str = ""):
    """Stocke le verificationid Nimba SMS pour un numéro de téléphone."""
    cache.set(f"otp:{phone}", {"verificationid": verificationid, "code": code},
              timeout=OTP_TTL)
    logger.debug("OTP stocké pour %s | vid=%s", phone, verificationid)


def otp_get(phone: str) -> dict | None:
    """Récupère le verificationid pour un numéro. Retourne None si expiré."""
    return cache.get(f"otp:{phone}")


def otp_delete(phone: str):
    """Supprime l'OTP après vérification réussie."""
    cache.delete(f"otp:{phone}")


# ══════════════════════════════════════════════════════════════════════════════
#  CACHE ABONNEMENT
# ══════════════════════════════════════════════════════════════════════════════

def subscription_set_active(user_id: str, end_date=None):
    """
    Met en cache le statut premium d'un utilisateur.
    TTL = min(600s, temps_restant_abonnement).
    """
    ttl = SUBSCRIPTION_TTL
    if end_date:
        from django.utils import timezone
        remaining = int((end_date - timezone.now()).total_seconds())
        ttl = min(ttl, max(remaining, 60))
    cache.set(f"sub_active:{user_id}", True, timeout=ttl)


def subscription_clear(user_id: str):
    """Vide le cache abonnement (à appeler quand le statut change)."""
    cache.delete(f"sub_active:{user_id}")


def subscription_is_cached_active(user_id: str) -> bool | None:
    """
    Retourne True/False depuis le cache, None si absent (→ vérifier en DB).
    """
    return cache.get(f"sub_active:{user_id}")


# ══════════════════════════════════════════════════════════════════════════════
#  CACHE SUJETS BAC
# ══════════════════════════════════════════════════════════════════════════════

def bac_subjects_cache_set(subjects: list):
    """Met en cache la liste complète des sujets BAC."""
    cache.set("bac:subjects:all", subjects, timeout=BAC_SUBJECTS_TTL)
    logger.info("Cache sujets BAC : %d sujets mis en cache", len(subjects))


def bac_subjects_cache_get() -> list | None:
    """Retourne les sujets depuis le cache, None si absent."""
    return cache.get("bac:subjects:all")


def bac_subjects_cache_clear():
    """Vide le cache des sujets (après un load_bac_data)."""
    cache.delete("bac:subjects:all")
    logger.info("Cache sujets BAC vidé.")


# ══════════════════════════════════════════════════════════════════════════════
#  RATE LIMITING API
# ══════════════════════════════════════════════════════════════════════════════

def rate_limit_check(key: str, limit: int, window: int = RATE_LIMIT_TTL) -> bool:
    """
    Vérifie si la clé a dépassé la limite dans la fenêtre de temps.
    Retourne True si autorisé, False si bloqué.
    Usage : rate_limit_check(f"api:{request.META['REMOTE_ADDR']}", limit=60)
    """
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout=window)
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS PRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

def _karamo_key(user_id) -> str:
    return f"karamo_quota:{user_id}:{date.today().isoformat()}"


def _is_subscribed(user) -> bool:
    """Vérifie l'abonnement avec cache Redis d'abord, DB ensuite."""
    cached = subscription_is_cached_active(str(user.id))
    if cached is not None:
        return cached

    # Pas en cache → vérifier en DB
    try:
        sub = user.subscription
        active = sub.is_active()
        if active:
            subscription_set_active(str(user.id), sub.end_date)
        return active
    except Exception:
        return False


def _seconds_until_midnight() -> int:
    """Secondes restantes jusqu'à minuit (pour TTL du quota journalier)."""
    import datetime
    now      = datetime.datetime.now()
    midnight = datetime.datetime.combine(now.date() + datetime.timedelta(days=1),
                                         datetime.time.min)
    return max(int((midnight - now).total_seconds()), 60)
