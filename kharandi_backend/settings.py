import environ
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY    = env("SECRET_KEY")
DEBUG         = env("DEBUG")

# ─── Hôtes autorisés ──────────────────────────────────────────────────────────
# On n'utilise JAMAIS ALLOWED_HOSTS = ["*"] : le filtrage est double,
#   1. Nginx rejette (444) tout Host qui n'est pas dans son `server_name`,
#   2. Django valide à nouveau via cette liste.
#
# Les hôtes « internes » ci-dessous sont ajoutés d'office et ne peuvent pas
# être oubliés dans le .env : sans eux le healthcheck du conteneur `api`
# (http://127.0.0.1:8000/healthz) tomberait en 400 DisallowedHost.
_INTERNAL_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    "api",      # nom de service Docker (nginx -> api:8000)
    "nginx",
]

_PUBLIC_ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["212.95.33.158", "api.kharandi.gn", "kharandi.gn", "www.kharandi.gn"],
)

ALLOWED_HOSTS = list(dict.fromkeys(
    [h.strip() for h in _PUBLIC_ALLOWED_HOSTS if h.strip()] + _INTERNAL_ALLOWED_HOSTS
))

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_crontab",
    "cloudinary",
    "cloudinary_storage",
    "core",
    "users",
    "learning",
    "ai_features",
    "ecommerce",
    "payments",
    "notifications",
    "support",
    "reports",
    "search",
    "ecole",
    "content",
    "marketplace",
    "grades",
]


UNFOLD = {
    "SITE_TITLE": "Kharandi Admin",
    "SITE_HEADER": "Kharandi",
    "SITE_SUBHEADER": "Administration Platform",
    "SITE_SYMBOL": "school",

    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,

        "navigation": [
            {
                "title": "Kharandi",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Tableau de bord",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                    {
                        "title": "Utilisateurs",
                        "icon": "people",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Profils",
                        "icon": "badge",
                        "link": "/admin/users/profile/",
                    },
                ],
            },

            {
                "title": "Éducation",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Documents",
                        "icon": "description",
                        "link": "/admin/learning/document/",
                    },
                    {
                        "title": "Matières",
                        "icon": "menu_book",
                        "link": "/admin/learning/subject/",
                    },
                    {
                        "title": "QCM",
                        "icon": "quiz",
                        "link": "/admin/learning/qcm/",
                    },
                ],
            },

            {
                "title": "Finance",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Plans",
                        "icon": "payments",
                        "link": "/admin/payments/plan/",
                    },
                    {
                        "title": "Abonnements",
                        "icon": "card_membership",
                        "link": "/admin/payments/subscription/",
                    },
                    {
                        "title": "Transactions",
                        "icon": "receipt_long",
                        "link": "/admin/payments/transaction/",
                    },
                    {
                        "title": "Commandes",
                        "icon": "shopping_cart",
                        "link": "/admin/ecommerce/order/",
                    },
                ],
            },

            {
                "title": "Marketplace",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Produits",
                        "icon": "inventory_2",
                        "link": "/admin/marketplace/product/",
                    },
                    {
                        "title": "Commandes vendeurs",
                        "icon": "store",
                        "link": "/admin/marketplace/order/",
                    },
                ],
            },

            {
                "title": "Kharandi École",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Écoles",
                        "icon": "school",
                        "link": "/admin/ecole/school/",
                    },
                    {
                        "title": "Enseignants",
                        "icon": "person",
                        "link": "/admin/ecole/schoolteacher/",
                    },
                    {
                        "title": "Élèves",
                        "icon": "groups",
                        "link": "/admin/ecole/schoolstudent/",
                    },
                    {
                        "title": "Classes",
                        "icon": "class",
                        "link": "/admin/ecole/schoolclass/",
                    },
                    {
                        "title": "Notes",
                        "icon": "grade",
                        "link": "/admin/ecole/schoolgrade/",
                    },
                    {
                        "title": "Paiements",
                        "icon": "account_balance_wallet",
                        "link": "/admin/ecole/schoolpayment/",
                    },
                    {
                        "title": "Absences",
                        "icon": "event_busy",
                        "link": "/admin/ecole/schoolabsence/",
                    },
                ],
            },

            {
                "title": "Intelligence artificielle",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Base de connaissances",
                        "icon": "psychology",
                        "link": "/admin/ai_features/guineaknowledgeentry/",
                    },
                ],
            },

            {
                "title": "Support",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Tickets",
                        "icon": "support_agent",
                        "link": "/admin/support/ticket/",
                    },
                ],
            },

            {
                "title": "Contenu",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Actualités",
                        "icon": "article",
                        "link": "/admin/content/news/",
                    },
                    {
                        "title": "Bourses",
                        "icon": "school",
                        "link": "/admin/content/scholarship/",
                    },
                    {
                        "title": "Classements scolaires",
                        "icon": "leaderboard",
                        "link": "/admin/content/schoolranking/",
                    },
                    {
                        "title": "Étudier à l'étranger",
                        "icon": "flight",
                        "link": "/admin/content/studyabroad/",
                    },
                    {
                        "title": "Annonces répétiteurs",
                        "icon": "campaign",
                        "link": "/admin/content/tutorad/",
                    },
                    {
                        "title": "Notifications",
                        "icon": "notifications",
                        "link": "/admin/content/notification/",
                    },
                ],
            },
        ],
    },
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.RateLimitMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF    = "kharandi_backend.urls"
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
               "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
               "OPTIONS": {"context_processors": [
                   "django.template.context_processors.request",
                   "django.contrib.auth.context_processors.auth",
                   "django.contrib.messages.context_processors.messages",
                   "kharandi_backend.admin_context.admin_dashboard",
               ]}}]

WSGI_APPLICATION = "kharandi_backend.wsgi.application"
DATABASES = {"default": env.db("DATABASE_URL",
    default="postgres://postgres:postgres@localhost:5432/kharandi_db")}

# ─── Cache Redis ──────────────────────────────────────────────────────────────
_REDIS_URL = env("REDIS_URL", default="")
if _REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND":  "django_redis.cache.RedisCache",
            "LOCATION": _REDIS_URL,
            "OPTIONS":  {
                "CLIENT_CLASS":           "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT":         5,
                "IGNORE_EXCEPTIONS":      True,
            },
            "KEY_PREFIX": "kharandi",
            "TIMEOUT":    300,
        }
    }
    SESSION_ENGINE      = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND":  "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kharandi-local",
        }
    }

# ─── DRF ─────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE":             20,
    "PAGE_SIZE_QUERY_PARAM": "page_size",
    "MAX_PAGE_SIZE":         500,
    "DEFAULT_SCHEMA_CLASS":  "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER":     "core.utils.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS":  True,
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
# CORS_ALLOW_ALL_ORIGINS = True désactive les restrictions → pratique en dev/test
# En production, mettre False et utiliser CORS_ALLOWED_ORIGINS
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:5173",
    "http://localhost:3000",
    "https://kharandi.gn",
    "https://www.kharandi.gn",
])

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-device-token",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# ─── Nimba SMS ────────────────────────────────────────────────────────────────
NIMBA_ACCOUNT_SID = env("NIMBA_ACCOUNT_SID", default="")
NIMBA_AUTH_TOKEN  = env("NIMBA_AUTH_TOKEN",  default="")
NIMBA_SENDER_NAME = env("NIMBA_SENDER_NAME", default="Kharandi")

# ─── LengoPay ─────────────────────────────────────────────────────────────────
# Référence : documentation officielle LengoPay « Collect payments (Cash In) »
#   Création  : POST {LENGOPAY_BASE_URL}/payments
#               body {websiteid, amount, currency, country, return_url,
#                     failure_url, callback_url}
#               réponse {status:"Success", pay_id, payment_url}
#   Statut    : POST {LENGOPAY_BASE_URL}/transaction/status
#               body {pay_id, websiteid}
#               réponse {status, pay_id, date, amount}
#   Callback  : POST vers callback_url, body
#               {pay_id, status, amount, message, Client}
#               → NON signé (aucun HMAC dans la documentation).
LENGOPAY_SITE_ID     = env("LENGOPAY_SITE_ID",     default="")
LENGOPAY_LICENSE_KEY = env("LENGOPAY_LICENSE_KEY", default="")
LENGOPAY_CURRENCY    = env("LENGOPAY_CURRENCY",    default="GNF")
LENGOPAY_COUNTRY     = env("LENGOPAY_COUNTRY",     default="GN")

# Racine de l'API. Passer à https://sandbox.lengopay.com/api/v1 pour les tests.
LENGOPAY_BASE_URL = env(
    "LENGOPAY_BASE_URL",
    default="https://portal.lengopay.com/api/v1",
).rstrip("/")

# Endpoint de création de paiement (Cash In).
# `or` et non `default=` seul : une variable présente mais VIDE dans le .env
# renvoie une chaîne vide, pas la valeur par défaut.
LENGOPAY_PAYMENT_URL = (
    env("LENGOPAY_PAYMENT_URL", default="").strip()
    or f"{LENGOPAY_BASE_URL}/payments"
)

# Endpoint de vérification serveur-à-serveur du statut réel d'un paiement.
# ATTENTION : c'est un POST avec {pay_id, websiteid}, PAS un GET sur
# /payments/{pay_id} (cet ancien défaut renvoyait une erreur HTTP et cassait
# toute la confirmation des callbacks).
LENGOPAY_STATUS_URL = (
    env("LENGOPAY_STATUS_URL", default="").strip()
    or f"{LENGOPAY_BASE_URL}/transaction/status"
)

# Jeton secret placé dans l'URL de callback. LengoPay ne signant pas ses
# notifications, c'est LUI qui authentifie l'appel : seul un émetteur
# connaissant l'URL complète peut déclencher une activation.
# Générer avec :  python -c "import secrets; print(secrets.token_urlsafe(32))"
LENGOPAY_CALLBACK_TOKEN = env("LENGOPAY_CALLBACK_TOKEN", default="").strip()

# Base publique du backend, utilisée pour construire l'URL de callback.
LENGOPAY_PUBLIC_BASE_URL = env(
    "LENGOPAY_PUBLIC_BASE_URL",
    default="http://212.95.33.158",
).rstrip("/")

# URL de callback transmise à LengoPay. Laissée vide, elle est construite
# automatiquement à partir de LENGOPAY_PUBLIC_BASE_URL et du jeton.
LENGOPAY_CALLBACK_URL = env("LENGOPAY_CALLBACK_URL", default="").strip()
if not LENGOPAY_CALLBACK_URL:
    if LENGOPAY_CALLBACK_TOKEN:
        LENGOPAY_CALLBACK_URL = (
            f"{LENGOPAY_PUBLIC_BASE_URL}/api/v1/payments/webhook/"
            f"{LENGOPAY_CALLBACK_TOKEN}/"
        )
    else:
        LENGOPAY_CALLBACK_URL = f"{LENGOPAY_PUBLIC_BASE_URL}/api/v1/payments/webhook/"

# Signature HMAC facultative (passerelle intermédiaire ou évolution future du
# fournisseur). Vide = chemin inutilisé.
LENGOPAY_WEBHOOK_SECRET = env("LENGOPAY_WEBHOOK_SECRET", default="").strip()

# CONFIRMATION SERVEUR OBLIGATOIRE — activée par défaut.
#
# Un callback annonçant « SUCCESS » ne suffit JAMAIS à valider un paiement :
# il faut que LengoPay le confirme par un appel serveur-à-serveur
# (POST /transaction/status). Le jeton d'URL authentifie l'émetteur, mais
# l'argent n'est reconnu encaissé que sur la parole de l'API.
#
# Ce réglage n'a de sens QUE parce que Celery Beat réconcilie les paiements
# toutes les quelques minutes : si l'API LengoPay est momentanément muette, le
# callback est journalisé en UNVERIFIED, la transaction reste en attente, et la
# réconciliation la rattrape dès que l'API répond — rien n'est perdu.
#
# ⚠ Ne repasser à False que si le service `beat` est à l'arrêt : sans
#   réconciliation automatique, ce mode strict bloquerait les paiements.
LENGOPAY_REQUIRE_STATUS_CONFIRMATION = env.bool(
    "LENGOPAY_REQUIRE_STATUS_CONFIRMATION", default=True
)

# Tolérance sur le montant renvoyé par le callback, en unités de devise.
# Un écart supérieur bloque l'activation et déclenche une alerte.
LENGOPAY_AMOUNT_TOLERANCE = env("LENGOPAY_AMOUNT_TOLERANCE", default="1").strip() or "1"

# Délai d'appel HTTP vers LengoPay (secondes).
LENGOPAY_TIMEOUT = env.int("LENGOPAY_TIMEOUT", default=20)

# ─── Karamo AI ────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")
TAVILY_API_KEY     = env("TAVILY_API_KEY",     default="")

# ─── Admin ────────────────────────────────────────────────────────────────────
ADMIN_PHONE    = env("ADMIN_PHONE",    default="")
ADMIN_PASSWORD = env("ADMIN_PASSWORD", default="")
CRON_SECRET    = env("CRON_SECRET",    default="")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Cloudinary ───────────────────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY    = env("CLOUDINARY_API_KEY",    default="")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", default="")
USE_CLOUDINARY        = env.bool("USE_CLOUDINARY",   default=False)

if USE_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
    import cloudinary
    cloudinary.config(
        cloud_name  = CLOUDINARY_CLOUD_NAME,
        api_key     = CLOUDINARY_API_KEY,
        api_secret  = CLOUDINARY_API_SECRET,
        secure      = True,
    )
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY":    CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
        "SECURE":     True,
        "PREFIX":     "kharandi",
    }
else:
    MEDIA_URL  = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# django-crontab : conservé uniquement pour compatibilité mais VOLONTAIREMENT
# vide. La planification est désormais assurée par Celery Beat (service `beat`),
# voir CELERY_BEAT_SCHEDULE plus bas.
#
# Pourquoi ce changement : django-crontab écrit dans la crontab du conteneur,
# or les conteneurs n'exécutent pas de démon cron — ces tâches ne tournaient
# donc jamais. Les laisser déclarées donnerait une fausse impression de
# sécurité, et un doublon si un cron hôte était ajouté plus tard.
CRONJOBS = []

SPECTACULAR_SETTINGS = {
    "TITLE":                "Kharandi API",
    "VERSION":              "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LANGUAGE_CODE      = "fr-fr"
TIME_ZONE          = "Africa/Conakry"
USE_I18N = USE_TZ  = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FRONTEND_URL       = env("FRONTEND_URL", default="https://kharandi.gn")

# ─── Celery ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL                        = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND                    = "django-db"
CELERY_ACCEPT_CONTENT                    = ["json"]
CELERY_TASK_SERIALIZER                   = "json"
CELERY_RESULT_SERIALIZER                 = "json"
CELERY_TIMEZONE                          = "Africa/Conakry"
CELERY_TASK_TRACK_STARTED                = True
CELERY_TASK_TIME_LIMIT                   = 300
CELERY_TASK_SOFT_TIME_LIMIT              = 240
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Une tâche perdue au redémarrage d'un worker serait une réconciliation non
# exécutée. L'accusé de réception tardif fait rejouer la tâche si le worker
# meurt en cours de traitement ; les tâches étant idempotentes, c'est sans
# danger.
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Purge les résultats de tâches après 7 jours : sans cela, la table
# django_celery_results_taskresult grossit indéfiniment (une tâche par minute).
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7

INSTALLED_APPS += ["django_celery_results"]

# ─── Celery Beat — planificateur ──────────────────────────────────────────────
# Beat tourne dans son PROPRE conteneur (service `beat` de docker-compose).
# Il ne doit JAMAIS y en avoir deux en parallèle : chaque tâche serait émise en
# double. Les tâches sont malgré tout protégées par un verrou Redis et par
# `select_for_update()`, mais mieux vaut ne pas s'y fier.
#
# Le planificateur par défaut (PersistentScheduler) conserve son état dans un
# fichier, monté sur le volume `beat_data`. Aucune migration supplémentaire
# n'est nécessaire, contrairement à django-celery-beat.
CELERY_BEAT_SCHEDULE_FILENAME = env(
    "CELERY_BEAT_SCHEDULE_FILENAME",
    default=str(BASE_DIR / "beat" / "celerybeat-schedule"),
)

# Fréquence de réconciliation des paiements, en minutes. C'est le délai
# maximal pendant lequel un client ayant payé peut rester sans son abonnement
# si le callback est perdu.
LENGOPAY_RECONCILE_EVERY_MIN = env.int("LENGOPAY_RECONCILE_EVERY_MIN", default=3)

CELERY_BEAT_SCHEDULE = {
    # ── Paiements : le filet de sécurité ────────────────────────────────────
    "reconciliation-lengopay": {
        "task": "payments.reconcile_lengopay",
        "schedule": LENGOPAY_RECONCILE_EVERY_MIN * 60.0,
        "kwargs": {"max_age_hours": 48},
        # Une exécution qui a pris du retard n'est pas rejouée en rafale.
        "options": {"expires": LENGOPAY_RECONCILE_EVERY_MIN * 60},
    },
    "rejeu-callbacks-orphelins": {
        "task": "payments.replay_orphan_callbacks",
        "schedule": 60.0,
        "kwargs": {"max_age_hours": 72},
        "options": {"expires": 55},
    },

    # ── Abonnements ─────────────────────────────────────────────────────────
    "expiration-abonnements": {
        "task": "payments.expire_subscriptions",
        "schedule": 15 * 60.0,
        "options": {"expires": 14 * 60},
    },
    # Fenêtre d'examen d'une heure dans la fonction → cadence horaire imposée.
    "alerte-abonnements-expirants": {
        "task": "payments.warn_expiring_subscriptions",
        "schedule": 60 * 60.0,
        "options": {"expires": 55 * 60},
    },

    # ── Maintenance ─────────────────────────────────────────────────────────
    "nettoyage-otp": {
        "task": "core.cleanup_expired_otps",
        "schedule": 30 * 60.0,
        "options": {"expires": 25 * 60},
    },
    "prechauffage-cache": {
        "task": "core.warmup_subjects_cache",
        "schedule": 6 * 60 * 60.0,
        "options": {"expires": 60 * 60},
    },

    # ── Supervision de Beat lui-même ────────────────────────────────────────
    # Prouve que la chaîne Beat → Redis → Worker fonctionne. Un Beat mort
    # silencieusement est plus dangereux qu'un Beat qui plante.
    "battement-beat": {
        "task": "payments.beat_heartbeat",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}

# ─── Rate Limiting ────────────────────────────────────────────────────────────
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_MIN = 300
RATE_LIMIT_AI_MIN  = 60
SCHOOL_TOKEN_MAX_AGE = env.int("SCHOOL_TOKEN_MAX_AGE", default=12 * 60 * 60)

# ─── Reverse proxy / VPS YIGUI ────────────────────────────────────────────────
# Django est servi derrière Nginx.
#
# USE_X_FORWARDED_HOST = False (choix volontaire) :
#   Nginx transmet déjà le vrai `Host` via `proxy_set_header Host $host`
#   (cf. nginx/proxy_params.conf). Faire confiance à X-Forwarded-Host serait
#   inutile ici et ouvrirait une surface d'attaque par empoisonnement d'en-tête.
#   À passer à True uniquement si un second proxy (Cloudflare, load balancer)
#   vient un jour se placer devant Nginx.
USE_X_FORWARDED_HOST  = env.bool("USE_X_FORWARDED_HOST", default=False)
USE_X_FORWARDED_PORT  = True

# Nginx pose systématiquement X-Forwarded-Proto : Django sait ainsi si la
# requête d'origine était en HTTPS (cookies sécurisés, request.is_secure()).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Origines de confiance pour les requêtes POST (admin Django, formulaires).
# Le SCHÉMA est obligatoire. On conserve l'accès HTTP par IP tant que le SSL
# n'est pas activé, sinon l'admin Django refuserait toute connexion.
_CSRF_DEFAULTS = [
    "https://kharandi.gn",
    "https://www.kharandi.gn",
    "http://212.95.33.158",
]
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
    o.strip() for o in env.list("CSRF_TRUSTED_ORIGINS", default=_CSRF_DEFAULTS) if o.strip()
))

# Durcissement activé uniquement hors DEBUG et lorsque HTTPS est en place
_SSL_ENABLED = env.bool("ENABLE_HTTPS", default=False)
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY      = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS             = "SAMEORIGIN"
    SESSION_COOKIE_HTTPONLY     = True
    if _SSL_ENABLED:
        SECURE_SSL_REDIRECT      = False   # la redirection est gérée par Nginx
        SESSION_COOKIE_SECURE    = True
        CSRF_COOKIE_SECURE       = True
        SECURE_HSTS_SECONDS      = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD      = True

# Taille maximale des envois (uploads de documents)
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
