"""
users/views.py
──────────────
Connexion :
  - Admin           → phone + password → JWT direct
  - Appareil connu  → phone + device_token → JWT direct (0 OTP)
  - Sinon           → OTP → verify → JWT + device_token sauvegardé
Inscription automatique si compte inexistant lors du verify OTP.
"""
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import success_response, error_response
from .models import OTPRecord, Profile, User, UserDevice, PointTransaction
from .serializers import (
    OTPSendSerializer, OTPVerifySerializer,
    UserSerializer, ProfileUpdateSerializer,
)

logger = logging.getLogger(__name__)


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def _is_admin(request):
    from core.permissions import IsAdmin
    return IsAdmin().has_permission(request, None)

def _normalize_phone(phone: str) -> str:
    clean = phone.replace(" ", "").replace("-", "")
    if not clean:
        return ""
    if not clean.startswith("+"):
        clean = "+224" + clean.lstrip("0")
    return clean

def _get_device_token(request) -> str:
    return request.META.get("HTTP_X_DEVICE_TOKEN", "").strip()

def _find_device(token_str: str, user) -> "UserDevice | None":
    """Retourne le device si le token est valide pour cet utilisateur, sinon None."""
    import uuid as uuid_lib
    if not token_str:
        return None
    try:
        token_uuid = uuid_lib.UUID(token_str)
    except ValueError:
        return None
    try:
        return UserDevice.objects.get(device_token=token_uuid, user=user)
    except UserDevice.DoesNotExist:
        return None

def _register_device(request, user) -> str:
    """Crée un device de confiance. Retourne le device_token (string)."""
    from .device_auth import get_client_ip, get_user_agent
    # Un seul appareil par utilisateur
    UserDevice.objects.filter(user=user).delete()
    device = UserDevice.objects.create(
        user       = user,
        last_ip    = get_client_ip(request),
        user_agent = get_user_agent(request),
    )
    logger.info("Appareil enregistré — %s", user.phone)
    return str(device.device_token)

def _update_device(device, request):
    """Met à jour l'IP et l'user-agent du device."""
    from .device_auth import get_client_ip, get_user_agent
    device.last_ip    = get_client_ip(request)
    device.user_agent = get_user_agent(request)
    device.save(update_fields=["last_ip", "user_agent", "last_used"])


# ─── POST /auth/login/ ────────────────────────────────────────────────────────
class LoginView(APIView):
    """
    Cas 1 — Admin               : phone + password → JWT direct
    Cas 2 — Appareil de confiance : phone + X-Device-Token connu → JWT direct
    Cas 3 — Sinon               : OTP envoyé
    """
    permission_classes = [AllowAny]
    def post(self, request):
        phone    = request.data.get("phone",    "").strip()
        password = request.data.get("password", "").strip()

        if not phone:
            return error_response("Numéro de téléphone requis.", status=400)

        clean = _normalize_phone(phone)

        # Vérifier que l'utilisateur existe
        try:
            user = User.objects.select_related("profile").get(phone=clean)
        except User.DoesNotExist:
            return error_response(
                "Aucun compte trouvé. Veuillez vous inscrire.",
                status=404,
                errors={"code": "account_not_found"},
            )

        if not user.is_active:
            return error_response("Ce compte est désactivé.", status=403)

        # Connexion par mot de passe pour tous les rôles, y compris ADMIN.
        if password:
            if not user.check_password(password):
                return error_response("Identifiants incorrects.", status=401)
            device_token = _register_device(request, user)
            return success_response(
                data={
                    "user": UserSerializer(user).data,
                    "tokens": _get_tokens(user),
                    "device_token": device_token,
                },
                message="Connexion réussie.",
            )

        # ── Cas 2 : Appareil de confiance ──────────────────────────────────────
        token_str = _get_device_token(request)
        device    = _find_device(token_str, user)

        if device:
            _update_device(device, request)
            logger.info("✅ Connexion directe (appareil connu) : %s", clean)
            return success_response(
                data={
                    "user":         UserSerializer(user).data,
                    "tokens":       _get_tokens(user),
                    "device_token": str(device.device_token),
                },
                message="Connexion réussie.",
            )

        # ── Cas 3 : OTP ────────────────────────────────────────────────────────
        return self._send_otp(clean)

    def _send_otp(self, phone: str):
        from notifications.tasks import send_otp_sms
        # Supprimer tous les anciens OTP non verifies pour ce numero
        OTPRecord.objects.filter(phone=phone, verified=False).delete()
        result = send_otp_sms(phone)
        if not result.get("success"):
            return error_response(
                "Impossible d'envoyer le SMS. Vérifiez votre numéro.",
                status=503,
            )
        OTPRecord.objects.create(
            phone          = phone,
            verificationid = result.get("verificationid", ""),
            expires_at     = timezone.now() + timedelta(minutes=5),
        )
        logger.info("OTP envoyé : %s", phone)
        return success_response(
            data={"otp_sent": True, "phone": phone},
            message=f"Code envoyé au {phone}. Valable 5 minutes.",
        )


# ─── POST /auth/login/verify/ ────────────────────────────────────────────────
class LoginVerifyView(APIView):
    """
    Vérifie l'OTP.
    Crée le compte si inexistant.
    Enregistre l'appareil → device_token retourné au frontend.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "").strip()
        code  = request.data.get("code",  "").strip()

        if not phone or not code:
            return error_response("Numéro et code requis.", status=400)

        clean = _normalize_phone(phone)

        record = OTPRecord.objects.filter(
            phone=clean, verified=False
        ).order_by("-sent_at").first()

        if not record:
            return error_response(
                "Aucun code OTP actif. Demandez un nouveau code.", status=400)
        if timezone.now() > record.expires_at:
            return error_response(
                "Le code OTP a expiré. Demandez un nouveau code.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code incorrect ou expiré. Vérifiez votre SMS.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        # Connexion seulement - pas de creation de compte ici
        try:
            user = User.objects.get(phone=clean)
            logger.info("Connexion OTP reussie : %s", clean)
        except User.DoesNotExist:
            # Compte inexistant -> erreur claire
            return error_response(
                "Aucun compte trouve avec ce numero. Veuillez vous inscrire d'abord.",
                status=404,
                errors={"code": "account_not_found"}
            )

        # Enregistrer l'appareil → prochain login sans OTP
        device_token = _register_device(request, user)

        return success_response(
            data={
                "user":         UserSerializer(user).data,
                "tokens":       _get_tokens(user),
                "device_token": device_token,
                "is_new":       False,
            },
            message="Connexion réussie.",
        )


# ─── POST /auth/otp/send/ ─────────────────────────────────────────────────────
class OTPSendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = OTPSendSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]
        from notifications.tasks import send_otp_sms
        result = send_otp_sms(phone)
        if not result.get("success"):
            return error_response("Impossible d'envoyer le SMS.", status=503)
        # Supprimer les anciens OTP non verifies
        OTPRecord.objects.filter(phone=phone, verified=False).delete()
        OTPRecord.objects.create(
            phone=phone, verificationid=result["verificationid"],
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        return success_response(message=f"Code envoye au {phone}.")


# ─── POST /auth/otp/verify/ ───────────────────────────────────────────────────
class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return LoginVerifyView().post(request)


# ─── GET + PATCH /auth/me/ ────────────────────────────────────────────────────
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        s = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success_response(data=UserSerializer(request.user).data,
                                message="Profil mis à jour.")


# ─── POST /auth/avatar/ ───────────────────────────────────────────────────────
class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        from django.conf import settings
        file = request.FILES.get("avatar")
        if not file:
            return error_response("Aucun fichier fourni.")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if getattr(settings, "USE_CLOUDINARY", False):
            from core.cloudinary_utils import upload_avatar
            result = upload_avatar(file)
            if not result.get("url"):
                return error_response("Erreur upload.", status=500)
            profile.avatar = result["url"]
        else:
            profile.avatar = file
        profile.save(update_fields=["avatar"])
        return success_response(data=UserSerializer(request.user).data,
                                message="Photo mise à jour.")


# ─── Wallet ───────────────────────────────────────────────────────────────────
class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Exception:
            profile, _ = Profile.objects.get_or_create(user=request.user)
        from .serializers import PointTransactionSerializer
        transactions = PointTransaction.objects.filter(
            user=request.user).order_by("-created_at")[:50]
        return success_response(data={
            "points":        profile.points or 0,
            "points_in_gnf": profile.points_in_gnf,
            "transactions":  PointTransactionSerializer(transactions, many=True).data,
        })


# ─── Points ───────────────────────────────────────────────────────────────────
class PointsAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)
        try:
            points = int(request.data.get("points", 0))
        except (TypeError, ValueError):
            return error_response("Points invalides.", status=400)
        if points <= 0:
            return error_response("Points invalides.", status=400)
        user_id = request.data.get("user_id") or str(request.user.id)
        try:
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                profile, _ = Profile.objects.select_for_update().get_or_create(user=user)
                profile.points = (profile.points or 0) + points
                profile.save(update_fields=["points"])
                PointTransaction.objects.create(
                    user=user, type=PointTransaction.Type.CREDIT,
                    source=PointTransaction.Source.ADMIN, points=points,
                    balance_after=profile.points,
                    description=request.data.get("description", "Ajustement administrateur")[:255],
                )
            return success_response(
                data={"user_id": str(user.id), "points": profile.points, "added": points},
                message=f"+{points} points !")
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable.", status=404)
        except Exception as e:
            logger.exception("Ajustement de points impossible")
            return error_response("Impossible d'ajuster les points.", status=500)


# ─── Appareils ────────────────────────────────────────────────────────────────
class DeviceResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "").strip()
        code  = request.data.get("code",  "").strip()
        if not phone:
            return error_response("Numéro requis.", status=400)
        clean = _normalize_phone(phone)
        if not code:
            from notifications.tasks import send_otp_sms
            result = send_otp_sms(clean)
            if not result.get("success"):
                return error_response("Impossible d'envoyer le SMS.", status=503)
            OTPRecord.objects.create(phone=clean,
                verificationid=result["verificationid"],
                expires_at=timezone.now() + timedelta(minutes=5))
            return success_response(message=f"Code envoyé au {clean}.")
        record = OTPRecord.objects.filter(
            phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code expiré. Recommencez.", status=400)
        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code incorrect.", status=400)
        record.verified = True; record.save(update_fields=["verified"])
        try:
            user = User.objects.get(phone=clean)
            UserDevice.objects.filter(user=user).delete()
        except User.DoesNotExist:
            pass
        return success_response(
            message="Appareil réinitialisé. Reconnectez-vous pour enregistrer votre nouvel appareil.")


class DeviceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        devices = UserDevice.objects.select_related("user").order_by("-last_used")
        return success_response(data=[{
            "id": str(d.id), "user_phone": d.user.phone,
            "last_ip": d.last_ip, "last_used": d.last_used,
        } for d in devices])

    def delete(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        user_id = request.data.get("user_id")
        if not user_id:
            return error_response("user_id requis.", status=400)
        try:
            user = User.objects.get(id=user_id)
            UserDevice.objects.filter(user=user).delete()
            return success_response(message=f"Appareil de {user.phone} révoqué.")
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable.", status=404)


# ─── Admin utilisateurs ───────────────────────────────────────────────────────
class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        users = User.objects.select_related("profile").all().order_by("-date_joined")
        return success_response(data=UserSerializer(users, many=True).data)

    def post(self, request):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        phone = request.data.get("phone", "").strip()
        role  = request.data.get("role", "STUDENT").upper()
        if not phone:
            return error_response("Numéro obligatoire.", status=400)
        if role not in User.Role.values:
            return error_response("Rôle invalide.", status=400)
        if not phone.startswith("+"): phone = "+" + phone
        if User.objects.filter(phone=phone).exists():
            return error_response("Compte déjà existant.", status=400)
        user = User.objects.create_user(phone=phone, role=role)
        user.is_active = request.data.get("is_active", True); user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.first_name = request.data.get("first_name", "")
        profile.last_name = request.data.get("last_name", "")
        profile.city = request.data.get("city", "")
        profile.school_level = request.data.get("school_level", "")
        profile.onboarding_completed = True
        profile.save(update_fields=[
            "first_name", "last_name", "city", "school_level", "onboarding_completed"
        ])
        return success_response(data=UserSerializer(user).data,
                                message="Utilisateur créé.", status=201)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, uid):
        try: return User.objects.select_related("profile").get(id=uid)
        except User.DoesNotExist: return None

    def patch(self, request, user_id):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        user = self._get(user_id)
        if not user: return error_response("Introuvable.", status=404)
        if "role" in request.data:
            role = str(request.data["role"]).upper()
            if role not in User.Role.values:
                return error_response("Rôle invalide.", status=400)
            user.role = role
        if "is_active" in request.data: user.is_active = request.data["is_active"]
        user.save(update_fields=["role","is_active"])
        profile, _ = Profile.objects.get_or_create(user=user)
        for f in ["first_name","last_name","city","school_level","bio"]:
            if f in request.data: setattr(profile, f, request.data[f])
        profile.save()
        return success_response(data=UserSerializer(user).data, message="Mis à jour.")

    def delete(self, request, user_id):
        if not _is_admin(request):
            return error_response("Accès réservé.", status=403)
        user = self._get(user_id)
        if not user: return error_response("Introuvable.", status=404)
        if user.is_superuser:
            return error_response("Impossible de supprimer le superadmin.", status=403)
        phone = user.phone; user.delete()
        return success_response(message=f"Utilisateur {phone} supprimé.")


# ══════════════════════════════════════════════════════════════════════════════
# INSCRIPTION PAR ROLE
# ══════════════════════════════════════════════════════════════════════════════

def _create_user_with_profile(phone, password, role, extra=None):
    """Crée un utilisateur + profil selon le rôle."""
    with transaction.atomic():
        user = User.objects.create_user(phone=phone, role=role)
        user.set_password(password)
        user.save(update_fields=["password"])
        profile, _ = Profile.objects.get_or_create(user=user)
        for field, value in (extra or {}).items():
            setattr(profile, field, value)
        profile.onboarding_completed = False
        profile.points = 0
        profile.save()
        # Le signal post_save peut avoir mis en cache une ancienne instance du
        # profil sur ``user``. Garder le cache relationnel cohérent pour que la
        # réponse d'inscription contienne immédiatement les valeurs enregistrées.
        user.profile = profile
        return user


# ─── POST /auth/register/eleve/ ───────────────────────────────────────────────
class RegisterEleveView(APIView):
    """Inscription Élève : OTP → mot de passe → niveau/serie"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone    = request.data.get("phone",    "").strip()
        code     = request.data.get("code",     "").strip()
        password = request.data.get("password", "").strip()
        niveau   = request.data.get("niveau",   "").strip()   # Terminale, 3eme, 6eme...
        serie    = request.data.get("serie",    "").strip()   # SM, SS, SE

        if not all([phone, code, password]):
            return error_response("Numero, code OTP et mot de passe requis.", status=400)
        if len(password) < 6:
            return error_response("Mot de passe : minimum 6 caracteres.", status=400)

        clean = _normalize_phone(phone)
        if User.objects.filter(phone=clean).exists():
            return error_response("Ce numero est deja inscrit. Connectez-vous.", status=400)

        record = OTPRecord.objects.filter(phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expire.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        user = _create_user_with_profile(clean, password, "STUDENT", {
            "niveau": niveau, "serie": serie,
        })
        device_token = _register_device(request, user)
        logger.info("Inscription eleve : %s", clean)

        return success_response(
            data={"user": UserSerializer(user).data, "tokens": _get_tokens(user),
                  "device_token": device_token, "is_new": True},
            message="Bienvenue sur Kharandi !",
            status=201,
        )


# ─── POST /auth/register/parent/ ──────────────────────────────────────────────
class RegisterParentView(APIView):
    """Inscription Parent : OTP → mot de passe → lien avec enfant(s)"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone         = request.data.get("phone",         "").strip()
        code          = request.data.get("code",          "").strip()
        password      = request.data.get("password",      "").strip()
        child_phone   = request.data.get("child_phone",   "").strip()

        if not all([phone, code, password]):
            return error_response("Numero, code OTP et mot de passe requis.", status=400)
        if len(password) < 6:
            return error_response("Mot de passe : minimum 6 caracteres.", status=400)

        clean = _normalize_phone(phone)
        if User.objects.filter(phone=clean).exists():
            return error_response("Ce numero est deja inscrit. Connectez-vous.", status=400)

        record = OTPRecord.objects.filter(phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expire.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        # Trouver l'enfant si son numero est fourni
        child_user = None
        if child_phone:
            clean_child = _normalize_phone(child_phone)
            child_user = User.objects.filter(phone=clean_child, role="STUDENT").first()

        user = _create_user_with_profile(clean, password, "PARENT")
        if child_user:
            try:
                child_user.profile.parent = user
                child_user.profile.save(update_fields=["parent"])
            except Exception:
                pass

        device_token = _register_device(request, user)
        logger.info("Inscription parent : %s", clean)

        return success_response(
            data={"user": UserSerializer(user).data, "tokens": _get_tokens(user),
                  "device_token": device_token, "is_new": True,
                  "child_linked": child_user is not None},
            message="Bienvenue sur Kharandi !",
            status=201,
        )


# ─── POST /auth/register/repetiteur/ ─────────────────────────────────────────
class RegisterRepetiteurView(APIView):
    """
    Inscription Répétiteur : OTP → mot de passe → infos pro → validation manuelle
    Statut initial : PENDING (en attente de validation par l'admin Kharandi)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone     = request.data.get("phone",     "").strip()
        code      = request.data.get("code",      "").strip()
        password  = request.data.get("password",  "").strip()
        nom       = request.data.get("nom",        "").strip()
        matieres  = request.data.get("matieres",  [])   # liste de matieres
        niveaux   = request.data.get("niveaux",   [])   # liste de niveaux
        zone      = request.data.get("zone",       "").strip()  # quartier/ville

        if not all([phone, code, password, nom]):
            return error_response("Numero, code, mot de passe et nom requis.", status=400)
        if len(password) < 6:
            return error_response("Mot de passe : minimum 6 caracteres.", status=400)

        clean = _normalize_phone(phone)
        if User.objects.filter(phone=clean).exists():
            return error_response("Ce numero est deja inscrit. Connectez-vous.", status=400)

        record = OTPRecord.objects.filter(phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expire.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        user = _create_user_with_profile(clean, password, "TUTOR", {
            "display_name": nom,
            "tutor_status": "PENDING",  # En attente validation
            "tutor_subjects": matieres if isinstance(matieres, list) else [matieres],
            "tutor_levels":   niveaux  if isinstance(niveaux, list)  else [niveaux],
            "tutor_zone":     zone,
        })
        device_token = _register_device(request, user)
        logger.info("Inscription repetiteur (PENDING) : %s", clean)

        return success_response(
            data={"user": UserSerializer(user).data, "tokens": _get_tokens(user),
                  "device_token": device_token, "is_new": True,
                  "validation_status": "pending"},
            message="Votre profil de repetiteur est en cours de validation. Vous serez notifie par SMS.",
            status=201,
        )


# ─── POST /auth/register/vendeur/ ────────────────────────────────────────────
class RegisterVendeurView(APIView):
    """Inscription Vendeur Makiti : OTP → mot de passe → infos boutique"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone          = request.data.get("phone",          "").strip()
        code           = request.data.get("code",           "").strip()
        password       = request.data.get("password",       "").strip()
        nom_boutique   = request.data.get("nom_boutique",   "").strip()
        description    = request.data.get("description",    "").strip()
        zone_livraison = request.data.get("zone_livraison", "").strip()

        if not all([phone, code, password, nom_boutique]):
            return error_response("Numero, code, mot de passe et nom boutique requis.", status=400)
        if len(password) < 6:
            return error_response("Mot de passe : minimum 6 caracteres.", status=400)

        clean = _normalize_phone(phone)
        if User.objects.filter(phone=clean).exists():
            return error_response("Ce numero est deja inscrit. Connectez-vous.", status=400)

        record = OTPRecord.objects.filter(phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expire.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        user = _create_user_with_profile(clean, password, "VENDOR", {
            "shop_name":        nom_boutique,
            "shop_description": description,
            "delivery_zone":    zone_livraison,
            "shop_status":      "ACTIVE",
        })
        device_token = _register_device(request, user)
        logger.info("Inscription vendeur Makiti : %s [%s]", clean, nom_boutique)

        return success_response(
            data={"user": UserSerializer(user).data, "tokens": _get_tokens(user),
                  "device_token": device_token, "is_new": True},
            message=f"Boutique '{nom_boutique}' creee ! Bienvenue sur Kharandi Makiti.",
            status=201,
        )


# ─── POST /auth/register/otp/send/ ───────────────────────────────────────────
class RegisterOTPSendView(APIView):
    """
    Envoie un OTP pour l'inscription (vérifie que le numéro n'est pas déjà utilisé).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "").strip()
        if not phone:
            return error_response("Numero requis.", status=400)

        clean = _normalize_phone(phone)

        # Vérifier si compte déjà existant
        if User.objects.filter(phone=clean).exists():
            return error_response(
                "Ce numero est deja inscrit sur Kharandi. Connectez-vous.",
                status=400,
                errors={"code": "already_registered"}
            )

        # Supprimer anciens OTP et envoyer un nouveau
        OTPRecord.objects.filter(phone=clean, verified=False).delete()

        from notifications.tasks import send_otp_sms
        result = send_otp_sms(clean)
        if not result or not result.get("success"):
            return error_response("Impossible d envoyer le SMS. Reessayez.", status=503)

        OTPRecord.objects.create(
            phone=clean,
            verificationid=result["verificationid"],
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        return success_response(
            data={"otp_sent": True, "phone": clean},
            message=f"Code d inscription envoye au {phone}. Valable 10 minutes.",
        )


# ─── POST /auth/login/password/ ───────────────────────────────────────────────
class LoginWithPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = _normalize_phone(request.data.get("phone", "").strip())
        password = request.data.get("password", "")
        if not phone or not password:
            return error_response("Numéro et mot de passe requis.", status=400)
        try:
            user = User.objects.select_related("profile").get(phone=phone, is_active=True)
        except User.DoesNotExist:
            return error_response("Identifiants incorrects.", status=401)
        if not user.check_password(password):
            return error_response("Identifiants incorrects.", status=401)

        device_token = _register_device(request, user)
        return success_response(
            data={
                "user": UserSerializer(user).data,
                "tokens": _get_tokens(user),
                "device_token": device_token,
            },
            message="Connexion réussie.",
        )


# ─── Mot de passe oublié ──────────────────────────────────────────────────────
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = _normalize_phone(request.data.get("phone", "").strip())
        if not phone:
            return error_response("Numéro requis.", status=400)

        # Réponse volontairement générique pour ne pas révéler les comptes existants.
        if User.objects.filter(phone=phone, is_active=True).exists():
            from notifications.tasks import send_otp_sms
            OTPRecord.objects.filter(phone=phone, verified=False).delete()
            result = send_otp_sms(phone)
            if result.get("success"):
                OTPRecord.objects.create(
                    phone=phone,
                    verificationid=result.get("verificationid", ""),
                    expires_at=timezone.now() + timedelta(minutes=5),
                )
        return success_response(
            message="Si ce numéro est enregistré, un code de réinitialisation a été envoyé."
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = _normalize_phone(request.data.get("phone", "").strip())
        code = request.data.get("code", "").strip()
        password = request.data.get("password", "")
        if not phone or not code or not password:
            return error_response("Numéro, code et nouveau mot de passe requis.", status=400)
        if len(password) < 8:
            return error_response("Le mot de passe doit contenir au moins 8 caractères.", status=400)

        record = OTPRecord.objects.filter(
            phone=phone, verified=False, expires_at__gt=timezone.now()
        ).order_by("-sent_at").first()
        if not record:
            return error_response("Code invalide ou expiré.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=phone):
            return error_response("Code invalide ou expiré.", status=400)

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(phone=phone, is_active=True)
                user.set_password(password)
                user.save(update_fields=["password"])
                UserDevice.objects.filter(user=user).delete()
                record.verified = True
                record.save(update_fields=["verified"])
        except User.DoesNotExist:
            return error_response("Code invalide ou expiré.", status=400)

        return success_response(message="Mot de passe modifié. Reconnectez-vous.")


# ══════════════════════════════════════════════════════════════════════════════
# INSCRIPTION GENERIQUE  —  POST /api/v1/auth/register/
# Utilisee par le frontend Kharandi (Login.tsx) : { phone, code, password, role? }
# ══════════════════════════════════════════════════════════════════════════════
class RegisterView(APIView):
    """Inscription universelle.

    Body : phone, code (OTP), password, role (optionnel : STUDENT | PARENT |
    TUTOR | SELLER), + champs de profil optionnels (first_name, last_name,
    niveau, serie, city, shop_name...).

    Reponse : { user, tokens, device_token, is_new }
    """
    permission_classes = [AllowAny]

    ROLE_ALIASES = {
        "": "STUDENT", "eleve": "STUDENT", "élève": "STUDENT", "etudiant": "STUDENT",
        "student": "STUDENT", "parent": "PARENT", "repetiteur": "TUTOR",
        "répétiteur": "TUTOR", "tutor": "TUTOR", "vendeur": "SELLER",
        "seller": "SELLER", "admin": "STUDENT",  # jamais d'auto-promotion admin
    }

    PROFILE_FIELDS = (
        "first_name", "last_name", "city", "niveau", "serie",
        "school_level", "bio", "shop_name", "shop_description",
    )

    def post(self, request):
        phone    = str(request.data.get("phone", "")).strip()
        code     = str(request.data.get("code", "")).strip()
        password = str(request.data.get("password", "")).strip()
        raw_role = str(request.data.get("role", "")).strip()

        if not all([phone, code, password]):
            return error_response("Numero, code OTP et mot de passe requis.", status=400)
        if len(password) < 6:
            return error_response("Mot de passe : minimum 6 caracteres.", status=400)

        role = self.ROLE_ALIASES.get(raw_role.lower(), raw_role.upper() or "STUDENT")
        valid_roles = {c[0] for c in getattr(User, "Role", None).choices} \
            if hasattr(User, "Role") else {"STUDENT", "PARENT", "TUTOR", "SELLER"}
        if role not in valid_roles:
            role = "STUDENT"

        clean = _normalize_phone(phone)
        if User.objects.filter(phone=clean).exists():
            return error_response("Ce numero est deja inscrit. Connectez-vous.", status=400)

        record = OTPRecord.objects.filter(phone=clean, verified=False).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expire.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        record.verified = True
        record.save(update_fields=["verified"])

        extra = {}
        for field in self.PROFILE_FIELDS:
            value = request.data.get(field)
            if value not in (None, ""):
                if hasattr(Profile, field) or field in [f.name for f in Profile._meta.get_fields()]:
                    extra[field] = value

        try:
            user = _create_user_with_profile(clean, password, role, extra)
        except Exception:
            logger.exception("Inscription generique impossible pour %s", clean)
            return error_response("Inscription impossible. Reessayez.", status=500)

        device_token = _register_device(request, user)
        logger.info("Inscription generique : %s (%s)", clean, role)

        return success_response(
            data={
                "user":         UserSerializer(user).data,
                "tokens":       _get_tokens(user),
                "device_token": device_token,
                "is_new":       True,
            },
            message="Bienvenue sur Kharandi !",
            status=201,
        )


# ══════════════════════════════════════════════════════════════════════════════
# WALLET LIBRE-SERVICE  —  POST/GET /api/v1/users/me/points/
# Utilise par Exercises.tsx (gain) et Marketplace.tsx (depense, points negatifs)
# ══════════════════════════════════════════════════════════════════════════════
class MyPointsView(APIView):
    """Solde et mouvement de points de l'utilisateur connecte.

    GET  -> { points, history: [...] }
    POST -> { points: <int> }  (positif = credit, negatif = debit)
    """
    permission_classes = [IsAuthenticated]

    MAX_CREDIT_PER_CALL = 100   # garde-fou anti-triche

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        history = PointTransaction.objects.filter(user=request.user)[:50]
        return success_response(data={
            "points": profile.points or 0,
            "history": [
                {
                    "id":            str(t.id),
                    "type":          t.type,
                    "source":        t.source,
                    "points":        t.points,
                    "balance_after": t.balance_after,
                    "description":   t.description,
                    "created_at":    t.created_at.isoformat(),
                }
                for t in history
            ],
        })

    def post(self, request):
        try:
            delta = int(request.data.get("points", 0))
        except (TypeError, ValueError):
            return error_response("Points invalides.", status=400)

        if delta == 0:
            return error_response("Points invalides.", status=400)
        if delta > self.MAX_CREDIT_PER_CALL:
            return error_response(
                f"Maximum {self.MAX_CREDIT_PER_CALL} points par operation.", status=400)

        raw_source  = str(request.data.get("source", "")).strip().upper()
        allowed_src = {"EXERCISE", "MARKETPLACE", "BONUS"}
        if raw_source not in allowed_src:
            raw_source = "EXERCISE" if delta > 0 else "MARKETPLACE"

        description = str(request.data.get("description", "")).strip()[:255] or (
            "Points gagnes" if delta > 0 else "Points depenses")

        try:
            with transaction.atomic():
                profile, _ = Profile.objects.select_for_update().get_or_create(user=request.user)
                current = profile.points or 0

                if delta < 0 and current < abs(delta):
                    return error_response(
                        f"Points insuffisants. Solde : {current} pts.", status=400)

                profile.points = current + delta
                profile.save(update_fields=["points"])

                PointTransaction.objects.create(
                    user          = request.user,
                    type          = PointTransaction.Type.CREDIT if delta > 0
                                    else PointTransaction.Type.DEBIT,
                    source        = raw_source,
                    points        = abs(delta),
                    balance_after = profile.points,
                    description   = description,
                    reference     = str(request.data.get("reference", ""))[:100],
                )
        except Exception:
            logger.exception("Mouvement de points impossible pour %s", request.user.phone)
            return error_response("Impossible de mettre a jour vos points.", status=500)

        return success_response(
            data={"points": profile.points, "delta": delta},
            message=(f"+{delta} points !" if delta > 0 else f"{delta} points."),
        )
