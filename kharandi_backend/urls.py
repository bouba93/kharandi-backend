from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def home(request):
    return JsonResponse({"api": "Kharandi API", "version": "1.0.0", "status": "online", "docs": "/api/docs/"})


def healthz(request):
    """LIVENESS — « le process Django répond-il ? »

    Volontairement SANS accès base de données ni Redis : c'est la sonde
    utilisée par le healthcheck Docker du conteneur `api`. Une panne
    momentanée de PostgreSQL ne doit pas faire passer le conteneur
    applicatif en `unhealthy` (ce qui masquerait la vraie cause et
    déclencherait des redémarrages inutiles).

    Pour un contrôle complet, utiliser /readyz.
    """
    return JsonResponse({"status": "ok", "service": "kharandi-api"}, status=200)


def readyz(request):
    """READINESS — « l'application peut-elle réellement servir du trafic ? »

    Vérifie PostgreSQL et Redis. Renvoie 503 si une dépendance critique est
    indisponible. Destinée au monitoring externe et au diagnostic, pas au
    healthcheck du conteneur.
    """
    from django.core.cache import cache
    from django.db import connection

    checks = {}

    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        cache.set("kharandi:readyz", "1", 10)
        checks["cache"] = cache.get("kharandi:readyz") == "1"
    except Exception:
        checks["cache"] = False

    # La base est critique ; le cache est dégradable (IGNORE_EXCEPTIONS=True).
    healthy = checks["database"]
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )

api_v1 = [
    path("auth/",          include("users.urls")),
    path("users/",         include("users.self_urls")),
    path("ai/",            include("ai_features.urls")),
    path("learning/",      include("learning.urls")),
    path("payments/",      include("payments.urls")),
    path("store/",         include("ecommerce.urls")),
    path("notifications/", include("notifications.urls")),
    path("support/",       include("support.urls")),
    path("reports/",       include("reports.urls")),
    path("ecole/",  include("ecole.urls")),
    path("search/",        include("search.urls")),
    path("content/",       include("content.urls")),
    path("marketplace/",   include("marketplace.urls")),
    path("grades/",        include("grades.urls")),
]

urlpatterns = [
    path("",            home),
    path("healthz",     healthz, name="healthz"),   # liveness  (Docker)
    path("readyz",      readyz,  name="readyz"),    # readiness (monitoring)
    path("admin/",      admin.site.urls),
    path("api/v1/",     include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# ─── Gestionnaires d'erreur : JSON, jamais de page HTML ──────────────────────
#
# Deuxième niveau de protection, en complément de core.middleware.
# ErreursJsonMiddleware : Django court-circuite la chaîne de middlewares pour
# certaines erreurs et rend alors le gabarit HTML par défaut. Ces gestionnaires
# garantissent une réponse JSON dans tous les cas.
from core.middleware import erreur_json  # noqa: E402


def handler400(request, exception=None):
    return erreur_json(request, exception, status=400)


def handler403(request, exception=None):
    return erreur_json(request, exception, status=403)


def handler404(request, exception=None):
    return erreur_json(request, exception, status=404)


def handler500(request):
    return erreur_json(request, None, status=500)
