"""
users/device_auth.py — Sécurité appareil Kharandi
──────────────────────────────────────────────────
Règle : 1 seul appareil de confiance par utilisateur.

Flux :
  ✅ Token connu + bon user         → connexion directe (0 OTP)
  🚫 Token appartient à autre user  → BLOQUÉ (vol de compte)
  🔑 Pas de token / token stale     → OTP requis (cas normal)

IMPORTANT :
  - Un token stale (inexistant en DB) = OTP, jamais bloqué
  - Logout ne supprime PAS le token localStorage → reconnexion directe
  - Seul le vol réel de token est bloqué
"""
import logging
import uuid as uuid_lib

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    for header in ("HTTP_CF_CONNECTING_IP", "HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"):
        ip = request.META.get(header, "").split(",")[0].strip()
        if ip:
            return ip
    return "0.0.0.0"


def get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:500]


def validate_device(request, user) -> dict:
    """
    Statuts retournés :
      "trusted"  → token valide pour cet utilisateur → connexion directe
      "blocked"  → token appartient à un AUTRE utilisateur → vol potentiel
      "new"      → pas de token, token stale, ou token invalide → OTP
    """
    from .models import UserDevice

    token_str = request.META.get("HTTP_X_DEVICE_TOKEN", "").strip()

    # Pas de token → OTP
    if not token_str:
        return {"status": "new", "trusted": False, "blocked": False, "device": None}

    # UUID invalide → traiter comme pas de token (jamais bloquer)
    try:
        token_uuid = uuid_lib.UUID(token_str)
    except ValueError:
        return {"status": "new", "trusted": False, "blocked": False, "device": None}

    # Chercher le device pour CET utilisateur
    try:
        device = UserDevice.objects.get(device_token=token_uuid, user=user)
        # ✅ Trouvé → connexion directe
        current_ip = get_client_ip(request)
        ip_changed = bool(device.last_ip) and (device.last_ip != current_ip)
        device.last_ip    = current_ip
        device.user_agent = get_user_agent(request)
        device.save(update_fields=["last_ip", "user_agent", "last_used"])
        return {
            "status":     "trusted",
            "trusted":    True,
            "blocked":    False,
            "ip_changed": ip_changed,
            "device":     device,
        }
    except UserDevice.DoesNotExist:
        pass

    # Token pas trouvé pour cet user — vérifier s'il appartient à quelqu'un d'autre
    belongs_to_other = UserDevice.objects.filter(
        device_token=token_uuid
    ).exclude(user=user).exists()

    if belongs_to_other:
        # 🚫 Token d'un autre utilisateur → vol potentiel
        logger.warning("🚫 Token volé détecté — user=%s ip=%s", user.phone, get_client_ip(request))
        return {"status": "blocked", "trusted": False, "blocked": True, "device": None}

    # Token simplement stale (DB reset, migration, révocation) → OTP normal
    logger.info("Token stale pour %s → OTP requis", user.phone)
    return {"status": "new", "trusted": False, "blocked": False, "device": None}


def create_device(request, user) -> "UserDevice":
    """Révoque tous les anciens appareils et crée le nouveau."""
    from .models import UserDevice
    old = UserDevice.objects.filter(user=user).count()
    if old:
        UserDevice.objects.filter(user=user).delete()
        logger.info("Anciens appareils révoqués pour %s (%d)", user.phone, old)
    device = UserDevice.objects.create(
        user       = user,
        last_ip    = get_client_ip(request),
        user_agent = get_user_agent(request),
    )
    logger.info("✅ Appareil enregistré — %s token=%s...", user.phone, str(device.device_token)[:8])
    return device


def revoke_all_devices(user) -> int:
    from .models import UserDevice
    count = UserDevice.objects.filter(user=user).delete()[0]
    logger.info("Appareils révoqués — %s : %d", user.phone, count)
    return count


def send_new_device_notification(user, request):
    try:
        from content.models import Notification
        Notification.objects.create(
            user=user, title="🔐 Nouvelle connexion",
            message=(
                f"Connexion depuis un nouvel appareil.\n"
                f"IP : {get_client_ip(request)}\n"
                f"Navigateur : {get_user_agent(request)[:80]}\n"
                f"Si ce n'est pas vous, allez dans Paramètres → Sécurité."
            ),
            notif_type="warning",
        )
    except Exception as exc:
        logger.debug("Notif new device : %s", exc)


def send_blocked_device_notification(user, request):
    try:
        from content.models import Notification
        Notification.objects.create(
            user=user, title="🚨 Tentative de connexion suspecte",
            message=(
                f"Un token appartenant à un autre compte a été utilisé pour se connecter.\n"
                f"IP : {get_client_ip(request)}"
            ),
            notif_type="danger",
        )
        from notifications.tasks import send_sms
        send_sms(user.phone,
                 "🚨 Kharandi : tentative de connexion suspecte bloquée. "
                 "Contactez le support si besoin.")
    except Exception as exc:
        logger.debug("Notif blocked : %s", exc)


def send_ip_change_notification(user, request, old_ip: str):
    try:
        from content.models import Notification
        Notification.objects.create(
            user=user, title="📍 Nouveau réseau",
            message=f"Connexion depuis {get_client_ip(request)} (ancien : {old_ip or 'inconnu'}).",
            notif_type="info",
        )
    except Exception as exc:
        logger.debug("Notif IP : %s", exc)
