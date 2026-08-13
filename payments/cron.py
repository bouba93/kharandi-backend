"""
payments/cron.py — Tâches périodiques de paiement
─────────────────────────────────────────────────
Filet de sécurité indispensable : un callback LengoPay peut se perdre (réseau
coupé, backend redémarré, notification envoyée avant l'enregistrement du
`gateway_ref`). Sans ces tâches, un client ayant réellement payé n'obtiendrait
jamais son abonnement.

  check_expired_subscriptions   → passe les abonnements échus en EXPIRED
  replay_orphan_callbacks       → rejoue les callbacks reçus « trop tôt »
  reconcile_pending_payments    → interroge LengoPay pour les transactions
                                  restées en attente
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def check_expired_subscriptions():
    from .models import Subscription
    n = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        end_date__lt=timezone.now(),
    ).update(status=Subscription.Status.EXPIRED)
    logger.info("[CRON] %d abonnement(s) expirés.", n)


def _apply_state(tx_pk, state, payload=None):
    """
    Applique un statut définitif à une transaction, de façon idempotente et
    sous verrou. Retourne le statut appliqué, ou None si rien n'a changé.
    """
    from django.db import transaction as db_transaction
    from .models import Transaction
    from .views import PaymentWebhookView, notify_payment_result
    from .lengopay import extract_phone

    view = PaymentWebhookView()

    with db_transaction.atomic():
        tx = Transaction.objects.select_for_update().select_related(
            "user", "subscription__plan", "order"
        ).get(pk=tx_pk)

        if tx.status != Transaction.Status.PENDING:
            return None

        champs = ["status"]
        if payload:
            tx.webhook_payload = payload
            champs.append("webhook_payload")
            telephone = extract_phone(payload)
            if telephone and not tx.phone:
                tx.phone = telephone
                champs.append("phone")

        if state == "SUCCESS":
            tx.status = Transaction.Status.SUCCESS
            tx.save(update_fields=champs)
            view._activate(tx)
            view._confirm_order(tx)
        else:
            tx.status = Transaction.Status.FAILED
            tx.save(update_fields=champs)

    notify_payment_result(tx, state)
    return state


def replay_orphan_callbacks(pay_id: str = None, max_age_hours: int = 72):
    """
    Rejoue les callbacks arrivés avant l'enregistrement du `gateway_ref`.

    Le statut annoncé n'est jamais cru sur parole : on le confirme auprès de
    LengoPay quand l'API répond, sinon on retient le statut annoncé uniquement
    si le callback était authentifié (jeton d'URL ou HMAC) et si le montant
    correspond à celui de la transaction.
    """
    from decimal import Decimal

    from django.conf import settings

    from .models import PaymentCallback, Transaction
    from .lengopay import normalize_status, to_decimal, transaction_status

    now = timezone.now()
    # ORPHAN    : callback arrivé avant l'enregistrement du gateway_ref.
    # UNVERIFIED: callback non appliqué faute de confirmation LengoPay au
    #             moment de sa réception (mode strict + API momentanément
    #             indisponible). Le rejeu retentera la confirmation.
    qs = PaymentCallback.objects.filter(
        outcome__in=[
            PaymentCallback.Outcome.ORPHAN,
            PaymentCallback.Outcome.UNVERIFIED,
        ],
        replayed=False,
        created_at__gt=now - timedelta(hours=max_age_hours),
    ).exclude(pay_id="")
    if pay_id:
        qs = qs.filter(pay_id=pay_id)

    rejoues = appliques = 0
    tolerance = to_decimal(settings.LENGOPAY_AMOUNT_TOLERANCE) or Decimal("0")

    for cb in qs.order_by("created_at"):
        tx = Transaction.objects.filter(gateway_ref=cb.pay_id).first()
        if not tx:
            continue  # toujours orphelin, on retentera au prochain passage

        rejoues += 1
        payload = cb.payload if isinstance(cb.payload, dict) else {}
        annonce = normalize_status(payload.get("status")) or normalize_status(cb.applied_status)

        etat, montant = transaction_status(cb.pay_id)
        if etat is None:
            if not cb.auth_method:
                logger.warning(
                    "Callback orphelin %s : non authentifié et API muette, "
                    "conservé pour un prochain passage.", cb.pay_id,
                )
                continue
            etat = annonce
            montant = to_decimal(payload.get("amount"))

        if etat not in {"SUCCESS", "FAILED"}:
            continue

        if etat == "SUCCESS" and montant is not None:
            if abs(Decimal(tx.amount) - montant) > tolerance:
                logger.error(
                    "Callback orphelin %s REFUSÉ : montant %s ≠ attendu %s.",
                    cb.pay_id, montant, tx.amount,
                )
                PaymentCallback.objects.filter(pk=cb.pk).update(
                    outcome=PaymentCallback.Outcome.MISMATCH,
                    transaction=tx,
                    replayed=True,
                    detail=f"Rejeu refusé : montant {montant} ≠ attendu {tx.amount}.",
                )
                continue

        applique = _apply_state(tx.pk, etat, payload=payload or None)
        PaymentCallback.objects.filter(pk=cb.pk).update(
            transaction=tx,
            replayed=True,
            applied_status=etat,
            outcome=(
                PaymentCallback.Outcome.APPLIED if applique
                else PaymentCallback.Outcome.DUPLICATE
            ),
            detail=(
                "Rejeu après rattachement du gateway_ref." if applique
                else "Rejeu : transaction déjà traitée entre-temps."
            ),
        )
        if applique:
            appliques += 1
            logger.info("Callback orphelin %s rejoué : %s.", cb.pay_id, etat)

    if rejoues:
        logger.info(
            "[CRON] Callbacks orphelins : %d rejoué(s), %d appliqué(s).",
            rejoues, appliques,
        )
    return {"replayed": rejoues, "applied": appliques}


def reconcile_pending_payments(max_age_hours: int = 48):
    """
    Rattrape les transactions restées « en attente ».

    On interroge LengoPay (POST /transaction/status) pour chaque transaction en
    attente de plus de deux minutes et de moins de `max_age_hours`, puis on
    applique le statut réel.
    """
    from decimal import Decimal

    from django.conf import settings

    from .lengopay import to_decimal
    from .models import Transaction

    # Les callbacks arrivés trop tôt sont traités d'abord : c'est le cas le
    # moins coûteux et le plus fréquent.
    orphelins = replay_orphan_callbacks()

    now = timezone.now()
    pendings = Transaction.objects.filter(
        status=Transaction.Status.PENDING,
        created_at__lt=now - timedelta(minutes=2),
        created_at__gt=now - timedelta(hours=max_age_hours),
    ).exclude(gateway_ref="").only("pk", "gateway_ref")

    checked = confirmed = failed = 0

    refused = 0
    tolerance = to_decimal(settings.LENGOPAY_AMOUNT_TOLERANCE) or Decimal("0")

    for tx in pendings:
        checked += 1
        state, amount = _lengopay_state(tx.gateway_ref)
        if state not in {"SUCCESS", "FAILED"}:
            continue

        # Contrôle du montant, même sur un statut venu de l'API : défense en
        # profondeur contre une transaction rapprochée du mauvais pay_id.
        if state == "SUCCESS" and amount is not None:
            if abs(Decimal(tx.amount) - amount) > tolerance:
                refused += 1
                logger.error(
                    "Réconciliation %s REFUSÉE : montant LengoPay %s ≠ "
                    "montant attendu %s (tolérance %s).",
                    tx.gateway_ref, amount, tx.amount, tolerance,
                )
                continue

        if _apply_state(tx.pk, state) is None:
            continue
        if state == "SUCCESS":
            confirmed += 1
        else:
            failed += 1

    logger.info(
        "[CRON] Réconciliation : %d vérifiée(s), %d confirmée(s), "
        "%d échouée(s), %d refusée(s) pour montant incohérent.",
        checked, confirmed, failed, refused,
    )
    return {
        "checked": checked,
        "confirmed": confirmed,
        "failed": failed,
        "refused": refused,
        "orphans_replayed": orphelins["replayed"],
        "orphans_applied": orphelins["applied"],
    }


def _lengopay_state(pay_id):
    from .lengopay import transaction_status
    return transaction_status(pay_id)
