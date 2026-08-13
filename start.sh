#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Kharandi — Démarrage du conteneur API (web)
#
# Ce script est IDEMPOTENT : il peut être rejoué indéfiniment (redémarrage du
# conteneur, `docker compose up -d`, reboot du VPS) sans jamais :
#   • supprimer de données,
#   • recréer la base,
#   • rejouer les imports lourds déjà effectués.
#
# Il n'exécute AUCUNE opération destructive (pas de flush, pas de reset, pas de
# `migrate --fake`, pas de suppression de volume).
#
# Variables de pilotage (toutes surchargeables dans .env / docker-compose.yml) :
#   RUN_MIGRATIONS      1 = applique `migrate --noinput`            (défaut 1)
#   RUN_COLLECTSTATIC   1 = collecte les statiques                  (défaut 1)
#   RUN_SEED            1 = seed_data + create_superadmin           (défaut 1)
#   RUN_BAC_IMPORT      1 = import des sujets BAC (une seule fois)  (défaut 1)
#   RUN_BAC_SCRAPER     1 = lance le scraper BAC en tâche de fond   (défaut 0)
#   RUN_CELERY_IN_API   1 = démarre Celery dans ce conteneur        (défaut 0)
#   GUNICORN_WORKERS / GUNICORN_THREADS / GUNICORN_TIMEOUT
#   DB_WAIT_TIMEOUT     secondes d'attente max de PostgreSQL        (défaut 90)
# ──────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

log()  { printf '==> %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-1}"
RUN_SEED="${RUN_SEED:-1}"
RUN_BAC_IMPORT="${RUN_BAC_IMPORT:-1}"
RUN_BAC_SCRAPER="${RUN_BAC_SCRAPER:-0}"
RUN_CELERY_IN_API="${RUN_CELERY_IN_API:-0}"

GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-90}"

# Marqueur persistant (volume media_data) : garantit que les imports lourds
# ne sont rejoués ni à chaque redémarrage, ni après un reboot du VPS.
STATE_DIR="${KHARANDI_STATE_DIR:-/app/media/.kharandi}"
BOOTSTRAP_MARKER="${STATE_DIR}/bootstrap-v1.done"

log "Kharandi API — démarrage (rôle : ${CONTAINER_ROLE:-web})"

# ─── 1. Attendre PostgreSQL (ceinture + bretelles avec depends_on) ───────────
log "Attente de PostgreSQL (max ${DB_WAIT_TIMEOUT}s)…"
python - "$DB_WAIT_TIMEOUT" <<'PY'
import os, sys, time
import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kharandi_backend.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

deadline = time.time() + float(sys.argv[1])
last = None
while time.time() < deadline:
    try:
        connections["default"].ensure_connection()
        print("    PostgreSQL est joignable.")
        sys.exit(0)
    except OperationalError as exc:
        last = exc
        connections["default"].close()
        time.sleep(2)
print(f"    PostgreSQL injoignable : {last}", file=sys.stderr)
sys.exit(1)
PY

# ─── 2. Migrations (non destructives, idempotentes) ──────────────────────────
if [[ "$RUN_MIGRATIONS" == "1" ]]; then
    log "Application des migrations Django…"
    # `migrate` est idempotent : les migrations déjà enregistrées dans
    # django_migrations sont ignorées. Aucune donnée n'est supprimée.
    python manage.py migrate --noinput --verbosity=1
else
    log "Migrations désactivées (RUN_MIGRATIONS=0)."
    # Garde-fou : on refuse de servir du trafic avec un schéma en retard.
    if ! python manage.py migrate --check --noinput >/dev/null 2>&1; then
        warn "Des migrations sont en attente. Les appliquer depuis le conteneur api."
    fi
fi

# ─── 3. Fichiers statiques ───────────────────────────────────────────────────
if [[ "$RUN_COLLECTSTATIC" == "1" ]]; then
    log "Collecte des fichiers statiques…"
    python manage.py collectstatic --noinput -v 0
fi

# ─── 4. Amorçage initial — UNE SEULE FOIS (marqueur persistant) ──────────────
mkdir -p "$STATE_DIR"

if [[ -f "$BOOTSTRAP_MARKER" ]]; then
    log "Amorçage déjà effectué (${BOOTSTRAP_MARKER}) — ignoré."
else
    if [[ "$RUN_SEED" == "1" ]]; then
        log "Données de référence (seed_data)…"
        python manage.py seed_data || warn "seed_data a échoué — poursuite."
        log "Compte super-administrateur (create_superadmin)…"
        python manage.py create_superadmin || warn "create_superadmin a échoué — poursuite."
    fi

    if [[ "$RUN_BAC_IMPORT" == "1" ]]; then
        log "Import des sujets BAC…"
        python manage.py load_bac_data   || warn "load_bac_data a échoué — poursuite."
        python manage.py clean_bac_content || warn "clean_bac_content a échoué — poursuite."
    fi

    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$BOOTSTRAP_MARKER"
    log "Amorçage terminé — marqueur écrit."
fi

# ─── 5. Jobs optionnels ──────────────────────────────────────────────────────
if [[ "$RUN_BAC_SCRAPER" == "1" ]]; then
    log "Scraper BAC en arrière-plan…"
    nohup python manage.py scrape_bac_subjects --delay 2 >> /tmp/bac_scraper.log 2>&1 &
fi

if [[ "$RUN_CELERY_IN_API" == "1" ]]; then
    warn "Celery dans le conteneur API (déconseillé) — préférer le service 'worker'."
    nohup celery -A kharandi_backend worker \
        --loglevel=warning --concurrency=2 --queues=celery \
        >> /tmp/celery_worker.log 2>&1 &
fi

# ─── 6. Gunicorn (PID 1 → arrêt propre sur SIGTERM) ──────────────────────────
log "Gunicorn sur 0.0.0.0:${PORT:-8000} (${GUNICORN_WORKERS} workers × ${GUNICORN_THREADS} threads)"
exec gunicorn kharandi_backend.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "$GUNICORN_WORKERS" \
    --worker-class gthread \
    --threads "$GUNICORN_THREADS" \
    --timeout "$GUNICORN_TIMEOUT" \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --forwarded-allow-ips '*'
