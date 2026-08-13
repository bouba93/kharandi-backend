"""
core/checks.py — Contrôles de configuration de production
─────────────────────────────────────────────────────────
Ces contrôles s'exécutent à chaque `manage.py check`, donc à chaque démarrage
du conteneur `api` (start.sh). Objectif : rendre IMPOSSIBLE un déploiement en
production avec une configuration dangereuse, au lieu d'espérer que personne
n'oubliera de la vérifier.

Les erreurs (préfixe E) font échouer la commande ; les avertissements (W) sont
affichés sans bloquer. En DEBUG=True, presque tout est réduit à un simple
avertissement : on ne veut pas gêner le développement local.

Lister les contrôles :  python manage.py check
Ignorer un contrôle    :  SILENCED_SYSTEM_CHECKS = ["kharandi.E006"] (à éviter)
"""
from django.conf import settings
from django.core.checks import Error, Warning, register

# Valeurs manifestement non modifiées, à refuser en production.
_SECRETS_INTERDITS = {
    "",
    "change-me",
    "changeme",
    "secret",
    "à_remplir",
    "a_remplir",
    "django-insecure",
    "test-secret-key-for-validation-only-0123456789",
    "à_générer",
    "a_generer",
}

_HOTES_LOCAUX = {"localhost", "127.0.0.1", "[::1]", "api", "nginx", "worker", "beat"}


def _valeur_suspecte(valeur: str) -> bool:
    v = str(valeur or "").strip().lower()
    if v in _SECRETS_INTERDITS:
        return True
    return any(v.startswith(p) for p in ("django-insecure", "change", "à_", "a_rempl"))


@register()
def verifier_configuration_production(app_configs, **kwargs):
    problemes = []
    production = not settings.DEBUG

    # Hors production, on n'impose rien : simple information.
    Niveau = Error if production else Warning

    # ── 1. DEBUG ─────────────────────────────────────────────────────────────
    if settings.DEBUG:
        problemes.append(Warning(
            "DEBUG=True : à ne jamais utiliser en production (fuite de "
            "variables d'environnement et de traces d'exécution sur les pages "
            "d'erreur).",
            hint="Mettre DEBUG=False dans le .env du serveur.",
            id="kharandi.W001",
        ))

    # ── 2. ALLOWED_HOSTS ─────────────────────────────────────────────────────
    if "*" in settings.ALLOWED_HOSTS:
        problemes.append(Niveau(
            "ALLOWED_HOSTS contient « * » : n'importe quel domaine pointé vers "
            "ce serveur serait accepté (empoisonnement d'en-tête Host, liens "
            "de réinitialisation de mot de passe falsifiés).",
            hint="Lister explicitement : api.kharandi.gn, 212.95.33.158.",
            id="kharandi.E002",
        ))

    publics = [h for h in settings.ALLOWED_HOSTS if h not in _HOTES_LOCAUX]
    if production and not publics:
        problemes.append(Error(
            "ALLOWED_HOSTS ne contient aucun hôte public : l'API ne répondra "
            "qu'en local et renverra 400 à tout le trafic externe.",
            hint="Renseigner ALLOWED_HOSTS dans le .env.",
            id="kharandi.E003",
        ))

    # ── 3. CORS ──────────────────────────────────────────────────────────────
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        problemes.append(Niveau(
            "CORS_ALLOW_ALL_ORIGINS=True : n'importe quel site pourrait "
            "appeler l'API depuis le navigateur d'un utilisateur connecté. "
            "Combiné à CORS_ALLOW_CREDENTIALS=True, c'est une faille directe.",
            hint="Mettre CORS_ALLOW_ALL_ORIGINS=False et lister "
                 "CORS_ALLOWED_ORIGINS (https://kharandi.gn, "
                 "https://www.kharandi.gn).",
            id="kharandi.E004",
        ))

    origines = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    if production:
        locales = [o for o in origines if "localhost" in o or "127.0.0.1" in o]
        if locales:
            problemes.append(Warning(
                f"CORS autorise des origines de développement : {locales}. "
                "Sans danger immédiat, mais à retirer de la production.",
                id="kharandi.W005",
            ))
        if not [o for o in origines if o not in locales]:
            problemes.append(Error(
                "Aucune origine CORS de production : le frontend Vercel "
                "(https://kharandi.gn) ne pourra pas appeler l'API.",
                hint="Renseigner CORS_ALLOWED_ORIGINS dans le .env.",
                id="kharandi.E006",
            ))

    for origine in origines:
        if not origine.startswith(("http://", "https://")):
            problemes.append(Error(
                f"Origine CORS invalide : « {origine} » — le schéma "
                "(https://) est obligatoire, sinon l'entrée est ignorée "
                "silencieusement.",
                id="kharandi.E007",
            ))

    # ── 4. CSRF ──────────────────────────────────────────────────────────────
    csrf = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))
    for origine in csrf:
        if not origine.startswith(("http://", "https://")):
            problemes.append(Error(
                f"CSRF_TRUSTED_ORIGINS : « {origine} » doit inclure le schéma "
                "(https://…), sinon Django refusera les connexions à l'admin.",
                id="kharandi.E008",
            ))
        if origine.strip() == "*" or origine.endswith("://*"):
            problemes.append(Niveau(
                "CSRF_TRUSTED_ORIGINS contient un joker : toute origine "
                "pourrait soumettre des formulaires authentifiés.",
                id="kharandi.E009",
            ))

    # ── 5. Secrets ───────────────────────────────────────────────────────────
    if _valeur_suspecte(settings.SECRET_KEY) or len(str(settings.SECRET_KEY)) < 40:
        problemes.append(Niveau(
            "SECRET_KEY absente, trop courte ou laissée à sa valeur d'exemple. "
            "Elle signe les sessions et les jetons : une clé devinable permet "
            "d'usurper n'importe quel compte.",
            hint='Générer : python -c "import secrets; print(secrets.token_urlsafe(64))"',
            id="kharandi.E010",
        ))

    if production and _valeur_suspecte(getattr(settings, "LENGOPAY_LICENSE_KEY", "")):
        problemes.append(Error(
            "LENGOPAY_LICENSE_KEY non renseignée : aucun paiement ne pourra "
            "être créé ni vérifié.",
            id="kharandi.E011",
        ))

    if production and _valeur_suspecte(getattr(settings, "LENGOPAY_SITE_ID", "")):
        problemes.append(Error(
            "LENGOPAY_SITE_ID (websiteid) non renseigné.",
            id="kharandi.E012",
        ))

    if production and _valeur_suspecte(getattr(settings, "CRON_SECRET", "")):
        problemes.append(Warning(
            "CRON_SECRET vide : l'endpoint /api/v1/payments/run-cron/ ne peut "
            "pas être déclenché. Sans conséquence si Celery Beat tourne.",
            id="kharandi.W013",
        ))

    # ── 6. LengoPay : jeton de callback ──────────────────────────────────────
    jeton = str(getattr(settings, "LENGOPAY_CALLBACK_TOKEN", "") or "")
    if production:
        if not jeton:
            problemes.append(Error(
                "LENGOPAY_CALLBACK_TOKEN vide. LengoPay ne signant pas ses "
                "notifications, ce jeton est le SEUL élément qui authentifie "
                "un callback : sans lui, aucun callback ne sera appliqué "
                "(sauf confirmation par l'API) et les paiements dépendront "
                "entièrement de la réconciliation.",
                hint='python -c "import secrets; print(secrets.token_urlsafe(32))"',
                id="kharandi.E014",
            ))
        elif len(jeton) < 24 or _valeur_suspecte(jeton):
            problemes.append(Error(
                f"LENGOPAY_CALLBACK_TOKEN trop court ou trop prévisible "
                f"({len(jeton)} caractères). Il doit être long et aléatoire : "
                "c'est lui qui empêche un tiers d'activer un abonnement non "
                "payé.",
                hint='python -c "import secrets; print(secrets.token_urlsafe(32))"',
                id="kharandi.E015",
            ))

        callback = str(getattr(settings, "LENGOPAY_CALLBACK_URL", "") or "")
        if jeton and jeton not in callback:
            problemes.append(Error(
                "LENGOPAY_CALLBACK_URL ne contient pas le jeton : l'URL "
                "déclarée chez LengoPay ne sera pas authentifiée.",
                hint="Laisser LENGOPAY_CALLBACK_URL vide pour qu'elle soit "
                     "construite automatiquement.",
                id="kharandi.E016",
            ))
        if callback.startswith("http://"):
            problemes.append(Warning(
                "L'URL de callback est en HTTP : le jeton circule en clair. "
                "Acceptable temporairement, à corriger dès qu'un sous-domaine "
                "HTTPS (api.kharandi.gn) est en place.",
                id="kharandi.W017",
            ))

    # ── 7. Cohérence mode strict / réconciliation ───────────────────────────
    if getattr(settings, "LENGOPAY_REQUIRE_STATUS_CONFIRMATION", False):
        planning = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}
        taches = {c.get("task") for c in planning.values()}
        if "payments.reconcile_lengopay" not in taches:
            problemes.append(Error(
                "LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True alors que la tâche "
                "de réconciliation n'est pas planifiée. En mode strict, toute "
                "indisponibilité de l'API LengoPay bloquerait DÉFINITIVEMENT "
                "les paiements concernés.",
                hint="Rétablir « reconciliation-lengopay » dans "
                     "CELERY_BEAT_SCHEDULE, ou repasser le mode strict à False.",
                id="kharandi.E018",
            ))

    # ── 8. Cohérence HTTPS ───────────────────────────────────────────────────
    if production:
        base = str(getattr(settings, "LENGOPAY_PUBLIC_BASE_URL", "") or "")
        front = str(getattr(settings, "FRONTEND_URL", "") or "")
        if front.startswith("https://") and base.startswith("http://"):
            problemes.append(Warning(
                "Le frontend est en HTTPS mais l'API est déclarée en HTTP "
                f"({base}). Les navigateurs bloquent ce contenu mixte : les "
                "appels directs du frontend vers l'API échoueraient.",
                hint="Activer HTTPS sur api.kharandi.gn puis passer "
                     "LENGOPAY_PUBLIC_BASE_URL à https://api.kharandi.gn.",
                id="kharandi.W019",
            ))

    return problemes
