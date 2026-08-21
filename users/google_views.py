"""
users/google_views.py — Connexion Google, pilotée EXCLUSIVEMENT par Django
═════════════════════════════════════════════════════════════════════════

Django reste le seul responsable de l'identité utilisateur. Le frontend ne fait
que trois choses : afficher un bouton, ouvrir `…/auth/google/login/`, puis
échanger un code opaque contre l'authentification Kharandi habituelle.

Flux complet
────────────
    Frontend → GET  /api/v1/auth/google/login/?platform=web|mobile
             ← 302 vers Google (state + nonce + PKCE S256)
    Google   → GET  /api/v1/auth/google/callback/?code=…&state=…
             ← 302 vers le frontend avec un ticket opaque à usage unique
    Frontend → POST /api/v1/auth/google/exchange/   {code}
             ← soit l'authentification Kharandi standard
               {user, tokens:{access,refresh}, device_token}
               soit {status:"signup_required", google:{…}} si aucun compte
                    Kharandi n'est encore rattaché à cette identité Google.
    Frontend → POST /api/v1/auth/google/complete/   {code, phone, code_otp, role…}
             ← authentification Kharandi standard, après vérification OTP du
               téléphone et choix explicite du rôle.
    Frontend → POST /api/v1/auth/google/link/       {code}   (JWT requis)
             ← liaison Google d'un compte déjà connecté.

Règles de sécurité appliquées
─────────────────────────────
  - aucune identité n'est déduite d'un email transmis par le frontend ;
  - le rapprochement de comptes se fait sur `google_sub`, jamais sur l'email,
    et la liaison exige TOUJOURS une preuve de possession : soit un JWT
    Kharandi valide, soit un OTP vérifié sur le numéro de téléphone ;
  - aucun JWT ne circule dans une URL de redirection ni dans un deep link :
    seul un code opaque à usage unique y transite ;
  - un rôle privilégié n'est jamais attribué par Google : ADMIN est refusé et
    le rôle reste choisi explicitement, comme dans l'inscription actuelle ;
  - une connexion Google ne modifie jamais le rôle, le Profile, l'abonnement,
    les commandes, les transactions ni les données pédagogiques existantes.
"""
from __future__ import annotations

import logging
import secrets as secrets_std
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.utils import error_response, success_response

from . import google_oauth as goauth
from .models import GoogleAccount, GoogleAuthTicket, GoogleOAuthState, OTPRecord, User
from .serializers import UserSerializer
from .views import (
    _create_user_with_profile, _get_tokens, _normalize_phone, _register_device,
)

logger = logging.getLogger(__name__)

# Rôles qu'un utilisateur peut choisir lui-même — strictement les mêmes que
# ceux des endpoints d'inscription existants. ADMIN en est volontairement exclu.
ROLES_AUTORISES = ("STUDENT", "TUTOR", "PARENT", "VENDOR")

MESSAGES_ERREUR = {
    "not_configured": "La connexion Google n'est pas configurée sur ce serveur.",
    "invalid_state": "Requête Google invalide ou expirée. Recommencez la connexion.",
    "invalid_identity": "Identité Google invalide.",
    "email_not_verified": "Cette adresse Google n'est pas vérifiée. "
                          "Vérifiez-la auprès de Google puis réessayez.",
    "google_unreachable": "Google est momentanément injoignable. Réessayez.",
    "token_exchange_failed": "Échec de la vérification auprès de Google.",
    "missing_id_token": "Réponse Google incomplète.",
    "invalid_issuer": "Identité Google invalide.",
    "invalid_nonce": "Identité Google invalide.",
    "account_disabled": "Ce compte est désactivé.",
    "invalid_ticket": "Code de connexion invalide ou expiré. Recommencez.",
}


class RedirectionRetour(HttpResponseRedirect):
    """Redirection de retour vers le frontend, web ou application mobile.

    Django n'autorise par défaut que http/https : le scheme du deep link mobile
    configuré (ex. « kharandi:// ») est ajouté, et lui seul. Les cibles restent
    celles de la liste blanche des réglages — jamais une valeur de la requête.
    """

    @property
    def allowed_schemes(self):
        schemes = ["http", "https"]
        cible = getattr(settings, "GOOGLE_POST_LOGIN_MOBILE_URL", "") or ""
        if "://" in cible:
            schemes.append(cible.split("://", 1)[0].lower())
        return schemes


def _message(code_erreur: str) -> str:
    return MESSAGES_ERREUR.get(code_erreur, "Échec de la connexion Google.")


def _reponse_auth(request, user, *, message, status=200, extra=None):
    """Réponse d'authentification IDENTIQUE à celle du login Kharandi actuel.

    Aucun second système de jetons : on réutilise `_get_tokens` (simplejwt) et
    `_register_device`, exactement comme `LoginView` et les vues d'inscription.
    """
    device_token = _register_device(request, user)
    donnees = {
        "user": UserSerializer(user).data,
        "tokens": _get_tokens(user),
        "device_token": device_token,
    }
    donnees.update(extra or {})
    return success_response(data=donnees, message=message, status=status)


def _creer_ticket(identite: dict, *, kind: str, user=None) -> str:
    """Crée un ticket opaque et retourne le code en clair (jamais stocké)."""
    if kind == GoogleAuthTicket.Kind.LOGIN:
        duree = settings.GOOGLE_OAUTH_LOGIN_TICKET_TTL
    else:
        duree = settings.GOOGLE_OAUTH_SIGNUP_TICKET_TTL
    code = goauth.nouveau_secret_url()
    GoogleAuthTicket.objects.create(
        code_hash=goauth.hacher_code(code),
        kind=kind,
        user=user,
        google_sub=identite["sub"],
        email=identite.get("email", ""),
        email_verified=identite.get("email_verified", False),
        given_name=identite.get("given_name", ""),
        family_name=identite.get("family_name", ""),
        expires_at=timezone.now() + timedelta(seconds=duree),
    )
    return code


def _lire_ticket(code: str, *, kind=None) -> GoogleAuthTicket | None:
    if not code:
        return None
    ticket = GoogleAuthTicket.objects.filter(
        code_hash=goauth.hacher_code(code)
    ).select_related("user").first()
    if ticket is None or not ticket.est_utilisable():
        return None
    if kind is not None and ticket.kind != kind:
        return None
    return ticket


def _lier_compte(user, identite: dict) -> GoogleAccount:
    """Attache une identité Google à un User existant, sans rien écraser.

    Seule la table `GoogleAccount` est écrite : ni le rôle, ni le Profile, ni
    l'abonnement, ni aucune donnée métier n'est touché.
    """
    compte, _ = GoogleAccount.objects.update_or_create(
        google_sub=identite["sub"],
        defaults={
            "user": user,
            "email": identite.get("email", ""),
            "email_verified": identite.get("email_verified", False),
            "given_name": identite.get("given_name", ""),
            "family_name": identite.get("family_name", ""),
            "last_used_at": timezone.now(),
        },
    )
    return compte


def _purger_expires():
    """Nettoyage opportuniste des états et tickets périmés (borné, sans tâche)."""
    limite = timezone.now() - timedelta(days=1)
    GoogleOAuthState.objects.filter(expires_at__lt=limite).delete()
    GoogleAuthTicket.objects.filter(expires_at__lt=limite).delete()


# ─── GET /auth/google/login/ ───────────────────────────────────────────────────
class GoogleLoginStartView(APIView):
    """Démarre le flux OAuth. Redirige vers Google (302).

    `?format=json` renvoie l'URL au lieu de rediriger : utile pour une
    application mobile qui ouvre elle-même un navigateur système.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        if not goauth.est_configure():
            return error_response(_message("not_configured"), status=503,
                                  errors={"code": "not_configured"})

        platform = request.query_params.get("platform", "web").strip().lower()
        if platform not in goauth.plateformes_disponibles():
            platform = "web"

        state = goauth.nouveau_secret_url()
        nonce = goauth.nouveau_secret_url()
        verifier = goauth.nouveau_code_verifier()

        GoogleOAuthState.objects.create(
            state=state, nonce=nonce, code_verifier=verifier, platform=platform,
            expires_at=timezone.now() + timedelta(seconds=settings.GOOGLE_OAUTH_STATE_TTL),
        )
        _purger_expires()

        url = goauth.url_autorisation(state=state, nonce=nonce, verifier=verifier)
        if request.query_params.get("format") == "json":
            return success_response(data={"authorization_url": url},
                                    message="Ouvrez cette URL pour continuer avec Google.")
        return HttpResponseRedirect(url)


# ─── GET /auth/google/callback/ ───────────────────────────────────────────────
class GoogleCallbackView(APIView):
    """Callback appelé par Google. Vérifie tout, puis redirige le frontend.

    Rien d'exploitable ne transite dans l'URL de retour : uniquement un code
    opaque à usage unique et un statut.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        state_recu = request.query_params.get("state", "")
        etat = GoogleOAuthState.objects.filter(state=state_recu).first()

        # Le `state` détermine la cible de redirection : si l'état est
        # inconnu ou périmé, on retombe sur la cible web par défaut.
        platform = etat.platform if etat else "web"

        if request.query_params.get("error"):
            logger.warning("Google OAuth refusé par l'utilisateur : %s",
                           request.query_params.get("error"))
            return self._retour(platform, status="error", reason="access_denied")

        if etat is None or not etat.est_utilisable():
            logger.warning("Google OAuth : state invalide ou déjà consommé.")
            return self._retour(platform, status="error", reason="invalid_state")

        # Consommé immédiatement : un `state` ne sert jamais deux fois.
        etat.consommer()

        code = request.query_params.get("code", "")
        if not code:
            return self._retour(platform, status="error", reason="invalid_state")

        if not goauth.est_configure():
            return self._retour(platform, status="error", reason="not_configured")

        try:
            jetons = goauth.echanger_code(code, etat.code_verifier)
            identite = goauth.verifier_id_token(jetons["id_token"], etat.nonce)
        except goauth.GoogleOAuthError as exc:
            logger.warning("Google OAuth échec (%s) : %s", exc.code, exc)
            return self._retour(platform, status="error", reason=exc.code)

        compte = GoogleAccount.objects.select_related("user").filter(
            google_sub=identite["sub"]
        ).first()

        if compte is not None:
            if not compte.user.is_active:
                return self._retour(platform, status="error", reason="account_disabled")
            ticket = _creer_ticket(identite, kind=GoogleAuthTicket.Kind.LOGIN,
                                   user=compte.user)
            logger.info("Google OAuth : identité reconnue pour %s", compte.user.phone)
            return self._retour(platform, status="authenticated", code=ticket)

        # Identité Google vérifiée mais aucun compte Kharandi rattaché.
        # Aucun compte n'est créé ici : le téléphone (identifiant Kharandi) doit
        # d'abord être vérifié par OTP et le rôle choisi explicitement.
        ticket = _creer_ticket(identite, kind=GoogleAuthTicket.Kind.SIGNUP)
        logger.info("Google OAuth : identité vérifiée, inscription à compléter.")
        return self._retour(platform, status="signup_required", code=ticket)

    def _retour(self, platform, *, status, code=None, reason=None):
        cible = goauth.cible_frontend(platform)
        parametres = {"status": status}
        if code:
            parametres["code"] = code
        if reason:
            parametres["reason"] = reason
        separateur = "&" if "?" in cible else "?"
        return RedirectionRetour(f"{cible}{separateur}{urlencode(parametres)}")


# ─── POST /auth/google/exchange/ ──────────────────────────────────────────────
class GoogleExchangeView(APIView):
    """Échange le code opaque du callback contre l'authentification Kharandi."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        ticket = _lire_ticket(code)
        if ticket is None:
            return error_response(_message("invalid_ticket"), status=400,
                                  errors={"code": "invalid_ticket"})

        if ticket.kind == GoogleAuthTicket.Kind.SIGNUP:
            # Le ticket n'est PAS consommé ici : il ne donne aucun accès et
            # reste nécessaire à l'appel `complete/` ou `link/`.
            return success_response(
                data={
                    "status": "signup_required",
                    "google": {
                        "email": ticket.email,
                        "first_name": ticket.given_name,
                        "last_name": ticket.family_name,
                    },
                    "roles": list(ROLES_AUTORISES),
                    "expires_at": ticket.expires_at,
                },
                message="Compte Google vérifié. Confirmez votre numéro de "
                        "téléphone pour finaliser l'inscription.",
            )

        user = ticket.user
        if user is None:
            return error_response(_message("invalid_ticket"), status=400,
                                  errors={"code": "invalid_ticket"})
        if not user.is_active:
            return error_response(_message("account_disabled"), status=403,
                                  errors={"code": "account_disabled"})

        ticket.consommer()
        compte = getattr(user, "google_account", None)
        if compte is not None:
            compte.marquer_utilise()
        logger.info("Connexion Google réussie : %s", user.phone)
        return _reponse_auth(request, user, message="Connexion réussie.",
                             extra={"is_new": False})


# ─── POST /auth/google/complete/ ──────────────────────────────────────────────
class GoogleCompleteView(APIView):
    """Finalise une connexion Google : téléphone vérifié par OTP + rôle.

    Deux cas, tous deux sûrs :
      - le numéro n'existe pas → création du compte selon les règles actuelles
        (`_create_user_with_profile`), avec le rôle choisi par l'utilisateur ;
      - le numéro existe déjà → AUCUN nouveau compte : l'identité Google est
        simplement liée au compte existant. La double preuve (identité Google
        vérifiée + OTP reçu sur le numéro) rend l'usurpation impossible, et
        rien n'est écrasé : ni rôle, ni Profile, ni abonnement, ni historique.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        phone = str(request.data.get("phone", "")).strip()
        code_otp = str(request.data.get("code_otp") or request.data.get("otp") or "").strip()
        role = str(request.data.get("role", "STUDENT")).strip().upper()
        password = str(request.data.get("password", "")).strip()

        ticket = _lire_ticket(code, kind=GoogleAuthTicket.Kind.SIGNUP)
        if ticket is None:
            return error_response(_message("invalid_ticket"), status=400,
                                  errors={"code": "invalid_ticket"})
        if not phone or not code_otp:
            return error_response("Numéro de téléphone et code OTP requis.", status=400)
        if role not in ROLES_AUTORISES:
            # Google ne peut jamais attribuer un rôle privilégié.
            return error_response("Rôle invalide.", status=400,
                                  errors={"code": "invalid_role",
                                          "roles": list(ROLES_AUTORISES)})
        if password and len(password) < 6:
            return error_response("Mot de passe : minimum 6 caractères.", status=400)

        clean = _normalize_phone(phone)

        # Vérification OTP — exactement le mécanisme existant, sans modification.
        record = OTPRecord.objects.filter(
            phone=clean, verified=False
        ).order_by("-sent_at").first()
        if not record or timezone.now() > record.expires_at:
            return error_response("Code OTP invalide ou expiré.", status=400)

        from notifications.tasks import verify_otp_sms
        if not verify_otp_sms(record.verificationid, code_otp, phone=clean):
            return error_response("Code OTP incorrect.", status=400)

        identite = {
            "sub": ticket.google_sub,
            "email": ticket.email,
            "email_verified": ticket.email_verified,
            "given_name": ticket.given_name,
            "family_name": ticket.family_name,
        }

        # Cette identité Google est-elle déjà rattachée à quelqu'un ?
        deja_lie = GoogleAccount.objects.select_related("user").filter(
            google_sub=ticket.google_sub
        ).first()
        if deja_lie is not None and deja_lie.user.phone != clean:
            return error_response(
                "Ce compte Google est déjà lié à un autre compte Kharandi.",
                status=409, errors={"code": "google_already_linked"},
            )

        existant = User.objects.select_related("profile").filter(phone=clean).first()

        if existant is not None:
            if not existant.is_active:
                return error_response(_message("account_disabled"), status=403,
                                      errors={"code": "account_disabled"})
            autre = GoogleAccount.objects.filter(user=existant).exclude(
                google_sub=ticket.google_sub
            ).first()
            if autre is not None:
                return error_response(
                    "Ce compte Kharandi est déjà lié à un autre compte Google.",
                    status=409, errors={"code": "user_already_linked"},
                )
            record.verified = True
            record.save(update_fields=["verified"])
            ticket.consommer()
            _lier_compte(existant, identite)
            logger.info("Google lié à un compte existant : %s", clean)
            # Aucune donnée métier modifiée : rôle, Profile et historique intacts.
            return _reponse_auth(
                request, existant,
                message="Compte Google lié. Connexion réussie.",
                extra={"is_new": False, "linked": True},
            )

        # ── Création d'un nouveau compte, selon les règles actuelles ──────────
        record.verified = True
        record.save(update_fields=["verified"])

        extra = self._extras_profil(request, role, ticket)
        with transaction.atomic():
            ticket.consommer()
            user = _create_user_with_profile(
                clean, password or secrets_std.token_urlsafe(32), role, extra
            )
            if not password:
                # Pas de mot de passe choisi : aucun secret inconnu mais
                # utilisable ne doit subsister. La connexion reste possible par
                # Google, par OTP, ou après une réinitialisation.
                user.set_unusable_password()
                user.save(update_fields=["password"])
            _lier_compte(user, identite)

        logger.info("Inscription Google (%s) : %s", role, clean)
        return _reponse_auth(
            request, user, message="Bienvenue sur Kharandi !", status=201,
            extra={"is_new": True,
                   **({"validation_status": "pending"} if role == "TUTOR" else {})},
        )

    def _extras_profil(self, request, role, ticket):
        """Champs de Profile, calqués sur les vues d'inscription existantes."""
        donnees = request.data
        extra = {}
        prenom = ticket.given_name
        nom_famille = ticket.family_name
        if prenom:
            extra["first_name"] = prenom
        if nom_famille:
            extra["last_name"] = nom_famille

        if role == "STUDENT":
            extra["niveau"] = str(donnees.get("niveau", "")).strip()
            extra["serie"] = str(donnees.get("serie", "")).strip()
        elif role == "TUTOR":
            nom = str(donnees.get("nom", "")).strip() or " ".join(
                p for p in (prenom, nom_famille) if p
            )
            matieres = donnees.get("matieres", [])
            niveaux = donnees.get("niveaux", [])
            extra.update({
                "display_name": nom,
                # Statut initial identique à l'inscription répétiteur actuelle :
                # validation manuelle par un administrateur Kharandi.
                "tutor_status": "PENDING",
                "tutor_subjects": matieres if isinstance(matieres, list) else [matieres],
                "tutor_levels": niveaux if isinstance(niveaux, list) else [niveaux],
                "tutor_zone": str(donnees.get("zone", "")).strip(),
            })
        elif role == "VENDOR":
            extra.update({
                "shop_name": str(donnees.get("shop_name", "")).strip(),
                "shop_description": str(donnees.get("shop_description", "")).strip(),
                "delivery_zone": str(donnees.get("delivery_zone", "")).strip(),
            })
        return extra


# ─── POST /auth/google/link/ ──────────────────────────────────────────────────
class GoogleLinkView(APIView):
    """Lie un compte Google à l'utilisateur DÉJÀ authentifié (JWT Kharandi).

    C'est le chemin de liaison le plus sûr : la possession du compte Kharandi
    est prouvée par le JWT, celle du compte Google par le flux OAuth complet.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        ticket = _lire_ticket(code)
        if ticket is None:
            return error_response(_message("invalid_ticket"), status=400,
                                  errors={"code": "invalid_ticket"})

        deja_lie = GoogleAccount.objects.select_related("user").filter(
            google_sub=ticket.google_sub
        ).first()
        if deja_lie is not None and deja_lie.user_id != request.user.id:
            return error_response(
                "Ce compte Google est déjà lié à un autre compte Kharandi.",
                status=409, errors={"code": "google_already_linked"},
            )
        autre = GoogleAccount.objects.filter(user=request.user).exclude(
            google_sub=ticket.google_sub
        ).first()
        if autre is not None:
            return error_response(
                "Ce compte Kharandi est déjà lié à un autre compte Google.",
                status=409, errors={"code": "user_already_linked"},
            )

        ticket.consommer()
        compte = _lier_compte(request.user, {
            "sub": ticket.google_sub,
            "email": ticket.email,
            "email_verified": ticket.email_verified,
            "given_name": ticket.given_name,
            "family_name": ticket.family_name,
        })
        logger.info("Compte Google lié à %s", request.user.phone)
        return success_response(
            data={"linked": True, "provider": GoogleAccount.PROVIDER,
                  "email": compte.email, "linked_at": compte.linked_at},
            message="Compte Google lié à votre compte Kharandi.",
        )
