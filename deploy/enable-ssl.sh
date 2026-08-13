#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# enable-ssl.sh — Active HTTPS (Let's Encrypt) sur le VPS YIGUI
#
# Prérequis : un domaine (ex. api.kharandi.gn) doit pointer en A vers 212.95.33.158
#
# À exécuter SUR LE SERVEUR, dans /opt/kharandi :
#   bash deploy/enable-ssl.sh api.kharandi.gn admin@kharandi.gn
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}==>${NC} $*"; }
die() { echo -e "${RED}[X]${NC} $*" >&2; exit 1; }

[[ -n "$DOMAIN" && -n "$EMAIL" ]] || die "Usage : bash deploy/enable-ssl.sh <domaine> <email>"
cd "$APP_DIR"

log "Vérification DNS : $DOMAIN"
RESOLVED="$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)"
[[ -n "$RESOLVED" ]] || die "Le domaine $DOMAIN ne résout pas. Créez l'enregistrement A vers 212.95.33.158."
log "  → $RESOLVED"

log "Obtention du certificat Let's Encrypt"
docker compose run --rm --entrypoint "certbot" certbot certonly \
    --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos --no-eff-email --non-interactive \
    || die "Échec Certbot. Vérifiez que le port 80 est ouvert et que Nginx tourne."

log "Activation de la configuration HTTPS"
cp nginx/kharandi.conf "nginx/kharandi.conf.http.bak"
sed "s/__DOMAIN__/${DOMAIN}/g" nginx/kharandi-ssl.conf.template > nginx/kharandi.conf

log "Ajout du domaine aux hôtes autorisés Django et activation du mode HTTPS"
grep -q "$DOMAIN" .env || sed -i "s|^ALLOWED_HOSTS=.*|&,${DOMAIN}|" .env
grep -q "https://${DOMAIN}" .env || sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|&,https://${DOMAIN}|" .env
if grep -q '^ENABLE_HTTPS=' .env; then
    sed -i 's|^ENABLE_HTTPS=.*|ENABLE_HTTPS=True|' .env
else
    echo 'ENABLE_HTTPS=True' >> .env
fi

# ── Bascule de l'URL de callback LengoPay vers HTTPS ─────────────────────────
# Point critique : tant que LENGOPAY_PUBLIC_BASE_URL reste en http://<IP>, le
# jeton de callback circule en clair et le frontend HTTPS ne peut pas appeler
# l'API (contenu mixte bloqué par les navigateurs). On sauvegarde l'ancienne
# valeur pour permettre un retour arrière.
ANCIENNE_BASE="$(grep -E '^LENGOPAY_PUBLIC_BASE_URL=' .env | cut -d= -f2- || true)"
if grep -q '^LENGOPAY_PUBLIC_BASE_URL=' .env; then
    sed -i "s|^LENGOPAY_PUBLIC_BASE_URL=.*|LENGOPAY_PUBLIC_BASE_URL=https://${DOMAIN}|" .env
else
    echo "LENGOPAY_PUBLIC_BASE_URL=https://${DOMAIN}" >> .env
fi
log "LENGOPAY_PUBLIC_BASE_URL : ${ANCIENNE_BASE:-(absent)} → https://${DOMAIN}"

# FRONTEND_URL et CORS restent inchangés : le frontend est sur kharandi.gn
# (Vercel), pas sur ce domaine d'API.

log "Vérification de la configuration Nginx avant rechargement"
docker compose exec -T nginx nginx -t || die "Configuration Nginx invalide. Restaurez avec :
    cp nginx/kharandi.conf.http.bak nginx/kharandi.conf && docker compose restart nginx"

# api, worker ET beat doivent être redémarrés : tous les trois lisent
# LENGOPAY_PUBLIC_BASE_URL, et c'est beat qui pilote la réconciliation.
log "Redémarrage de Nginx, de l'API, du worker et du planificateur"
docker compose restart nginx api worker beat

sleep 8
if curl -fsS "https://${DOMAIN}/healthz" >/dev/null 2>&1; then
    log "HTTPS actif : https://${DOMAIN}/"
    echo "  Côté frontend : VITE_API_URL=https://${DOMAIN}/api/v1"
    echo "  Le renouvellement du certificat est automatique (conteneur certbot, toutes les 12 h)."
    echo
    log "NOUVELLE URL DE CALLBACK à déclarer dans le portail LengoPay :"
    docker compose exec -T api python manage.py lengopay_doctor 2>/dev/null \
        | tail -4 || echo "  https://${DOMAIN}/api/v1/payments/webhook/<TOKEN>/"
    echo
    echo "  ⚠ L'ancienne URL en http://212.95.33.158/… doit être remplacée chez"
    echo "    LengoPay, sinon les callbacks continueront d'arriver en clair."
else
    die "HTTPS ne répond pas. Restaurez avec :
    cp nginx/kharandi.conf.http.bak nginx/kharandi.conf && docker compose restart nginx"
fi
