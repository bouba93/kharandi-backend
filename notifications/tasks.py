"""
notifications/tasks.py — SMS Nimba + Tâches Celery
────────────────────────────────────────────────────
OTP : synchrone (l'utilisateur attend)
SMS : asynchrone via Celery
"""
import base64, http.client, json, logging, secrets
from django.conf import settings
from django.core.cache import cache
from celery import shared_task

logger = logging.getLogger(__name__)

OTP_TTL = 300  # 5 minutes


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT NIMBA SMS
# ══════════════════════════════════════════════════════════════════════════════

def _auth():
    return "Basic " + base64.b64encode(
        f"{settings.NIMBA_ACCOUNT_SID}:{settings.NIMBA_AUTH_TOKEN}".encode()
    ).decode()

def _request(method, endpoint, body):
    conn = http.client.HTTPSConnection("api.nimbasms.com", timeout=15)
    try:
        conn.request(method, endpoint, json.dumps(body),
                     {"authorization": _auth(), "content-type": "application/json"})
        res  = conn.getresponse()
        raw  = res.read().decode("utf-8")
        logger.info("Nimba [%s %s] → %d : %s", method, endpoint, res.status, raw[:300])
        return {"status": res.status, "data": json.loads(raw) if raw else {}}
    except Exception as exc:
        logger.error("Erreur Nimba [%s %s] : %s", method, endpoint, exc)
        return {"status": 500, "data": {"error": str(exc)}}
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  OTP
# ══════════════════════════════════════════════════════════════════════════════

def _local_otp_key(phone: str) -> str:
    return f"otp_local:{phone}"

def send_otp_sms(phone: str) -> dict:
    """
    Envoie OTP via Nimba SMS.
    Stocke aussi le code localement dans Redis comme fallback.
    """
    # Générer un code local de 6 chiffres
    local_code = str(secrets.randbelow(900000) + 100000)
    cache.set(_local_otp_key(phone), local_code, timeout=OTP_TTL)

    if not settings.NIMBA_ACCOUNT_SID or not settings.NIMBA_AUTH_TOKEN:
        logger.warning("Nimba non configuré — OTP local uniquement pour %s", phone)
        # Le fallback local est réservé au développement : en production il ne
        # faut jamais annoncer qu'un SMS a été envoyé quand aucun fournisseur
        # n'est configuré.
        return {
            "success": bool(settings.DEBUG),
            "verificationid": "",
            "local_code": local_code if settings.DEBUG else "",
        }

    r = _request("POST", "/v1/verifications", {
        "to":          phone.strip(),
        "sender_name": settings.NIMBA_SENDER_NAME,
        "channel":     "sms",
        "message":     f"Kharandi : votre code est <{local_code}>. Valable 5 minutes.",
        "expiry_time": 5,
        "attempts":    5,
        "code_length": 6,
        "language":    "fr",
    })

    if r["status"] in (200, 201):
        # Nimba peut retourner "verificationid" ou "verificationId" (camelCase)
        d   = r["data"]
        vid = (d.get("verificationid")
               or d.get("verificationId")
               or d.get("id")
               or "")
        logger.info("✅ OTP Nimba envoyé à %s | vid=%s | local=%s", phone, vid, local_code)
        return {"success": True, "verificationid": vid, "local_code": local_code}

    logger.error("❌ Nimba OTP échoué pour %s : %s", phone, r["data"])
    # Fallback : SMS classique avec le code local
    sent = _send_sms_now(
        phone,
        f"Kharandi : votre code de connexion est {local_code}. Valable 5 minutes.",
    )
    return {
        "success": sent,
        "verificationid": "",
        "local_code": local_code if settings.DEBUG else "",
    }


def verify_otp_sms(verificationid: str, code: str, phone: str = "") -> bool:
    """
    Vérifie l'OTP.
    1. Vérifie d'abord via Nimba si verificationid disponible
    2. Sinon vérifie le code local stocké dans Redis (fallback fiable)
    """
    # Fallback local — toujours disponible
    if phone:
        local_code = cache.get(_local_otp_key(phone))
        if local_code and str(local_code) == str(code).strip():
            cache.delete(_local_otp_key(phone))
            logger.info("✅ OTP vérifié localement pour %s", phone)
            return True

    # Vérification Nimba si verificationid disponible
    if verificationid:
        try:
            r = _request("PATCH", f"/v1/verifications/{verificationid}", {"code": int(code)})
            if r["status"] == 200:
                status = r["data"].get("status", "")
                logger.info("OTP Nimba → status=%s", status)
                if status == "approved":
                    return True
        except Exception as exc:
            logger.error("Erreur vérification Nimba : %s", exc)

    logger.warning("❌ OTP non vérifié — phone=%s vid=%s", phone, verificationid)
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  SMS CLASSIQUE
# ══════════════════════════════════════════════════════════════════════════════

def _send_sms_now(phone: str, message: str) -> bool:
    if not settings.NIMBA_ACCOUNT_SID:
        logger.warning("Nimba non configuré — SMS ignoré pour %s", phone)
        return False
    r = _request("POST", "/v1/messages", {
        "sender_name": settings.NIMBA_SENDER_NAME,
        "to": [phone.strip()], "message": message, "channel": "sms",
    })
    ok = r["status"] in (200, 201)
    if ok:  logger.info("✅ SMS envoyé à %s", phone)
    else:   logger.error("❌ SMS échoué pour %s : %s", phone, r["data"])
    return ok

def send_sms(phone: str, message: str) -> bool:
    return _send_sms_now(phone, message)


# ══════════════════════════════════════════════════════════════════════════════
#  TÂCHES CELERY
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3, default_retry_delay=30, name="notifications.send_welcome_sms")
def send_welcome_sms_task(self, user_id: str):
    try:
        from users.models import User
        user   = User.objects.select_related("profile").get(id=user_id)
        prenom = ""
        if hasattr(user, "profile") and user.profile and user.profile.first_name:
            prenom = f", {user.profile.first_name}"
        _send_sms_now(user.phone,
            f"Bienvenue sur Kharandi{prenom} ! 🎓 "
            f"Commence à réviser le BAC avec Karamö. kharandi.gn")
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=30, name="notifications.send_payment_sms")
def send_payment_confirmation_sms_task(self, user_id: str, transaction_id: str):
    try:
        from users.models import User
        from payments.models import Transaction
        user = User.objects.get(id=user_id)
        tx   = Transaction.objects.select_related("subscription__plan").get(id=transaction_id)
        plan = tx.subscription.plan.name if tx.subscription and tx.subscription.plan else "Votre achat"
        _send_sms_now(user.phone,
            f"Paiement confirmé ! {plan} — {int(tx.amount):,} {tx.currency}. "
            f"Ref : {tx.reference}. Merci 🎓")
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(name="notifications.send_subscription_expiry_warning")
def send_subscription_expiry_warning_task(user_id: str, days_remaining: int):
    try:
        from users.models import User
        user = User.objects.get(id=user_id)
        _send_sms_now(user.phone,
            f"⚠️ Kharandi : votre abonnement expire dans {days_remaining} jour(s). "
            f"Renouvelez sur kharandi.gn.")
    except Exception as exc:
        logger.error("Erreur SMS expiry : %s", exc)

@shared_task(bind=True, max_retries=2, name="notifications.send_bulk_sms")
def send_bulk_sms_task(self, phones: list, message: str):
    sent = sum(1 for p in phones if _send_sms_now(p, message))
    return {"sent": sent, "total": len(phones)}

def send_welcome_sms(user_id: str):
    send_welcome_sms_task.delay(user_id)

def send_payment_confirmation_sms(user_id: str, transaction_id: str):
    send_payment_confirmation_sms_task.delay(user_id, transaction_id)

def send_email(*args, **kwargs):
    return False
