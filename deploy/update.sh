#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# update.sh — Mise à jour EN PLACE du backend Kharandi (stack déjà en prod)
#
# À exécuter SUR LE VPS, dans /opt/kharandi :
#   cd /opt/kharandi && bash deploy/update.sh
#
# Ce script est NON DESTRUCTIF :
#   • sauvegarde PostgreSQL + configuration avant toute action
#   • ne supprime aucun volume (jamais de `down -v`)
#   • ne recrée pas la base, ne réinitialise aucune migration
#   • restaure automatiquement la configuration si Nginx refuse de démarrer
# ══════════════════════════════════════════════════════════════════════════════
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-/opt/kharandi-backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[X]${NC} $*" >&2; exit 1; }

cd "$APP_DIR"
[[ -f manage.py && -f docker-compose.yml ]] || die "Lancez ce script depuis /opt/kharandi."
[[ -f .env ]] || die "Fichier .env absent. Voir deploy/make-env.sh."

mkdir -p "$BACKUP_DIR"

# ─── 1. Sauvegarde base de données ───────────────────────────────────────────
log "Sauvegarde PostgreSQL"
DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo kharandi_user)"
DB_NAME="$(grep -E '^POSTGRES_DB='   .env | cut -d= -f2- || echo kharandi_db)"
if docker compose ps --status running --services 2>/dev/null | grep -qx db; then
    docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" \
        | gzip > "${BACKUP_DIR}/db_avant_update_${STAMP}.sql.gz"
    log "  → ${BACKUP_DIR}/db_avant_update_${STAMP}.sql.gz"
else
    warn "  Conteneur db non démarré — sauvegarde ignorée."
fi

# ─── 2. Sauvegarde de la configuration ───────────────────────────────────────
log "Sauvegarde de la configuration"
CFG_BAK="${BACKUP_DIR}/config_${STAMP}"
mkdir -p "$CFG_BAK"
cp -a docker-compose.yml start.sh nginx .env "$CFG_BAK"/ 2>/dev/null || true
log "  → ${CFG_BAK}"

# ─── 3. Contrôles avant démarrage ────────────────────────────────────────────
log "Validation de docker-compose.yml"
docker compose config >/dev/null || die "docker-compose.yml invalide. Rien n'a été modifié."

if grep -qE 'À_REMPLIR|À_GÉNÉRER' .env; then
    warn "Valeurs non renseignées dans .env :"
    grep -nE 'À_REMPLIR|À_GÉNÉRER' .env >&2
    die "Complétez ces valeurs avant de déployer (voir PREPARATION_PRODUCTION.md § 7)."
fi

# ─── 4. Construction et démarrage ────────────────────────────────────────────
log "Construction des images (quelques minutes au premier passage)"
docker compose build --pull

log "Démarrage de la stack (aucun volume supprimé)"
docker compose up -d --remove-orphans

# ─── 5. Vérification Nginx, avec restauration automatique ────────────────────
log "Vérification de la configuration Nginx"
sleep 3
if ! docker compose exec -T nginx nginx -t >/dev/null 2>&1; then
    warn "Nginx refuse la configuration — restauration de la précédente."
    cp -a "${CFG_BAK}/nginx/." nginx/
    cp -a "${CFG_BAK}/docker-compose.yml" docker-compose.yml
    docker compose up -d nginx
    die "Configuration restaurée. Détails : docker compose logs --tail=50 nginx"
fi

# ─── 6. Sondes de santé ──────────────────────────────────────────────────────
log "Attente du démarrage de l'API (migrations + collectstatic)"
OK=0
for _ in $(seq 1 50); do
    if docker compose exec -T nginx wget -qO- http://127.0.0.1/healthz >/dev/null 2>&1; then
        OK=1; break
    fi
    printf '.'
    sleep 6
done
echo

[[ "$OK" -eq 1 ]] || die "L'API n'a pas répondu à temps. Diagnostic :
    docker compose ps
    docker compose logs --tail=120 api
    docker compose logs --tail=60 nginx
Rollback : cp -a ${CFG_BAK}/nginx/. nginx/ && cp ${CFG_BAK}/docker-compose.yml . && docker compose up -d"

log "Sondes de santé"
echo -n "  nginx (liveness)  : "; docker compose exec -T nginx wget -qO- http://127.0.0.1:8081/nginx-health || true
echo -n "  django (liveness) : "; docker compose exec -T nginx wget -qO- http://127.0.0.1/healthz; echo
echo -n "  readiness         : "; docker compose exec -T nginx wget -qO- http://127.0.0.1/readyz; echo

# ─── 6 bis. Celery Beat ───────────────────────────────────────────────────
log "Vérification du planificateur (Celery Beat)"
if docker compose ps --status running --services 2>/dev/null | grep -qx beat; then
    echo "  Conteneur beat : en cours d'exécution."
else
    warn "  Conteneur beat ARRÊTÉ. La réconciliation des paiements ne tourne"
    warn "  pas : un callback LengoPay perdu ne serait jamais rattrapé."
    warn "  Diagnostic : docker compose logs --tail=60 beat"
fi

# Le battement de cœur prouve la chaîne complète Beat → Redis → Worker.
# Beat émet la tâche chaque minute : on laisse jusqu'à 100 s.
log "Attente du premier battement du planificateur (jusqu'à 100 s)"
BEAT_OK=0
for _ in $(seq 1 20); do
    if docker compose exec -T api python -c "
import sys
from django.core.cache import cache
sys.exit(0 if cache.get('kharandi:beat:heartbeat') else 1)
" >/dev/null 2>&1; then
        BEAT_OK=1; break
    fi
    printf '.'
    sleep 5
done
echo
if [[ "$BEAT_OK" -eq 1 ]]; then
    echo "  Chaîne Beat → Redis → Worker opérationnelle."
else
    warn "  Aucun battement reçu. Vérifier que beat ET worker tournent :"
    warn "    docker compose ps beat worker"
    warn "    docker compose exec api python manage.py lengopay_doctor"
fi

log "Contrôle du schéma de base"
docker compose exec -T api python manage.py migrate --check >/dev/null 2>&1 \
    && echo "  Schéma à jour." \
    || warn "  Des migrations restent en attente."

log "Nettoyage des images orphelines"
docker image prune -f >/dev/null || true

echo
docker compose ps
echo
log "Mise à jour terminée."
echo "  API      : http://212.95.33.158/"
echo "  Santé    : http://212.95.33.158/healthz"
echo "  Readiness: http://212.95.33.158/readyz"
echo "  Docs     : http://212.95.33.158/api/docs/"
echo "  Admin    : http://212.95.33.158/admin/"
echo
echo "  Diagnostic paiements : docker compose exec api python manage.py lengopay_doctor"
echo
echo "  Sauvegardes de cette mise à jour :"
echo "    ${BACKUP_DIR}/db_avant_update_${STAMP}.sql.gz"
echo "    ${CFG_BAK}"
