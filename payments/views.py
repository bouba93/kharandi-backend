"""
payments/views.py — LengoPay + Gestion Plans
─────────────────────────────────────────────
Plans    → GET  /payments/plans/           → liste plans actifs
           POST /payments/plans/           → créer un plan (admin)
           PATCH/DELETE /payments/plans/<id>/ → modifier/supprimer (admin)

Abonnements → POST /payments/subscriptions/initiate/
              Accepte : UUID, "seller", "mensuel", "annuel", "gratuit" comme plan_id
"""
import hashlib
import hmac
import logging
import uuid
import traceback
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import WebhookPermission, IsAdmin
from core.utils import success_response, error_response
from .models import Plan, PaymentCallback, Subscription, Transaction
from .serializers import PlanSerializer, PaymentInitiateSerializer, TransactionSerializer
from .lengopay import (
    create_payment as _lengopay_create,
    extract_phone,
    normalize_status,
    to_decimal,
    transaction_status,
)

logger = logging.getLogger(__name__)


def _lengopay_status(pay_id: str):
    """
    Alias historique conserve pour la compatibilite (payments/cron.py).

    Delegue au client officiel : POST {LENGOPAY_STATUS_URL} avec
    {"pay_id", "websiteid"}. Retourne (statut, montant) ou (None, None).
    """
    return transaction_status(pay_id)


def notify_payment_result(tx, state: str):
    """
    Effets secondaires d'un paiement : SMS + notification temps réel.

    Volontairement TOLÉRANT AUX PANNES : le paiement est déjà enregistré en
    base. Si Redis, Celery ou la passerelle SMS sont indisponibles, il ne faut
    surtout pas remonter d'erreur à LengoPay, qui rejouerait le callback en
    boucle alors que l'argent est encaissé.
    """
    if state == "SUCCESS":
        try:
            from notifications.tasks import send_payment_confirmation_sms
            send_payment_confirmation_sms(str(tx.user.id), str(tx.id))
        except Exception:
            logger.exception(
                "SMS de confirmation non envoyé pour %s (paiement bien "
                "enregistré, à relancer manuellement si besoin).", tx.reference,
            )
        message = {
            "type":    "payment_success",
            "message": "Paiement confirmé ! Votre abonnement est maintenant actif.",
            "ref":     tx.reference,
        }
    else:
        message = {
            "type":    "payment_failed",
            "message": "Votre paiement a échoué. Veuillez réessayer.",
            "ref":     tx.reference,
        }
    try:
        from notifications.sse import push_notification
        push_notification(str(tx.user.id), message)
    except Exception:
        logger.exception("Notification SSE non transmise pour %s.", tx.reference)


def claim_orphan_callbacks(tx) -> bool:
    """
    Rattache immédiatement un éventuel callback arrivé AVANT l'enregistrement
    du `gateway_ref`.

    Les paiements Mobile Money sont quasi instantanés : LengoPay peut notifier
    avant que l'initiation n'ait fini d'écrire `gateway_ref` en base. Sans ce
    rattrapage, la notification serait perdue et le client attendrait le cron.

    Retourne True si un callback a été trouvé et doit être rejoué.
    """
    if not tx.gateway_ref:
        return False
    try:
        existe = PaymentCallback.objects.filter(
            pay_id=tx.gateway_ref,
            outcome=PaymentCallback.Outcome.ORPHAN,
            replayed=False,
        ).exists()
    except Exception:
        logger.exception("Recherche de callback orphelin impossible pour %s.", tx.reference)
        return False
    if existe:
        logger.warning(
            "Callback orphelin déjà reçu pour %s (pay_id=%s) : rejeu immédiat.",
            tx.reference, tx.gateway_ref,
        )
    return existe


def _gen_ref(): return f"KHR-{uuid.uuid4().hex[:12].upper()}"


def _is_admin(request):
    return IsAdmin().has_permission(request, None)


def _call_lengopay(amount, currency, reference):
    """Cree un paiement Cash In via le client officiel (payments/lengopay.py)."""
    return _lengopay_create(amount, currency, reference)


def _get_plan(plan_id_or_name: str):
    """Résout un plan par UUID ou par nom/alias."""
    try:
        return Plan.objects.get(id=plan_id_or_name, is_active=True)
    except Exception:
        pass
    name_map = {
        "seller":    "Boutique Vendeur",
        "boutique":  "Boutique Vendeur",
        "mensuel":   "Premium Mensuel",
        "annuel":    "Premium Annuel",
        "gratuit":   "Gratuit",
    }
    mapped = name_map.get(plan_id_or_name.lower(), plan_id_or_name)
    try:
        return Plan.objects.get(name__iexact=mapped, is_active=True)
    except Plan.DoesNotExist:
        return None


# ─── GET + POST /payments/plans/ ─────────────────────────────────────────────
class PlanListView(APIView):
    """
    GET  → liste tous les plans actifs (tous les utilisateurs)
    POST → créer un nouveau plan (admin uniquement)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True)
        return success_response(data=PlanSerializer(plans, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)

        s = PlanSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        plan = s.save()

        logger.info("Plan créé : %s (%s %s)", plan.name, plan.price, plan.currency)
        return success_response(
            data=PlanSerializer(plan).data,
            message="Plan créé avec succès.",
            status=201,
        )


# ─── PATCH + DELETE /payments/plans/<pk>/ ────────────────────────────────────
class PlanDetailView(APIView):
    """
    PATCH  → modifier un plan (admin)
    DELETE → supprimer un plan (admin)
    """
    permission_classes = [IsAuthenticated]

    def _get_plan(self, pk):
        try:
            return Plan.objects.get(id=pk)
        except Plan.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _is_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)

        plan = self._get_plan(pk)
        if not plan:
            return error_response("Plan introuvable.", status=404)

        s = PlanSerializer(plan, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()

        logger.info("Plan mis à jour : %s", plan.name)
        return success_response(
            data=PlanSerializer(plan).data,
            message="Plan mis à jour.",
        )

    def delete(self, request, pk):
        if not _is_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)

        plan = self._get_plan(pk)
        if not plan:
            return error_response("Plan introuvable.", status=404)

        # Désactiver plutôt que supprimer (préserve les abonnements existants)
        plan.is_active = False
        plan.save(update_fields=["is_active"])

        logger.info("Plan désactivé : %s", plan.name)
        return success_response(message=f"Plan '{plan.name}' supprimé.")


# ─── GET /payments/subscriptions/status/ ─────────────────────────────────────
class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub  = request.user.subscription
            data = {
                "is_premium": sub.is_active(),
                "status":     sub.status,
                "plan":       PlanSerializer(sub.plan).data if sub.plan else None,
                "end_date":   sub.end_date,
            }
        except Subscription.DoesNotExist:
            data = {"is_premium": False, "status": "NONE", "plan": None, "end_date": None}
        return success_response(data=data)


# ─── POST /payments/subscriptions/initiate/ ──────────────────────────────────
class SubscriptionInitiateView(APIView):
    """
    Body : { plan_id: "UUID" | "seller" | "mensuel" | "annuel", currency: "GNF" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            plan_id  = request.data.get("plan_id", "")
            currency = request.data.get("currency", settings.LENGOPAY_CURRENCY)

            if not plan_id:
                return error_response("plan_id est obligatoire.", status=400)

            plan = _get_plan(str(plan_id))

            if not plan:
                return error_response(
                    f"Plan '{plan_id}' introuvable.",
                    status=404,
                )
            final_amount = Decimal(plan.price)

            # Plan gratuit → activer directement
            if final_amount == Decimal("0"):
                sub, _ = Subscription.objects.get_or_create(user=request.user)
                sub.plan = plan; sub.status = Subscription.Status.ACTIVE
                sub.start_date = timezone.now(); sub.end_date = None
                sub.save()
                return success_response(data={"is_premium": False}, message="Plan gratuit activé.")

            ref = _gen_ref()
            sub, _ = Subscription.objects.get_or_create(user=request.user)
            sub.plan = plan
            sub.status = Subscription.Status.PENDING
            sub.save(update_fields=["plan", "status"])

            tx = Transaction.objects.create(
                user=request.user, subscription=sub, reference=ref,
                amount=final_amount, currency=plan.currency,
                provider=Transaction.Provider.LENGOPAY, phone=request.user.phone or "",
            )

            result = _call_lengopay(final_amount, plan.currency, ref)
            if not result["success"]:
                return error_response(
                    "Impossible de générer le lien de paiement.",
                    errors=result.get("error"), status=502,
                )

            tx.gateway_ref = result["pay_id"]
            tx.save(update_fields=["gateway_ref"])

            # Le callback peut arriver avant cette ligne (Mobile Money quasi
            # instantané) : on rejoue immédiatement toute notification déjà
            # reçue pour ce pay_id.
            if claim_orphan_callbacks(tx):
                try:
                    from .cron import replay_orphan_callbacks
                    replay_orphan_callbacks(pay_id=tx.gateway_ref)
                except Exception:
                    logger.exception(
                        "Rejeu du callback orphelin impossible pour %s.", tx.reference
                    )

            return success_response(
                data={"reference": ref, "pay_id": result["pay_id"],
                      "payment_url": result["payment_url"]},
                status=201,
            )
        except Exception as exc:
            logger.error("ERREUR paiement : %s", traceback.format_exc())
            return error_response(f"Erreur interne : {str(exc)}", status=500)


# ─── POST /payments/initiate/ ────────────────────────────────────────────────
class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            s = PaymentInitiateSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            data = s.validated_data
            from ecommerce.models import Order
            try:
                order = Order.objects.get(
                    id=data["order_id"], user=request.user, status=Order.Status.PENDING
                )
            except Order.DoesNotExist:
                return error_response("Commande introuvable ou déjà traitée.", status=404)
            if order.total <= 0:
                return error_response("Montant de commande invalide.", status=400)
            ref  = _gen_ref()
            tx   = Transaction.objects.create(
                user=request.user, reference=ref,
                amount=order.total,
                currency=order.currency,
                provider=Transaction.Provider.LENGOPAY,
                phone=request.user.phone or "",
                order=order,
            )

            result = _call_lengopay(
                order.total,
                order.currency,
                ref,
            )
            if not result["success"]:
                return error_response("Impossible de générer le lien.", errors=result.get("error"), status=502)

            tx.gateway_ref = result["pay_id"]
            tx.save(update_fields=["gateway_ref"])

            # Le callback peut arriver avant cette ligne (Mobile Money quasi
            # instantané) : on rejoue immédiatement toute notification déjà
            # reçue pour ce pay_id.
            if claim_orphan_callbacks(tx):
                try:
                    from .cron import replay_orphan_callbacks
                    replay_orphan_callbacks(pay_id=tx.gateway_ref)
                except Exception:
                    logger.exception(
                        "Rejeu du callback orphelin impossible pour %s.", tx.reference
                    )
            return success_response(
                data={"reference": ref, "pay_id": result["pay_id"],
                      "payment_url": result["payment_url"], "transaction_id": str(tx.id)},
                status=201,
            )
        except Exception as exc:
            logger.error("ERREUR paiement commande : %s", traceback.format_exc())
            return error_response(f"Erreur interne : {str(exc)}", status=500)


# ─── POST /payments/webhook/ ─────────────────────────────────────────────────
class PaymentWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/<token>/   ← URL transmise à LengoPay
    POST /api/v1/payments/webhook/           ← ancienne URL, conservée

    Charge utile envoyée par LengoPay (documentation officielle) :
        {"pay_id": "...", "status": "SUCCESS", "amount": 1500,
         "message": "Transaction Successful", "Client": "624897845"}

    LengoPay ne signe pas ses notifications. L'authentification repose donc sur
    un secret partagé placé dans l'URL de callback (LENGOPAY_CALLBACK_TOKEN),
    complété par une vérification serveur-à-serveur du statut et un contrôle du
    montant. Chaque appel est journalisé dans PaymentCallback.

    Réponses : toujours HTTP 200 dès que la charge utile est exploitable, afin
    que LengoPay ne rejoue pas indéfiniment. Les cas non appliqués sont repris
    par la tâche de réconciliation.
    """

    permission_classes = [WebhookPermission]
    authentication_classes = []

    # ── Authentification ─────────────────────────────────────────────────────
    @staticmethod
    def _verify_token(token) -> bool:
        """Compare le jeton d'URL au secret configuré, en temps constant."""
        expected = str(getattr(settings, "LENGOPAY_CALLBACK_TOKEN", "") or "").strip()
        supplied = str(token or "").strip()
        if not expected or not supplied:
            return False
        return hmac.compare_digest(supplied, expected)

    @staticmethod
    def _verify_signature(raw_body: bytes, signature: str) -> bool:
        """
        Vérification HMAC facultative : utilisée seulement si un secret est
        configuré ET qu'une signature est présente. Prévue pour une passerelle
        intermédiaire ou une évolution future du fournisseur.
        """
        secret = str(getattr(settings, "LENGOPAY_WEBHOOK_SECRET", "") or "").strip()
        if not secret or not signature:
            return False
        supplied = signature.removeprefix("sha256=").strip()
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(supplied, expected)

    @staticmethod
    def _client_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        return str(request.META.get("REMOTE_ADDR", ""))[:64]

    @staticmethod
    def _log_callback(**kwargs):
        """
        Journalise le callback. Ne doit JAMAIS faire échouer la requête :
        perdre une trace est ennuyeux, perdre un paiement est grave.
        """
        try:
            return PaymentCallback.objects.create(**kwargs)
        except Exception:
            logger.exception("Journalisation du callback LengoPay impossible.")
            return None

    # ── Diagnostic de joignabilité ───────────────────────────────────────────
    def get(self, request, token=None):
        """
        Permet de vérifier depuis l'extérieur que l'URL de callback est bien
        atteignable (utile pour diagnostiquer un « souci de callback ») sans
        rien révéler ni rien modifier.
        """
        return Response(
            {"detail": "Endpoint de callback LengoPay actif. Utiliser POST."},
            status=200,
        )

    # ── Traitement du callback ───────────────────────────────────────────────
    def post(self, request, token=None):
        raw_body = request.body
        signature = request.headers.get("X-LengoPay-Signature", "")
        payload = request.data if isinstance(request.data, dict) else {}
        pay_id = str(payload.get("pay_id", "") or "").strip()
        announced_raw = str(payload.get("status", "") or "").strip()
        announced = normalize_status(announced_raw)
        source_ip = self._client_ip(request)

        logger.info(
            "Webhook LengoPay | pay_id=%s | statut annoncé=%r | ip=%s",
            pay_id, announced_raw, source_ip,
        )

        if not pay_id:
            self._log_callback(
                pay_id="", announced_status=announced_raw[:32],
                outcome=PaymentCallback.Outcome.INVALID,
                source_ip=source_ip, payload=payload or None,
                detail="pay_id absent de la charge utile.",
            )
            return Response({"error": "pay_id manquant"}, status=400)

        # 1. Authentification de l'émetteur.
        if self._verify_token(token):
            auth_method = "url_token"
        elif self._verify_signature(raw_body, signature):
            auth_method = "hmac"
        else:
            auth_method = ""

        # 2. Confirmation serveur-à-serveur (source de vérité quand elle
        #    répond). Un échec ici ne bloque plus le traitement.
        api_state, api_amount = transaction_status(pay_id)

        # 3. Détermination du statut à appliquer.
        if api_state is not None:
            state = api_state
            if announced and announced != api_state:
                logger.warning(
                    "Callback %s : statut annoncé %r ≠ statut réel %r "
                    "(source ip=%s). Le statut de l'API fait foi.",
                    pay_id, announced_raw, api_state, source_ip,
                )
            source = "api"
        elif auth_method and not settings.LENGOPAY_REQUIRE_STATUS_CONFIRMATION:
            # L'API n'a pas répondu, mais l'appel est authentifié : on applique
            # le statut annoncé, avec contrôle du montant plus bas.
            state = announced
            source = f"callback({auth_method})"
            logger.warning(
                "Callback %s appliqué sans confirmation API "
                "(authentifié par %s). Vérifier la disponibilité de %s.",
                pay_id, auth_method, settings.LENGOPAY_STATUS_URL,
            )
        else:
            reason = (
                "callback non authentifié et confirmation API indisponible"
                if not auth_method
                else "confirmation API obligatoire mais indisponible"
            )
            logger.error(
                "Callback %s NON appliqué : %s. Transaction laissée en "
                "attente, reprise par la réconciliation.", pay_id, reason,
            )
            tx_ref = Transaction.objects.filter(gateway_ref=pay_id).first()
            self._log_callback(
                pay_id=pay_id, transaction=tx_ref,
                announced_status=announced_raw[:32],
                outcome=PaymentCallback.Outcome.UNVERIFIED,
                auth_method=auth_method, source_ip=source_ip,
                payload=payload or None, detail=reason,
            )
            return Response({"received": True, "verified": False}, status=200)

        if state is None:
            self._log_callback(
                pay_id=pay_id, announced_status=announced_raw[:32],
                outcome=PaymentCallback.Outcome.INVALID,
                auth_method=auth_method, source_ip=source_ip,
                payload=payload or None,
                detail=f"Statut non interprétable : {announced_raw!r}",
            )
            return Response({"error": "status invalide"}, status=400)

        if state == "PENDING":
            self._log_callback(
                pay_id=pay_id, announced_status=announced_raw[:32],
                applied_status="PENDING",
                outcome=PaymentCallback.Outcome.PENDING,
                auth_method=auth_method, source_ip=source_ip,
                payload=payload or None, detail=f"Statut fourni par {source}.",
            )
            return Response({"received": True, "pending": True}, status=200)

        # 4. Rapprochement avec la transaction locale.
        tx = Transaction.objects.filter(gateway_ref=pay_id).first()
        if not tx:
            # Course possible : le callback Mobile Money peut arriver avant que
            # l'initiation ait enregistré le gateway_ref. On conserve la
            # notification, le cron la rejouera.
            logger.error(
                "Callback %s : aucune transaction avec ce gateway_ref. "
                "Callback conservé pour rejeu.", pay_id,
            )
            self._log_callback(
                pay_id=pay_id, announced_status=announced_raw[:32],
                applied_status=state,
                outcome=PaymentCallback.Outcome.ORPHAN,
                auth_method=auth_method, source_ip=source_ip,
                payload=payload or None,
                detail="gateway_ref inconnu au moment du callback.",
            )
            return Response({"received": True}, status=200)

        # 5. Contrôle du montant (défense en profondeur : empêche l'activation
        #    d'un abonnement avec un montant inférieur au prix du plan).
        reported = api_amount if api_amount is not None else to_decimal(payload.get("amount"))
        if state == "SUCCESS" and reported is not None:
            tolerance = to_decimal(settings.LENGOPAY_AMOUNT_TOLERANCE) or Decimal("0")
            ecart = abs(Decimal(tx.amount) - reported)
            if ecart > tolerance:
                logger.error(
                    "Callback %s REFUSÉ : montant %s ≠ montant attendu %s "
                    "(écart %s, tolérance %s, ip=%s).",
                    pay_id, reported, tx.amount, ecart, tolerance, source_ip,
                )
                self._log_callback(
                    pay_id=pay_id, transaction=tx,
                    announced_status=announced_raw[:32], applied_status="",
                    outcome=PaymentCallback.Outcome.MISMATCH,
                    auth_method=auth_method, source_ip=source_ip,
                    payload=payload or None,
                    detail=f"Montant reçu {reported} ≠ attendu {tx.amount}.",
                )
                return Response({"received": True, "verified": False}, status=200)

        # 6. Application idempotente.
        try:
            with transaction.atomic():
                tx = Transaction.objects.select_for_update().select_related(
                    "user", "subscription__plan", "order"
                ).get(pk=tx.pk)

                if tx.status == Transaction.Status.SUCCESS:
                    self._log_callback(
                        pay_id=pay_id, transaction=tx,
                        announced_status=announced_raw[:32], applied_status=state,
                        outcome=PaymentCallback.Outcome.DUPLICATE,
                        auth_method=auth_method, source_ip=source_ip,
                        payload=payload or None,
                        detail="Transaction déjà réussie, aucune action.",
                    )
                    return Response({"received": True, "duplicate": True}, status=200)

                # Un échec est un état terminal. Ne le rouvrir que si l'API
                # LengoPay l'affirme elle-même : sinon, quiconque connaîtrait
                # le jeton pourrait « ressusciter » un paiement refusé. Le cas
                # reste possible (LengoPay confirmant tardivement un
                # encaissement) car refuser reviendrait à garder l'argent d'un
                # client sans lui donner son abonnement.
                if tx.status == Transaction.Status.FAILED and state == "SUCCESS":
                    if source != "api":
                        logger.error(
                            "Callback %s REFUSÉ : tentative de repasser une "
                            "transaction FAILED en SUCCESS sans confirmation "
                            "de l'API LengoPay (source=%s, ip=%s).",
                            pay_id, source, source_ip,
                        )
                        self._log_callback(
                            pay_id=pay_id, transaction=tx,
                            announced_status=announced_raw[:32], applied_status="",
                            outcome=PaymentCallback.Outcome.UNVERIFIED,
                            auth_method=auth_method, source_ip=source_ip,
                            payload=payload or None,
                            detail="Réouverture d'un échec refusée : "
                                   "confirmation API absente.",
                        )
                        return Response({"received": True, "verified": False}, status=200)
                    logger.warning(
                        "Callback %s : transaction FAILED repassée en SUCCESS "
                        "sur confirmation de l'API LengoPay. À vérifier "
                        "manuellement (ip=%s).", pay_id, source_ip,
                    )

                if tx.status == Transaction.Status.REFUNDED:
                    self._log_callback(
                        pay_id=pay_id, transaction=tx,
                        announced_status=announced_raw[:32], applied_status="",
                        outcome=PaymentCallback.Outcome.DUPLICATE,
                        auth_method=auth_method, source_ip=source_ip,
                        payload=payload or None,
                        detail="Transaction remboursée, callback ignoré.",
                    )
                    return Response({"received": True}, status=200)

                champs = ["status", "webhook_payload"]
                tx.webhook_payload = payload or {}
                telephone = extract_phone(payload)
                if telephone and not tx.phone:
                    tx.phone = telephone
                    champs.append("phone")

                if state == "SUCCESS":
                    tx.status = Transaction.Status.SUCCESS
                    tx.save(update_fields=champs)
                    self._activate(tx)
                    self._confirm_order(tx)
                else:
                    tx.status = Transaction.Status.FAILED
                    tx.save(update_fields=champs)
        except Exception:
            logger.exception("Callback %s : erreur pendant l'application.", pay_id)
            self._log_callback(
                pay_id=pay_id, announced_status=announced_raw[:32],
                applied_status=state,
                outcome=PaymentCallback.Outcome.ERROR,
                auth_method=auth_method, source_ip=source_ip,
                payload=payload or None, detail=traceback.format_exc()[:4000],
            )
            # 500 : LengoPay réessaiera, ce qui est le comportement souhaité
            # puisque rien n'a été enregistré.
            return Response({"received": False, "error": "erreur interne"}, status=500)

        self._log_callback(
            pay_id=pay_id, transaction=tx,
            announced_status=announced_raw[:32], applied_status=state,
            outcome=PaymentCallback.Outcome.APPLIED,
            auth_method=auth_method, source_ip=source_ip,
            payload=payload or None, detail=f"Statut fourni par {source}.",
        )
        logger.info("Callback %s appliqué : %s (%s).", pay_id, state, source)

        # ── Effets secondaires NON bloquants ────────────────────────────────
        # Le paiement est déjà enregistré en base. Si le SMS ou la notification
        # temps réel échoue (Redis/Celery indisponible), il ne faut SURTOUT PAS
        # renvoyer une erreur : LengoPay rejouerait le callback en boucle alors
        # que l'argent est encaissé et l'abonnement activé.
        notify_payment_result(tx, state)
        return Response({"received": True, "status": state}, status=200)

    def _activate(self, tx):
        if not tx.subscription or not tx.subscription.plan: return
        sub = tx.subscription; plan = sub.plan; now = timezone.now()
        if plan and plan.period == "MENSUEL":      end = now + timedelta(days=30)
        elif plan and plan.period == "ANNUEL":     end = now + timedelta(days=365)
        elif plan and plan.period == "SEMESTRIEL": end = now + timedelta(days=183)
        else: end = None
        sub.status = Subscription.Status.ACTIVE
        sub.start_date = now; sub.end_date = end
        sub.save(update_fields=["status", "start_date", "end_date"])
        # Mettre à jour le cache Redis
        from core.redis_utils import subscription_set_active
        subscription_set_active(str(tx.user.id), end)

    def _confirm_order(self, tx):
        if not tx.order: return
        tx.order.status = "PAID"; tx.order.save(update_fields=["status"])


# ─── GET /payments/callbacks/ ────────────────────────────────────────────────
class CallbackLogView(APIView):
    """
    GET /api/v1/payments/callbacks/?limit=50&outcome=UNVERIFIED

    Journal des notifications LengoPay reçues. Réservé aux administrateurs.
    Premier réflexe de diagnostic quand un client dit avoir payé sans avoir
    obtenu son abonnement : si aucune ligne n'apparaît, LengoPay n'a pas
    atteint le serveur (URL, pare-feu, DNS). Si une ligne apparaît avec un
    `outcome` autre que APPLIED, le motif exact est dans `detail`.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 50)), 500)
        except (TypeError, ValueError):
            limit = 50

        qs = PaymentCallback.objects.select_related("transaction").all()

        outcome = str(request.query_params.get("outcome", "")).strip().upper()
        if outcome:
            qs = qs.filter(outcome=outcome)
        pay_id = str(request.query_params.get("pay_id", "")).strip()
        if pay_id:
            qs = qs.filter(pay_id=pay_id)

        data = [
            {
                "id":               str(cb.id),
                "created_at":       cb.created_at,
                "pay_id":           cb.pay_id,
                "outcome":          cb.outcome,
                "announced_status": cb.announced_status,
                "applied_status":   cb.applied_status,
                "auth_method":      cb.auth_method or "aucune",
                "source_ip":        cb.source_ip,
                "replayed":         cb.replayed,
                "reference":        cb.transaction.reference if cb.transaction else None,
                "detail":           cb.detail,
                "payload":          cb.payload,
            }
            for cb in qs[:limit]
        ]
        return success_response(data=data)


# ─── GET /payments/transactions/ ─────────────────────────────────────────────
class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin(request):
            txs = Transaction.objects.select_related("user").all()
        else:
            txs = Transaction.objects.filter(user=request.user)
        return success_response(data=TransactionSerializer(txs, many=True).data)


# ─── POST /payments/run-cron/ ─────────────────────────────────────────────────
class RunCronView(APIView):
    """
    Appelé par cron-job.org toutes les heures.
    Protégé par un secret dans le header X-Cron-Secret.
    Tâches :
      1. Expirer les abonnements dépassés
      2. Réconcilier les paiements restés en attente auprès de LengoPay
      3. Nettoyer les OTPs expirés
      4. Avertir les abonnés dont l'abonnement expire dans 3 jours
    """
    permission_classes     = []
    authentication_classes = []

    def post(self, request):
        secret   = request.headers.get("X-Cron-Secret", "")
        expected = getattr(settings, "CRON_SECRET", "")

        if not expected or secret != expected:
            logger.warning("run-cron : secret invalide depuis %s",
                           request.META.get("REMOTE_ADDR"))
            return Response({"error": "Non autorisé"}, status=403)

        results = {}

        # 1. Expirer les abonnements dépassés
        try:
            from payments.cron import check_expired_subscriptions
            check_expired_subscriptions()
            results["subscriptions"] = "ok"
        except Exception as exc:
            logger.error("Cron subscriptions : %s", exc)
            results["subscriptions"] = str(exc)

        # 1 bis. Rattraper les paiements dont le callback s'est perdu
        try:
            from payments.cron import reconcile_pending_payments
            results["payments_reconciled"] = reconcile_pending_payments()
        except Exception as exc:
            logger.error("Cron réconciliation paiements : %s", exc)
            results["payments_reconciled"] = str(exc)

        # 2. Nettoyer les OTPs expirés
        try:
            from users.cron import cleanup_expired_otps
            cleanup_expired_otps()
            results["otps"] = "ok"
        except Exception as exc:
            logger.error("Cron OTPs : %s", exc)
            results["otps"] = str(exc)

        # 3. Avertir les abonnés qui expirent dans 3 jours
        try:
            _warn_expiring_subscriptions()
            results["expiry_warnings"] = "ok"
        except Exception as exc:
            logger.error("Cron expiry warnings : %s", exc)
            results["expiry_warnings"] = str(exc)

        logger.info("Cron exécuté : %s", results)
        return Response({"status": "ok", "results": results})


def _warn_expiring_subscriptions():
    """
    Envoie un SMS aux abonnés qui expirent dans exactement 3 jours.

    La fenêtre d'examen est d'UNE HEURE : cette fonction doit donc être
    exécutée toutes les heures (c'est ce que fait Celery Beat), sinon
    certains abonnés ne seraient jamais prévenus.

    Retourne le nombre d'avertissements envoyés.
    """
    from datetime import timedelta
    from django.utils import timezone
    from notifications.tasks import send_subscription_expiry_warning_task

    in_3_days_start = timezone.now() + timedelta(days=3)
    in_3_days_end   = in_3_days_start + timedelta(hours=1)

    expiring = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        end_date__gte=in_3_days_start,
        end_date__lt=in_3_days_end,
    ).select_related("user")

    envoyes = 0
    for sub in expiring:
        send_subscription_expiry_warning_task.delay(str(sub.user.id), 3)
        logger.info("Avertissement expiration envoyé à user=%s", sub.user.id)
        envoyes += 1
    return envoyes
