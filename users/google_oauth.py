"""
users/google_oauth.py — Couche technique OAuth 2.0 / OpenID Connect Google
═══════════════════════════════════════════════════════════════════════════

Ce module ne contient AUCUNE logique métier Kharandi : il ne crée pas
d'utilisateur, ne délivre pas de JWT, ne touche ni au rôle ni au Profile.
Il fait uniquement le dialogue avec Google :

  1. construction de l'URL d'autorisation (Authorization Code + PKCE S256) ;
  2. échange du `code` contre les jetons, sur le canal serveur↔serveur
     authentifié par le `client_secret` ;
  3. vérification cryptographique de l'`id_token`.

La vérification de l'id_token est DÉLÉGUÉE à `google-auth`, la bibliothèque
officielle de Google : signature RS256 contre les clés publiques Google
(JWKS, rotation gérée), `aud`, `exp`, `iss`. Aucune primitive cryptographique
n'est réimplémentée ici. Les contrôles supplémentaires propres à notre usage
(`nonce`, `email_verified`, présence du `sub`) sont faits explicitement.

Le `GOOGLE_CLIENT_SECRET` n'est lu que depuis la configuration Django, ne sort
jamais de ce module et n'apparaît dans aucune réponse d'API.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings

# Points d'entrée officiels Google (OpenID Connect Discovery).
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

SCOPES = "openid email profile"
TIMEOUT = 10


class GoogleOAuthError(Exception):
    """Échec du dialogue avec Google ou identité Google non vérifiable.

    Le message reste volontairement générique côté client : les détails ne
    partent que dans les logs serveur.
    """

    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


# ─── Configuration ────────────────────────────────────────────────────────────
def est_configure() -> bool:
    """Vrai si le client OAuth Google est configuré (identifiant + secret)."""
    return bool(
        getattr(settings, "GOOGLE_CLIENT_ID", "")
        and getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    )


def redirect_uri() -> str:
    """URI de callback déclarée chez Google. Valeur de configuration UNIQUEMENT.

    Elle n'est jamais construite à partir de la requête entrante : cela
    interdit par construction toute redirection ouverte via l'en-tête Host.
    """
    return settings.GOOGLE_OAUTH_REDIRECT_URI


def cible_frontend(platform: str) -> str:
    """URL de retour vers le frontend, choisie dans une liste blanche fermée.

    `platform` est une simple étiquette ("web" / "mobile") : aucune URL fournie
    par le client n'est acceptée, ce qui élimine le risque d'open redirect.
    """
    if platform == "mobile" and settings.GOOGLE_POST_LOGIN_MOBILE_URL:
        return settings.GOOGLE_POST_LOGIN_MOBILE_URL
    return settings.GOOGLE_POST_LOGIN_WEB_URL


def plateformes_disponibles() -> tuple[str, ...]:
    if settings.GOOGLE_POST_LOGIN_MOBILE_URL:
        return ("web", "mobile")
    return ("web",)


# ─── PKCE ─────────────────────────────────────────────────────────────────────
def nouveau_code_verifier() -> str:
    """`code_verifier` PKCE : 43 à 128 caractères non réservés (RFC 7636)."""
    return secrets.token_urlsafe(64)[:96]


def code_challenge(verifier: str) -> str:
    """`code_challenge` = BASE64URL(SHA256(verifier)), sans remplissage."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def nouveau_secret_url() -> str:
    """Valeur aléatoire pour un `state`, un `nonce` ou un code de ticket."""
    return secrets.token_urlsafe(32)


def hacher_code(code: str) -> str:
    """SHA-256 hexadécimal — les tickets ne sont jamais stockés en clair."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# ─── Étape 1 : URL d'autorisation ─────────────────────────────────────────────
def url_autorisation(*, state: str, nonce: str, verifier: str) -> str:
    parametres = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge(verifier),
        "code_challenge_method": "S256",
        # `select_account` évite de reconnecter silencieusement un compte Google
        # laissé ouvert sur un téléphone partagé.
        "prompt": "select_account",
        "access_type": "online",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(parametres)}"


# ─── Étape 2 : échange du code ────────────────────────────────────────────────
def echanger_code(code: str, verifier: str) -> dict:
    """Échange serveur↔serveur du `code` contre les jetons Google.

    C'est le seul endroit où le `client_secret` est utilisé, sur une connexion
    TLS sortante vers Google. Aucun jeton Google n'est conservé en base.
    """
    donnees = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }
    try:
        reponse = requests.post(GOOGLE_TOKEN_ENDPOINT, data=donnees, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GoogleOAuthError("google_unreachable", str(exc)) from exc

    if reponse.status_code != 200:
        raise GoogleOAuthError("token_exchange_failed", reponse.text[:300])

    try:
        charge = reponse.json()
    except ValueError as exc:
        raise GoogleOAuthError("token_exchange_failed", "réponse non JSON") from exc

    if not charge.get("id_token"):
        raise GoogleOAuthError("missing_id_token")
    return charge


# ─── Étape 3 : vérification de l'identité ─────────────────────────────────────
def verifier_id_token(id_token_brut: str, nonce_attendu: str) -> dict:
    """Vérifie l'id_token et retourne l'identité Google normalisée.

    Contrôles effectués par `google-auth` : signature RS256 contre les clés
    publiques Google, `aud` == GOOGLE_CLIENT_ID, `exp`, `iss`.
    Contrôles explicites ajoutés ici : `iss` dans la liste attendue, `nonce`
    identique à celui du flux, présence du `sub`, `email_verified` vrai.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        charge = google_id_token.verify_oauth2_token(
            id_token_brut,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:  # signature, audience, expiration, clés…
        raise GoogleOAuthError("invalid_identity", str(exc)) from exc

    if charge.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleOAuthError("invalid_issuer", str(charge.get("iss")))

    # Comparaison à temps constant : le nonce lie l'id_token à CE flux précis.
    if not nonce_attendu or not secrets.compare_digest(
        str(charge.get("nonce", "")), str(nonce_attendu)
    ):
        raise GoogleOAuthError("invalid_nonce")

    sub = str(charge.get("sub") or "").strip()
    if not sub:
        raise GoogleOAuthError("invalid_identity", "sub absent")

    email_verifie = charge.get("email_verified")
    if email_verifie in ("true", "True"):
        email_verifie = True
    if email_verifie is not True:
        raise GoogleOAuthError("email_not_verified")

    return {
        "sub": sub,
        "email": (charge.get("email") or "").strip().lower(),
        "email_verified": True,
        "given_name": (charge.get("given_name") or "").strip()[:150],
        "family_name": (charge.get("family_name") or "").strip()[:150],
    }
