#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# deploy-yigui.sh — Déploiement du backend Kharandi sur le VPS YIGUI
#
# À LANCER DEPUIS VOTRE MACHINE LOCALE, à la racine du projet backend :
#   bash deploy/deploy-yigui.sh
#
# Envoie le code par rsync/SSH, construit les images et redémarre la stack.
# Idempotent : relançable à chaque mise à jour du code.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-212.95.33.158}"
VPS_USER="${VPS_USER:-root}"
APP_DIR="${APP_DIR:-/opt/kharandi}"
SSH="ssh -o StrictHostKeyChecking=accept-new ${VPS_USER}@${VPS_HOST}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[X]${NC} $*" >&2; exit 1; }

[[ -f manage.py ]] || die "Lancez ce script à la racine du backend (manage.py introuvable)."

# ─── 1. Connectivité ──────────────────────────────────────────────────────────
log "Test de la connexion SSH vers ${VPS_USER}@${VPS_HOST}"
$SSH "echo ok" >/dev/null || die "Connexion SSH impossible. Vérifiez votre clé ou le mot de passe."

log "Vérification de Docker sur le serveur"
$SSH "command -v docker >/dev/null && docker compose version >/dev/null" \
    || die "Docker absent. Lancez d'abord deploy/bootstrap-yigui.sh sur le serveur."

# ─── 2. Envoi du code ─────────────────────────────────────────────────────────
log "Envoi du code vers ${APP_DIR}"
$SSH "mkdir -p ${APP_DIR}"
rsync -az --delete \
    --exclude '.git' \
    --exclude '.env' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'venv' \
    --exclude 'staticfiles' \
    --exclude 'media' \
    --exclude 'db.sqlite3' \
    --exclude 'node_modules' \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    ./ "${VPS_USER}@${VPS_HOST}:${APP_DIR}/"

# ─── 3. Fichier .env ──────────────────────────────────────────────────────────
if $SSH "[ -f ${APP_DIR}/.env ]"; then
    log "Fichier .env déjà présent sur le serveur (conservé)"
else
    warn "Aucun .env sur le serveur — création à partir de .env.yigui.example"
    $SSH "cp ${APP_DIR}/.env.yigui.example ${APP_DIR}/.env && chmod 600 ${APP_DIR}/.env"
    echo
    warn "ACTION REQUISE — remplissez les secrets avant de continuer :"
    echo "    ssh ${VPS_USER}@${VPS_HOST}"
    echo "    nano ${APP_DIR}/.env"
    echo "    bash deploy/deploy-yigui.sh   # relancez ensuite"
    exit 1
fi

log "Contrôle des variables obligatoires"
$SSH "grep -q 'À_REMPLIR' ${APP_DIR}/.env" \
    && die "Le fichier .env contient encore des valeurs « À_REMPLIR ». Complétez-le puis relancez."

# ─── 4. Build & démarrage ─────────────────────────────────────────────────────
log "Construction des images Docker (peut prendre quelques minutes)"
$SSH "cd ${APP_DIR} && docker compose build --pull"

log "Validation de la composition"
$SSH "cd ${APP_DIR} && docker compose config >/dev/null" || die "docker-compose.yml invalide."

log "Démarrage de la stack (db, redis, api, worker, nginx)"
$SSH "cd ${APP_DIR} && docker compose up -d --remove-orphans"

log "Vérification de la configuration Nginx"
sleep 3
$SSH "cd ${APP_DIR} && docker compose exec -T nginx nginx -t" >/dev/null 2>&1 \
    || die "Configuration Nginx invalide. Voir : docker compose logs --tail=50 nginx"

log "Nettoyage des images inutilisées"
$SSH "docker image prune -f >/dev/null" || true

# ─── 5. Vérification de santé ─────────────────────────────────────────────────
log "Attente du démarrage de l'API (migrations + collectstatic)"
for i in $(seq 1 40); do
    if $SSH "curl -fsS http://127.0.0.1/healthz" >/dev/null 2>&1; then
        echo
        log "API en ligne."
        $SSH "curl -s http://127.0.0.1/healthz"; echo
        $SSH "curl -s http://127.0.0.1/readyz";  echo
        echo
        echo "  API        : http://${VPS_HOST}/"
        echo "  Santé      : http://${VPS_HOST}/healthz"
        echo "  Readiness  : http://${VPS_HOST}/readyz"
        echo "  Docs API   : http://${VPS_HOST}/api/docs/"
        echo "  Admin      : http://${VPS_HOST}/admin/"
        echo
        echo "Côté frontend, définissez :"
        echo "  VITE_API_URL=http://${VPS_HOST}/api/v1"
        exit 0
    fi
    printf '.'
    sleep 6
done

echo
die "L'API n'a pas répondu à temps. Diagnostiquez avec :
    ssh ${VPS_USER}@${VPS_HOST} 'cd ${APP_DIR} && docker compose logs --tail=120 api'"
