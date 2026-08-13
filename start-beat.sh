#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Kharandi — Démarrage de Celery Beat (service `beat`)
#
# Beat est le PLANIFICATEUR : il n'exécute aucune tâche lui-même, il les émet
# vers Redis, où le worker les consomme. C'est lui qui déclenche la
# réconciliation des paiements LengoPay — sans lui, un callback perdu signifie
# un client qui a payé sans rien recevoir.
#
# RÈGLE ABSOLUE : un seul conteneur `beat` à la fois. Deux planificateurs
# émettraient chaque tâche en double.
#
# Beat n'applique JAMAIS de migration et ne collecte pas les statiques :
# le conteneur `api` est la seule source de vérité pour le schéma de base.
# ──────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

log() { printf '==> %s\n' "$*"; }

CELERY_LOGLEVEL="${CELERY_LOGLEVEL:-info}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-90}"
BEAT_STATE_DIR="${BEAT_STATE_DIR:-/app/beat}"
BEAT_SCHEDULE_FILE="${BEAT_SCHEDULE_FILE:-${BEAT_STATE_DIR}/celerybeat-schedule}"
BEAT_PID_FILE="${BEAT_STATE_DIR}/celerybeat.pid"

mkdir -p "$BEAT_STATE_DIR"

# Un arrêt brutal (kill -9, OOM, coupure de courant) laisse un fichier PID
# périmé qui empêche Beat de redémarrer. Le conteneur étant seul à utiliser ce
# volume, tout PID trouvé au démarrage est forcément obsolète.
if [ -f "$BEAT_PID_FILE" ]; then
    log "Fichier PID résiduel détecté — suppression (redémarrage après arrêt brutal)."
    rm -f "$BEAT_PID_FILE"
fi

log "Celery Beat — attente de PostgreSQL (max ${DB_WAIT_TIMEOUT}s)…"
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

log "Attente de Redis (le courtier de messages)…"
python - <<'PY'
import os, sys, time
import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kharandi_backend.settings")
django.setup()

from kharandi_backend.celery import app

deadline = time.time() + 60
while time.time() < deadline:
    try:
        conn = app.connection()
        conn.ensure_connection(max_retries=0)
        conn.release()
        sys.exit(0)
    except Exception:
        time.sleep(2)
print("Redis injoignable après 60 s — Beat démarre quand même et retentera.")
sys.exit(0)
PY

# Récapitulatif du planning : visible dans `docker compose logs beat`, ce qui
# évite d'avoir à deviner ce qui est réellement planifié en production.
python - <<'PY'
import os, sys
import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kharandi_backend.settings")
django.setup()

from django.conf import settings

print("==> Tâches planifiées :")
for nom, conf in sorted(settings.CELERY_BEAT_SCHEDULE.items()):
    secondes = conf.get("schedule")
    if isinstance(secondes, (int, float)):
        cadence = (
            f"toutes les {int(secondes)} s" if secondes < 120
            else f"toutes les {int(secondes // 60)} min"
        )
    else:
        cadence = str(secondes)
    print(f"      {nom:<32} {conf['task']:<38} {cadence}")
PY

log "Démarrage de Celery Beat (état : ${BEAT_SCHEDULE_FILE})"
exec celery -A kharandi_backend beat \
    --loglevel="$CELERY_LOGLEVEL" \
    --schedule="$BEAT_SCHEDULE_FILE" \
    --pidfile="$BEAT_PID_FILE"
