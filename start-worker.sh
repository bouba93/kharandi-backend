#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Kharandi — Démarrage du worker Celery (service `worker`)
#
# Le worker n'applique JAMAIS de migration et ne collecte pas les statiques :
# le conteneur `api` est la seule source de vérité pour le schéma de base.
# ──────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

log() { printf '==> %s\n' "$*"; }

CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-4}"
CELERY_LOGLEVEL="${CELERY_LOGLEVEL:-warning}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-90}"

log "Worker Celery — attente de PostgreSQL (max ${DB_WAIT_TIMEOUT}s)…"
python - "$DB_WAIT_TIMEOUT" <<'PY'
import os, sys, time
import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kharandi_backend.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

deadline = time.time() + float(sys.argv[1])
while time.time() < deadline:
    try:
        connections["default"].ensure_connection()
        sys.exit(0)
    except OperationalError:
        connections["default"].close()
        time.sleep(2)
sys.exit(1)
PY

log "Démarrage du worker (concurrency=${CELERY_CONCURRENCY})"
exec celery -A kharandi_backend worker \
    --loglevel="$CELERY_LOGLEVEL" \
    --concurrency="$CELERY_CONCURRENCY" \
    --queues=celery \
    --without-gossip \
    --without-mingle
