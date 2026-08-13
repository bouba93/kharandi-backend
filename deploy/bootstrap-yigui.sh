#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# bootstrap-yigui.sh — Préparation initiale du VPS YIGUI (à lancer UNE SEULE FOIS)
#
# À exécuter EN TANT QUE ROOT SUR LE SERVEUR :
#   ssh root@212.95.33.158
#   bash bootstrap-yigui.sh
#
# Installe : Docker + Docker Compose, pare-feu UFW, fail2ban, swap, dossiers.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="/opt/kharandi"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[X]${NC} $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Ce script doit être lancé en root."

log "Mise à jour du système"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

log "Installation des outils de base"
apt-get install -y -qq ca-certificates curl gnupg git ufw fail2ban htop nano rsync

# ─── Docker ───────────────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    log "Docker déjà installé ($(docker --version))"
else
    log "Installation de Docker Engine + Compose v2"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
fi

docker compose version >/dev/null 2>&1 || die "Docker Compose v2 indisponible."

# ─── Swap (utile si le VPS a peu de RAM) ──────────────────────────────────────
if ! swapon --show | grep -q .; then
    log "Création d'un swap de 2 Go"
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
else
    log "Swap déjà actif"
fi

# ─── Pare-feu ─────────────────────────────────────────────────────────────────
log "Configuration du pare-feu UFW (22, 80, 443)"
ufw --force reset >/dev/null
ufw default deny incoming  >/dev/null
ufw default allow outgoing >/dev/null
ufw allow 22/tcp  comment 'SSH'   >/dev/null
ufw allow 80/tcp  comment 'HTTP'  >/dev/null
ufw allow 443/tcp comment 'HTTPS' >/dev/null
ufw --force enable >/dev/null
warn "PostgreSQL et Redis ne sont PAS exposés : ils restent sur le réseau Docker interne."

log "Activation de fail2ban (protection SSH)"
systemctl enable --now fail2ban

# ─── Rotation des logs Docker ─────────────────────────────────────────────────
log "Limitation de la taille des logs Docker"
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
JSON
systemctl restart docker

# ─── Arborescence applicative ────────────────────────────────────────────────
log "Création de $APP_DIR"
mkdir -p "$APP_DIR" /opt/kharandi-backups

echo
log "VPS YIGUI prêt."
echo "   Docker  : $(docker --version)"
echo "   Compose : $(docker compose version --short)"
echo
echo "Étape suivante — depuis votre machine locale :"
echo "   bash deploy/deploy-yigui.sh"
