"""
core/middleware.py — Rate limiting et garantie « API = JSON »
─────────────────────────────────────────────────────────────
1. RateLimitMiddleware   : limitation de débit par utilisateur (IP en repli).
2. ErreursJsonMiddleware : aucune route /api/ ne renvoie jamais de HTML.

Les limites sont lues dans les réglages à CHAQUE requête (et non figées à
l'instanciation du middleware) afin que `override_settings` fonctionne en test
et qu'un changement de variable d'environnement soit pris en compte au simple
redémarrage du conteneur, sans reconstruction d'image.
"""
import hashlib
import logging

from django.conf import settings
from django.http import JsonResponse
from core.redis_utils import rate_limit_check

logger = logging.getLogger(__name__)

# Endpoints Karamo/AI → limite dédiée.
# Note : "/api/v1/ai/ask/" est un préfixe de "/api/v1/ai/ask/stream/",
# le streaming est donc couvert par la même règle.
AI_PATHS = ["/api/v1/ai/ask/", "/api/v1/ai/ask-image/"]

# Sondes de santé : jamais limitées. Docker interroge /healthz toutes les 30 s ;
# si Redis venait à tomber, un rate-limit sur ces routes rendrait le conteneur
# artificiellement « unhealthy ».
EXEMPT_PATHS = ("/healthz", "/readyz", "/nginx-health")

# Callbacks de paiement : JAMAIS limités. LengoPay réémet ses notifications
# depuis un petit nombre d'adresses IP ; sous forte charge, un rate-limit
# renverrait un 429 et ferait perdre des confirmations de paiement.
EXEMPT_PREFIXES = ("/api/v1/payments/webhook",)


class RateLimitMiddleware:
    """Limitation de débit, par utilisateur authentifié quand c'est possible.

    La clé était auparavant l'adresse IP seule. En Guinée, une grande partie du
    trafic mobile sort derrière le NAT de l'opérateur : des centaines d'élèves
    partagent alors la même IP publique et se volaient mutuellement leur quota
    de requêtes. La clé est donc l'identifiant utilisateur dès qu'il est connu,
    et l'IP uniquement pour le trafic anonyme.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", True) or settings.DEBUG:
            return self.get_response(request)

        if request.path in EXEMPT_PATHS:
            return self.get_response(request)

        if request.path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        path = request.path
        is_ai = any(path.startswith(p) for p in AI_PATHS)

        limit = (
            int(getattr(settings, "RATE_LIMIT_AI_MIN", 30))
            if is_ai
            else int(getattr(settings, "RATE_LIMIT_PER_MIN", 300))
        )

        key = f"rl:{'ai' if is_ai else 'api'}:{self._identite(request)}"

        if not rate_limit_check(key, limit=limit, window=60):
            logger.warning(
                "Rate limit dépassé — identite=%s path=%s limite=%s/min",
                self._identite(request), path, limit,
            )
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Vous envoyez trop de messages à Karamo. Patientez 1 minute."
                        if is_ai else
                        "Trop de requêtes. Veuillez patienter une minute."
                    ),
                    "code": "rate_limited",
                    "error": "rate_limited",
                    "limite_par_minute": limit,
                },
                status=429,
                json_dumps_params={"ensure_ascii": False},
            )

        return self.get_response(request)

    @staticmethod
    def _identite(request) -> str:
        """Identifiant de compteur : porteur du jeton si présent, sinon IP.

        Un middleware s'exécute AVANT l'authentification DRF : `request.user`
        est encore anonyme pour un client JWT. On dérive donc l'identité d'une
        empreinte du jeton présenté (jamais du jeton lui-même, qui ne doit ni
        être journalisé ni finir dans une clé de cache en clair). Un jeton
        correspond à une session utilisateur : le compteur est donc de fait par
        utilisateur, et non plus partagé par toutes les personnes derrière la
        même IP NAT.
        """
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return f"u{user.pk}"

        jeton = (
            request.META.get("HTTP_AUTHORIZATION")
            or request.META.get("HTTP_X_SCHOOL_TOKEN")
            or ""
        ).strip()
        if jeton:
            empreinte = hashlib.sha256(jeton.encode("utf-8", "ignore")).hexdigest()[:16]
            return f"t{empreinte}"

        return f"ip{RateLimitMiddleware._get_ip(request)}"

    @staticmethod
    def _get_ip(request) -> str:
        """Récupère l'IP réelle même derrière un proxy (Nginx, Cloudflare)."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")


# ══════════════════════════════════════════════════════════════════════════════
#  GARANTIE : UNE ROUTE /api/ NE RENVOIE JAMAIS DE HTML
# ══════════════════════════════════════════════════════════════════════════════

# Préfixes considérés comme « API » : leurs réponses doivent toujours être
# lisibles par un client JSON.
PREFIXES_API = ("/api/", "/healthz", "/readyz")

# Messages lisibles associés aux codes d'erreur les plus courants.
MESSAGES_PAR_CODE = {
    400: "Requête invalide.",
    401: "Authentification requise.",
    403: "Accès refusé.",
    404: "Ressource introuvable.",
    405: "Méthode HTTP non autorisée sur cette route.",
    413: "Corps de requête trop volumineux.",
    414: "URL trop longue.",
    429: "Trop de requêtes.",
    500: "Erreur interne du serveur.",
    502: "Passerelle en erreur.",
    503: "Service temporairement indisponible.",
    504: "Délai d'attente dépassé.",
}


class ErreursJsonMiddleware:
    """Convertit en JSON toute réponse d'erreur HTML sur une route d'API.

    DRF gère déjà proprement les erreurs levées dans les vues. Mais certaines
    erreurs se produisent AVANT ou EN DEHORS de DRF et Django y répond par une
    page HTML :

      - `DisallowedHost` → 400 Bad Request en HTML (cas classique quand Nginx
        ne transmet pas l'en-tête Host attendu par ALLOWED_HOSTS) ;
      - une URL qui ne correspond à aucune route → page 404 HTML ;
      - une exception non capturée hors vue DRF → page 500 HTML ;
      - `CommonMiddleware` / `SecurityMiddleware` → redirections et 400 HTML.

    Un frontend qui fait `response.json()` échoue alors avec « Expected JSON,
    got HTML », ce qui masque complètement la vraie cause. Ce middleware est le
    filet de sécurité : il inspecte le type de contenu des réponses d'erreur
    sur les routes d'API et le remplace par une enveloppe JSON équivalente.

    Il ne touche JAMAIS :
      - les réponses de succès ;
      - les réponses déjà en JSON ;
      - les flux `text/event-stream` (SSE) ;
      - les routes hors API (/admin/, /static/, page d'accueil…).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self._json_si_besoin(request, response)

    @staticmethod
    def _est_route_api(request) -> bool:
        chemin = request.path or ""
        return chemin.startswith(PREFIXES_API)

    def _json_si_besoin(self, request, response):
        if response.status_code < 400:
            return response
        if not self._est_route_api(request):
            return response

        type_contenu = (response.get("Content-Type") or "").lower()

        # Déjà exploitable par un client JSON, ou flux SSE : on ne touche pas.
        if "json" in type_contenu or "event-stream" in type_contenu:
            return response

        # Les réponses en streaming ne peuvent pas être relues sans casser le
        # flux : on les laisse passer (la vue SSE gère déjà ses erreurs).
        if getattr(response, "streaming", False):
            return response

        code = response.status_code
        message = MESSAGES_PAR_CODE.get(code, "Erreur.")

        detail = None
        if code == 400 and self._probable_hote_refuse(request):
            message = (
                "Hôte HTTP non autorisé par le serveur (ALLOWED_HOSTS). "
                "Vérifiez l'en-tête Host transmis par le reverse proxy."
            )
            detail = {"host_recu": request.META.get("HTTP_HOST", "")}

        logger.warning(
            "Réponse HTML %s convertie en JSON — chemin=%s type=%s",
            code, request.path, type_contenu or "(absent)",
        )

        corps = {
            "success": False,
            "message": message,
            "error": message,
            "errors": detail,
            "details": detail,
            "status": code,
        }
        nouvelle = JsonResponse(
            corps, status=code, json_dumps_params={"ensure_ascii": False}
        )
        # On conserve les en-têtes signifiants de la réponse d'origine
        # (Allow pour un 405, WWW-Authenticate pour un 401, Retry-After…).
        for entete in ("Allow", "WWW-Authenticate", "Retry-After", "Vary"):
            if response.has_header(entete):
                nouvelle[entete] = response[entete]
        return nouvelle

    @staticmethod
    def _probable_hote_refuse(request) -> bool:
        """Un 400 sans corps JSON sur une route d'API sent le DisallowedHost."""
        hote = (request.META.get("HTTP_HOST") or "").split(":")[0]
        if not hote:
            return False
        autorises = [str(h).lower() for h in getattr(settings, "ALLOWED_HOSTS", [])]
        if "*" in autorises:
            return False
        return hote.lower() not in autorises


def erreur_json(request, exception=None, status=500, message=None):
    """Vue d'erreur JSON, branchée sur handler400/403/404/500 dans urls.py.

    Deuxième niveau du filet de sécurité : même si Django court-circuite la
    chaîne de middlewares (ce qu'il fait pour certaines erreurs), la réponse
    reste du JSON dès lors que la requête vise une route d'API.

    Hors API (/admin/, /static/, page d'accueil…) on rend la main aux vues
    d'erreur natives de Django : le back-office doit continuer à afficher ses
    pages HTML normales.
    """
    if not ErreursJsonMiddleware._est_route_api(request):
        from django.views import defaults

        if status == 404:
            return defaults.page_not_found(request, exception)
        if status == 403:
            return defaults.permission_denied(request, exception)
        if status == 400:
            return defaults.bad_request(request, exception)
        return defaults.server_error(request)

    texte = message or MESSAGES_PAR_CODE.get(status, "Erreur.")
    detail = None

    # Cas particulier très courant : Django lève DisallowedHost et rendait ici
    # une page HTML « 400 Bad Request ». C'est la cause classique d'un frontend
    # qui échoue sur « Expected JSON, got HTML ». On nomme explicitement le
    # problème pour que le diagnostic soit immédiat.
    if status == 400 and ErreursJsonMiddleware._probable_hote_refuse(request):
        texte = (
            "Hôte HTTP non autorisé par le serveur (ALLOWED_HOSTS). "
            "Vérifiez l'en-tête Host transmis par le reverse proxy."
        )
        detail = {"host_recu": request.META.get("HTTP_HOST", "")}
        logger.error(
            "Hôte refusé : Host=%r chemin=%s ALLOWED_HOSTS=%s",
            request.META.get("HTTP_HOST", ""), request.path,
            getattr(settings, "ALLOWED_HOSTS", []),
        )

    return JsonResponse(
        {
            "success": False,
            "message": texte,
            "error": texte,
            "errors": detail,
            "details": detail,
            "status": status,
        },
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )
