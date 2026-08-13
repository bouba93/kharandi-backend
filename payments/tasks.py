"""
payments/tasks.py — Tâches Celery de paiement (exécutées par Celery Beat)
─────────────────────────────────────────────────────────────────────────
Un callback LengoPay peut se perdre : réseau coupé, backend en redémarrage,
notification émise avant l'enregistrement du `gateway_ref`, ou API de statut
momentanément indisponible en mode confirmation obligatoire.

Sans ces tâches, un client ayant réellement payé n'obtiendrait jamais son
abonnement. C'est le filet de sécurité du système de paiement :

    Paiement PENDING
          ↓
    Callback absent / perdu / non confirmé
          ↓
    Celery Beat (toutes les 3 minutes)
          ↓
    POST /api/v1/transaction/status auprès de LengoPay
          ↓
    SUCCESS → abonnement activé, commande confirmée
    FAILED  → transaction marquée en échec, rien n'est crédité

VERROU : chaque tâche est protégée par un verrou Redis. Deux exécutions
simultanées (Beat qui redémarre, worker qui a pris du retard, appel manuel via
`lengopay_doctor --reconcile`) ne peuvent pas traiter la même transaction deux
fois. Combiné au `select_for_update()` de `_apply_state`, cela garantit
l'idempotence même en cas de concurrence.
"""
import logging
from contextlib import contextmanager

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)


@contextmanager
def verrou(nom: str, expire: int = 600):
    """
    Verrou distribué best-effort via le cache Redis.

    `cache.add` est atomique : il ne réussit que si la clé n'existe pas encore.
    Si Redis est indisponible, on laisse volontairement passer la tâche —
    mieux vaut un risque de doublon (neutralisé par `select_for_update`) qu'une
    réconciliation qui ne tourne plus du tout.
    """
    cle = f"lock:{nom}"
    try:
        obtenu = cache.add(cle, "1", timeout=expire)
    except Exception:
        logger.warning("Verrou %s indisponible (cache muet) : exécution quand même.", nom)
        obtenu = True
        cle = None

    if not obtenu:
        logger.info("Tâche %s déjà en cours d'exécution : passage ignoré.", nom)
        yield False
        return

    try:
        yield True
    finally:
        if cle:
            try:
                cache.delete(cle)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  RÉCONCILIATION LENGOPAY — la tâche la plus importante
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name="payments.reconcile_lengopay", ignore_result=False)
def reconcile_lengopay(max_age_hours: int = 48):
    """
    Interroge LengoPay pour toutes les transactions restées en attente et
    applique leur statut réel. Rejoue au passage les callbacks orphelins ou
    non confirmés.

    Planifiée toutes les 3 minutes par Celery Beat.
    """
    from .cron import reconcile_pending_payments

    with verrou("reconcile_lengopay", expire=600) as acquis:
        if not acquis:
            return {"skipped": True}
        resultat = reconcile_pending_payments(max_age_hours=max_age_hours)

    if resultat.get("confirmed") or resultat.get("failed") or resultat.get("orphans_applied"):
        logger.warning(
            "Réconciliation LengoPay : %d paiement(s) rattrapé(s) qui auraient "
            "été perdus sans elle. Détail : %s",
            resultat.get("confirmed", 0) + resultat.get("orphans_applied", 0),
            resultat,
        )
    if resultat.get("refused"):
        logger.error(
            "Réconciliation : %d transaction(s) refusée(s) pour montant "
            "incohérent — à examiner manuellement.", resultat["refused"],
        )
    return resultat


@shared_task(name="payments.replay_orphan_callbacks", ignore_result=False)
def replay_orphan_callbacks_task(max_age_hours: int = 72):
    """
    Rejeu ciblé des callbacks reçus alors que la transaction n'était pas encore
    rattachable (course d'exécution Mobile Money). Passage rapide, planifié
    toutes les minutes : c'est le cas le plus fréquent et le moins coûteux.
    """
    from .cron import replay_orphan_callbacks

    with verrou("replay_orphan_callbacks", expire=120) as acquis:
        if not acquis:
            return {"skipped": True}
        return replay_orphan_callbacks(max_age_hours=max_age_hours)


# ══════════════════════════════════════════════════════════════════════════════
#  ABONNEMENTS
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name="payments.expire_subscriptions", ignore_result=False)
def expire_subscriptions():
    """Passe en EXPIRED les abonnements dont la date de fin est dépassée."""
    from .cron import check_expired_subscriptions

    with verrou("expire_subscriptions", expire=300) as acquis:
        if not acquis:
            return {"skipped": True}
        check_expired_subscriptions()
        return {"done": True}


@shared_task(name="payments.warn_expiring_subscriptions", ignore_result=False)
def warn_expiring_subscriptions():
    """Prévient par SMS les utilisateurs dont l'abonnement expire bientôt."""
    from .views import _warn_expiring_subscriptions

    with verrou("warn_expiring_subscriptions", expire=3600) as acquis:
        if not acquis:
            return {"skipped": True}
        try:
            return {"warned": _warn_expiring_subscriptions()}
        except Exception:
            logger.exception("Alerte d'expiration d'abonnement : échec.")
            return {"error": True}


# ══════════════════════════════════════════════════════════════════════════════
#  SUPERVISION DE CELERY BEAT
# ══════════════════════════════════════════════════════════════════════════════

BATTEMENT_CLE = "kharandi:beat:heartbeat"
BATTEMENT_TTL = 900  # 15 minutes


@shared_task(name="payments.beat_heartbeat", ignore_result=True)
def beat_heartbeat():
    """
    Battement de cœur du planificateur.

    Beat émet cette tâche chaque minute, le worker l'exécute et horodate une
    clé Redis. Cette clé prouve que la chaîne complète Beat → Redis → Worker
    fonctionne : c'est ce que vérifie `manage.py lengopay_doctor` et ce qui
    permet de détecter un Beat mort silencieusement — panne bien plus
    dangereuse qu'un crash, puisque plus aucune réconciliation ne tournerait.
    """
    from django.utils import timezone

    horodatage = timezone.now().isoformat()
    try:
        cache.set(BATTEMENT_CLE, horodatage, timeout=BATTEMENT_TTL)
    except Exception:
        logger.warning("Battement Beat non enregistré : cache indisponible.")
    return horodatage
