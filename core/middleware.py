"""
core/middleware.py — Rate Limiting par IP via Redis
────────────────────────────────────────────────────
- API générale  : 60 req/min par IP
- Endpoints AI  : 10 req/min par IP
- Désactivé en DEBUG
"""
from django.conf import settings
from django.http import JsonResponse
from core.redis_utils import rate_limit_check
import logging

logger = logging.getLogger(__name__)

# Endpoints Karamo/AI → limite plus stricte
AI_PATHS = ["/api/v1/ai/ask/", "/api/v1/ai/ask/stream/", "/api/v1/ai/ask-image/"]

# Sondes de santé : jamais limitées. Docker interroge /healthz toutes les 30 s ;
# si Redis venait à tomber, un rate-limit sur ces routes rendrait le conteneur
# artificiellement « unhealthy ».
EXEMPT_PATHS = ("/healthz", "/readyz", "/nginx-health")

# Callbacks de paiement : JAMAIS limités. LengoPay réémet ses notifications
# depuis un petit nombre d'adresses IP ; sous forte charge, un rate-limit
# renverrait un 429 et ferait perdre des confirmations de paiement.
EXEMPT_PREFIXES = ("/api/v1/payments/webhook",)


class RateLimitMiddleware:
    """
    Middleware de rate limiting par IP.
    S'appuie sur Redis via core.redis_utils.rate_limit_check.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled      = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self.general_limit = getattr(settings, "RATE_LIMIT_PER_MIN", 60)
        self.ai_limit      = getattr(settings, "RATE_LIMIT_AI_MIN",  10)

    def __call__(self, request):
        # Désactivé en dev ou si Redis non configuré
        if not self.enabled or settings.DEBUG:
            return self.get_response(request)

        if request.path in EXEMPT_PATHS:
            return self.get_response(request)

        if request.path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        ip    = self._get_ip(request)
        path  = request.path
        is_ai = any(path.startswith(p) for p in AI_PATHS)

        limit = self.ai_limit if is_ai else self.general_limit
        key   = f"rl:{'ai' if is_ai else 'api'}:{ip}"

        if not rate_limit_check(key, limit=limit, window=60):
            logger.warning("Rate limit dépassé — IP=%s path=%s", ip, path)
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Trop de requêtes. Veuillez patienter une minute."
                        if not is_ai else
                        "Vous envoyez trop de messages à Karamö. Patientez 1 minute."
                    ),
                    "code": "rate_limited",
                },
                status=429,
            )

        return self.get_response(request)

    @staticmethod
    def _get_ip(request) -> str:
        """Récupère l'IP réelle même derrière un proxy (Render, Cloudflare)."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
