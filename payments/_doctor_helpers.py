"""
payments/_doctor_helpers.py — Contrôles utilisés par `manage.py lengopay_doctor`
───────────────────────────────────────────────────────────────────────────────
Chaque fonction renvoie une liste de couples (niveau, message) où `niveau` vaut
« ok », « warn », « ko » ou « info ». Aucun effet de bord, aucune écriture.
"""
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone


def masque(valeur, garde: int = 4) -> str:
    """Affiche un secret sans le révéler."""
    valeur = str(valeur or "")
    if not valeur:
        return "(vide)"
    if len(valeur) <= garde * 2:
        return "*" * len(valeur)
    return f"{valeur[:garde]}…{valeur[-garde:]} ({len(valeur)} car.)"


def verifier_configuration():
    resultats = []

    if settings.LENGOPAY_SITE_ID:
        resultats.append(("ok", f"LENGOPAY_SITE_ID = {settings.LENGOPAY_SITE_ID}"))
    else:
        resultats.append(("ko", "LENGOPAY_SITE_ID est vide : aucun paiement ne peut être créé."))

    if settings.LENGOPAY_LICENSE_KEY:
        resultats.append(("ok", f"LENGOPAY_LICENSE_KEY = {masque(settings.LENGOPAY_LICENSE_KEY)}"))
    else:
        resultats.append(("ko", "LENGOPAY_LICENSE_KEY est vide : l'API refusera toute requête (401)."))

    resultats.append(("info", f"Création  : POST {settings.LENGOPAY_PAYMENT_URL}"))
    resultats.append(("info", f"Statut    : POST {settings.LENGOPAY_STATUS_URL}"))

    if "{pay_id}" in str(settings.LENGOPAY_STATUS_URL):
        resultats.append((
            "ko",
            "LENGOPAY_STATUS_URL contient encore l'ancien gabarit {pay_id} : "
            "cet endpoint n'existe pas. Utiliser "
            f"{settings.LENGOPAY_BASE_URL}/transaction/status",
        ))

    callback = str(settings.LENGOPAY_CALLBACK_URL or "")
    resultats.append(("info", f"Callback  : POST {callback}"))

    parsed = urlparse(callback)
    if not parsed.scheme or not parsed.netloc:
        resultats.append(("ko", "LENGOPAY_CALLBACK_URL est invalide ou vide."))
    else:
        if "/api/v1/payments/webhook" not in parsed.path:
            resultats.append((
                "ko",
                "LENGOPAY_CALLBACK_URL ne pointe pas vers /api/v1/payments/webhook/.",
            ))
        if not parsed.path.endswith("/"):
            resultats.append((
                "warn",
                "L'URL de callback ne se termine pas par « / ». Les routes sans "
                "slash sont gérées, mais mieux vaut conserver le slash final.",
            ))
        if parsed.scheme == "http":
            resultats.append((
                "warn",
                "Callback en HTTP (non chiffré). Acceptable tant qu'aucun "
                "sous-domaine n'est disponible, mais le jeton circule en clair : "
                "passer en HTTPS dès que possible.",
            ))
        hote = parsed.hostname or ""
        if hote and hote not in settings.ALLOWED_HOSTS:
            resultats.append((
                "ko",
                f"L'hôte « {hote} » de l'URL de callback n'est pas dans "
                "ALLOWED_HOSTS : Django répondrait 400 DisallowedHost.",
            ))
        elif hote:
            resultats.append(("ok", f"L'hôte « {hote} » est bien dans ALLOWED_HOSTS."))

    if settings.LENGOPAY_CALLBACK_TOKEN:
        if settings.LENGOPAY_CALLBACK_TOKEN in callback:
            resultats.append((
                "ok",
                f"Jeton de callback présent dans l'URL : "
                f"{masque(settings.LENGOPAY_CALLBACK_TOKEN)}",
            ))
        else:
            resultats.append((
                "ko",
                "LENGOPAY_CALLBACK_TOKEN est défini mais absent de "
                "LENGOPAY_CALLBACK_URL : les callbacks arriveront non authentifiés.",
            ))
        if len(settings.LENGOPAY_CALLBACK_TOKEN) < 24:
            resultats.append((
                "warn",
                "Jeton de callback court (< 24 caractères). Régénérer avec "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\".",
            ))
    else:
        resultats.append((
            "warn",
            "LENGOPAY_CALLBACK_TOKEN est vide : les callbacks ne pourront être "
            "appliqués que si l'API de vérification de statut répond.",
        ))

    if settings.LENGOPAY_REQUIRE_STATUS_CONFIRMATION:
        resultats.append((
            "ok",
            "Confirmation serveur OBLIGATOIRE : un callback « SUCCESS » ne "
            "valide un paiement que si l'API LengoPay le confirme. Une "
            "indisponibilité de l'API laisse le paiement en attente jusqu'au "
            "passage de la réconciliation (voir section Celery Beat).",
        ))
    else:
        resultats.append((
            "ok",
            "Callback authentifié appliqué même si l'API de statut est muette "
            "(contrôle du montant conservé).",
        ))

    if not settings.CRON_SECRET:
        resultats.append((
            "warn",
            "CRON_SECRET est vide : la réconciliation ne peut pas être "
            "déclenchée via /api/v1/payments/run-cron/.",
        ))

    return resultats


def verifier_endpoint_statut():
    """Appel réel (inoffensif) de l'endpoint de statut avec un pay_id factice."""
    import requests

    resultats = []
    url = str(settings.LENGOPAY_STATUS_URL or "")
    if not url or "{pay_id}" in url:
        url = f"{settings.LENGOPAY_BASE_URL}/transaction/status"

    entetes = {
        "Authorization": f"Basic {settings.LENGOPAY_LICENSE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    corps = {"pay_id": "diagnostic-kharandi", "websiteid": settings.LENGOPAY_SITE_ID}

    try:
        reponse = requests.post(url, json=corps, headers=entetes, timeout=15)
    except requests.RequestException as exc:
        resultats.append((
            "ko",
            f"{url} injoignable depuis le conteneur : {exc}. Vérifier la "
            "résolution DNS et la sortie Internet du conteneur api.",
        ))
        return resultats

    resultats.append(("info", f"HTTP {reponse.status_code} — {reponse.text[:200]}"))
    if reponse.status_code in (200, 400, 404):
        resultats.append((
            "ok",
            "L'endpoint répond : la vérification serveur-à-serveur est "
            "opérationnelle (un pay_id factice est légitimement rejeté).",
        ))
    elif reponse.status_code == 401:
        resultats.append((
            "ko",
            "HTTP 401 : clé de licence invalide ou mal formée. Vérifier "
            "LENGOPAY_LICENSE_KEY (elle est utilisée telle quelle après « Basic »).",
        ))
    elif reponse.status_code == 405:
        resultats.append((
            "ko",
            "HTTP 405 : méthode refusée. L'URL de statut est probablement "
            "erronée ; la documentation attend un POST sur /transaction/status.",
        ))
    else:
        resultats.append((
            "warn",
            f"Réponse inattendue (HTTP {reponse.status_code}). "
            "La confirmation de statut risque de ne pas fonctionner.",
        ))
    return resultats


def resumer_callbacks(heures: int = 48):
    from django.db import DatabaseError

    from .models import PaymentCallback

    resultats = []
    depuis = timezone.now() - timedelta(hours=heures)
    qs = PaymentCallback.objects.filter(created_at__gte=depuis)
    try:
        total = qs.count()
    except DatabaseError as exc:
        # Typiquement : migration 0003_paymentcallback non appliquée. Un outil
        # de diagnostic ne doit jamais s'interrompre sur une trace d'erreur.
        return [(
            "ko",
            f"Journal des callbacks inaccessible ({exc}). Appliquer les "
            "migrations : docker compose exec api python manage.py migrate",
        )]

    if total == 0:
        resultats.append((
            "warn",
            f"Aucun callback reçu depuis {heures} h. Si des paiements ont été "
            "effectués, LengoPay n'atteint pas le serveur : vérifier l'URL "
            "enregistrée côté LengoPay, le pare-feu et l'accès au port 80.",
        ))
        return resultats

    resultats.append(("ok", f"{total} callback(s) reçu(s) depuis {heures} h."))
    for choix in PaymentCallback.Outcome:
        n = qs.filter(outcome=choix.value).count()
        if not n:
            continue
        niveau = "ok" if choix.value in {"APPLIED", "DUPLICATE", "PENDING"} else "warn"
        resultats.append((niveau, f"{choix.label} : {n}"))

    for cb in qs.exclude(outcome=PaymentCallback.Outcome.APPLIED).order_by("-created_at")[:5]:
        resultats.append((
            "info",
            f"{cb.created_at:%Y-%m-%d %H:%M} | {cb.pay_id} | {cb.outcome} | "
            f"auth={cb.auth_method or 'aucune'} | {cb.detail[:120]}",
        ))
    return resultats


def resumer_transactions(heures: int = 48):
    from django.db import DatabaseError

    from .models import Transaction

    resultats = []
    depuis = timezone.now() - timedelta(hours=heures)
    qs = Transaction.objects.filter(created_at__gte=depuis)

    try:
        nombre = qs.count()
    except DatabaseError as exc:
        return [(
            "ko",
            f"Table des transactions inaccessible ({exc}). Appliquer les "
            "migrations : docker compose exec api python manage.py migrate",
        )]

    resultats.append(("info", f"{nombre} transaction(s) créée(s) depuis {heures} h."))
    for statut in Transaction.Status:
        n = qs.filter(status=statut.value).count()
        if n:
            resultats.append(("info", f"{statut.label} : {n}"))

    bloquees = qs.filter(
        status=Transaction.Status.PENDING,
        created_at__lt=timezone.now() - timedelta(minutes=30),
    ).exclude(gateway_ref="")
    n = bloquees.count()
    if n:
        resultats.append((
            "warn",
            f"{n} transaction(s) en attente depuis plus de 30 minutes. "
            "Lancer : python manage.py lengopay_doctor --reconcile",
        ))
        for tx in bloquees[:5]:
            resultats.append((
                "info",
                f"{tx.reference} | pay_id={tx.gateway_ref} | "
                f"{tx.amount} {tx.currency} | {tx.created_at:%Y-%m-%d %H:%M}",
            ))
    else:
        resultats.append(("ok", "Aucune transaction bloquée en attente."))

    sans_ref = qs.filter(gateway_ref="").count()
    if sans_ref:
        resultats.append((
            "warn",
            f"{sans_ref} transaction(s) sans gateway_ref : la création du "
            "paiement chez LengoPay a échoué (voir les journaux).",
        ))
    return resultats


def verifier_planificateur():
    """
    Vérifie que Celery Beat tourne réellement et que la réconciliation est
    planifiée.

    C'est le contrôle le plus utile de tout ce diagnostic : en mode
    confirmation obligatoire, un Beat à l'arrêt signifie que les paiements dont
    le callback n'a pas pu être confirmé ne seront JAMAIS validés. Et un Beat
    arrêté ne provoque aucune erreur visible côté API.
    """
    from django.conf import settings
    from django.core.cache import cache
    from django.utils import timezone

    lignes = []
    planning = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}

    if not planning:
        lignes.append(("ko", "CELERY_BEAT_SCHEDULE est vide : aucune tâche planifiée."))
        return lignes

    taches = {c.get("task") for c in planning.values()}
    if "payments.reconcile_lengopay" in taches:
        entree = next(
            c for c in planning.values() if c.get("task") == "payments.reconcile_lengopay"
        )
        cadence = entree.get("schedule")
        if isinstance(cadence, (int, float)):
            lignes.append(("ok", f"Réconciliation planifiée toutes les {int(cadence // 60)} min."))
        else:
            lignes.append(("ok", f"Réconciliation planifiée : {cadence}"))
    else:
        lignes.append(("ko", "La tâche payments.reconcile_lengopay n'est PAS planifiée."))

    lignes.append(("info", f"{len(planning)} tâche(s) planifiée(s) : "
                           + ", ".join(sorted(planning.keys()))))

    # Vérification que les noms planifiés correspondent à des tâches réelles.
    try:
        from kharandi_backend.celery import app
        app.loader.import_default_modules()
        enregistrees = set(app.tasks.keys())
        manquantes = sorted(t for t in taches if t and t not in enregistrees)
        if manquantes:
            lignes.append(("ko", "Tâches planifiées introuvables (Beat émet dans "
                                 f"le vide) : {', '.join(manquantes)}"))
        else:
            lignes.append(("ok", "Toutes les tâches planifiées existent bien."))
    except Exception as exc:
        lignes.append(("warn", f"Impossible de valider les noms de tâches : {exc}"))

    # Battement de cœur : prouve la chaîne Beat → Redis → Worker.
    try:
        battement = cache.get("kharandi:beat:heartbeat")
    except Exception as exc:
        lignes.append(("ko", f"Cache Redis injoignable : {exc}"))
        return lignes

    if not battement:
        lignes.append(("ko",
            "Aucun battement de Celery Beat détecté. Soit Beat est arrêté, "
            "soit le worker ne consomme plus la file. En mode confirmation "
            "obligatoire, les paiements non confirmés resteraient bloqués. "
            "Vérifier : docker compose ps beat && docker compose logs --tail=50 beat"))
        return lignes

    try:
        from datetime import datetime
        horodatage = datetime.fromisoformat(str(battement))
        age = (timezone.now() - horodatage).total_seconds()
        if age < 180:
            lignes.append(("ok", f"Celery Beat actif (dernier battement il y a {int(age)} s)."))
        else:
            lignes.append(("warn",
                f"Dernier battement de Beat il y a {int(age)} s — attendu moins "
                "de 60 s. Beat ou le worker est peut-être bloqué."))
    except Exception:
        lignes.append(("info", f"Dernier battement : {battement}"))

    return lignes


def verifier_securite():
    """Reprend les contrôles système Django et les affiche dans le diagnostic."""
    from django.core.checks import Error

    try:
        from core.checks import verifier_configuration_production
        problemes = verifier_configuration_production(None)
    except Exception as exc:
        return [("warn", f"Contrôles de configuration indisponibles : {exc}")]

    if not problemes:
        return [("ok", "Aucun problème de configuration détecté.")]

    lignes = []
    for probleme in problemes:
        niveau = "ko" if isinstance(probleme, Error) else "warn"
        lignes.append((niveau, f"[{probleme.id}] {probleme.msg}"))
    return lignes
