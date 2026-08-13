"""
core/authentication.py
───────────────────────
Firebase JWT Authentication pour Django REST Framework.

Flux :
  1. React récupère un idToken Firebase après login.
  2. React envoie  Authorization: Bearer <idToken>  à l'API Django.
  3. Ce backend vérifie le token via firebase-admin SDK.
  4. Si valide, on récupère ou crée le User Django correspondant.
"""
import logging

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth, credentials
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


# ─── Initialisation Firebase (singleton) ──────────────────────────────────────
def _init_firebase():
    if not firebase_admin._apps:
        cred_path = getattr(settings, "FIREBASE_CREDENTIALS_JSON_PATH", None)
        if cred_path:
            cred = credentials.Certificate(cred_path)
        else:
            # Fallback : application default credentials (Cloud Run / GCP)
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)


_init_firebase()


# ─── DRF Authentication Class ─────────────────────────────────────────────────
class FirebaseAuthentication(BaseAuthentication):
    """
    Authentification via le token Firebase ID.
    Renvoie (user, firebase_uid) si valide, None si pas de Bearer token.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None  # Pas de token → laisse passer aux autres backends

        id_token = auth_header.split(" ", 1)[1].strip()
        if not id_token:
            return None

        try:
            decoded = firebase_auth.verify_id_token(id_token)
        except firebase_auth.ExpiredIdTokenError:
            raise AuthenticationFailed("Token Firebase expiré.")
        except firebase_auth.InvalidIdTokenError:
            raise AuthenticationFailed("Token Firebase invalide.")
        except Exception as exc:
            logger.error("Firebase verify error: %s", exc)
            raise AuthenticationFailed("Erreur de vérification du token.")

        uid = decoded["uid"]
        user = self._get_or_create_user(uid, decoded)
        return (user, uid)

    # ------------------------------------------------------------------
    def _get_or_create_user(self, uid: str, decoded: dict):
        from users.models import User  # Import tardif pour éviter les imports circulaires

        user, created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={
                "email":      decoded.get("email", ""),
                "phone":      decoded.get("phone_number", ""),
                "is_active":  True,
            },
        )

        if created:
            logger.info("Nouvel utilisateur Firebase créé : %s", uid)

        return user

    def authenticate_header(self, request):
        return self.keyword


# ─── Django Auth Backend (pour admin & session) ────────────────────────────────
class FirebaseAuthBackend:
    """Backend Django classique — utilisé uniquement pour l'admin Django."""

    def authenticate(self, request, firebase_uid=None, **kwargs):
        if not firebase_uid:
            return None
        from users.models import User
        return User.objects.filter(firebase_uid=firebase_uid).first()

    def get_user(self, user_id):
        from users.models import User
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
