#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# make-env.sh — Génère le fichier .env de production sur le VPS YIGUI
# ══════════════════════════════════════════════════════════════════════════════
# À exécuter SUR LE SERVEUR, dans /opt/kharandi.
# Génère automatiquement les secrets techniques (SECRET_KEY, CRON_SECRET,
# mot de passe PostgreSQL) et demande interactivement les clés fournisseurs.
#
#   ssh root@212.95.33.158
#   cd /opt/kharandi && bash deploy/make-env.sh
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[X]${NC} $*" >&2; exit 1; }

[ -f .env.yigui.example ] || die "Lancez ce script depuis /opt/kharandi."

if [ -f .env ]; then
    warn "Un fichier .env existe déjà."
    read -rp "Le remplacer ? Une sauvegarde sera créée. [o/N] " ans
    [[ "$ans" =~ ^[oOyY]$ ]] || { echo "Abandon."; exit 0; }
    cp .env ".env.bak.$(date +%Y%m%d-%H%M%S)"
    log "Sauvegarde créée."
fi

gen() { python3 -c "import secrets;print(secrets.token_urlsafe($1))"; }

# ─── Secrets techniques générés automatiquement ───────────────────────────────
log "Génération des secrets techniques"
SECRET_KEY="$(gen 64)"
CRON_SECRET="$(gen 32)"
POSTGRES_PASSWORD="$(gen 24)"
# LengoPay ne signe pas ses callbacks. L'authentification repose donc sur un
# jeton secret placé dans l'URL de callback : seul un émetteur connaissant
# l'URL complète peut déclencher l'activation d'un abonnement.
LENGOPAY_CALLBACK_TOKEN="$(gen 32)"
# Signature HMAC : non fournie par LengoPay, laissée vide.
LENGOPAY_WEBHOOK_SECRET=""

# ─── Saisie interactive ───────────────────────────────────────────────────────
ask() {                      # ask VARIABLE "Libellé" [obligatoire]
    local var="$1" label="$2" required="${3:-non}" val=""
    while :; do
        read -rp "  ${label} : " val
        if [ -z "$val" ] && [ "$required" = "oui" ]; then
            warn "  Cette valeur est obligatoire."
            continue
        fi
        break
    done
    printf -v "$var" '%s' "$val"
}

echo
echo "─── Compte super-administrateur ──────────────────────────────────────────"
ask ADMIN_PHONE    "Numéro admin (format +224XXXXXXXXX)" oui
while :; do
    read -rsp "  Mot de passe admin (min. 8 caractères) : " ADMIN_PASSWORD; echo
    [ ${#ADMIN_PASSWORD} -ge 8 ] && break
    warn "  Trop court."
done

echo
echo "─── SMS Nimba (envoi des codes OTP) ──────────────────────────────────────"
ask NIMBA_ACCOUNT_SID  "Account SID"  oui
ask NIMBA_AUTH_TOKEN   "Auth token"   oui
ask NIMBA_SENDER_NAME  "Nom expéditeur [Kharandi]"
NIMBA_SENDER_NAME="${NIMBA_SENDER_NAME:-Kharandi}"

echo
echo "─── Paiement LengoPay (Orange Money, MTN) ────────────────────────────────"
ask LENGOPAY_SITE_ID      "Site ID"      oui
ask LENGOPAY_LICENSE_KEY  "Clé licence"  oui

echo
echo "─── Intelligence artificielle Karamo ─────────────────────────────────────"
ask OPENROUTER_API_KEY "Clé OpenRouter" oui
ask GEMINI_API_KEY     "Clé Gemini (facultatif, Entrée pour ignorer)"
ask TAVILY_API_KEY     "Clé Tavily (facultatif, Entrée pour ignorer)"

echo
echo "─── Stockage médias Cloudinary (facultatif) ──────────────────────────────"
ask CLOUDINARY_CLOUD_NAME  "Cloud name (Entrée pour ignorer)"
ask CLOUDINARY_API_KEY     "API key (Entrée pour ignorer)"
ask CLOUDINARY_API_SECRET  "API secret (Entrée pour ignorer)"

# ─── Écriture ─────────────────────────────────────────────────────────────────
cat > .env <<EOF
# Généré par deploy/make-env.sh le $(date '+%d/%m/%Y à %H:%M')
# NE JAMAIS versionner ni copier ce fichier ailleurs.

SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=212.95.33.158,localhost,127.0.0.1,api,api.kharandi.gn,kharandi.gn,www.kharandi.gn

POSTGRES_DB=kharandi_db
POSTGRES_USER=kharandi_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

REDIS_URL=redis://redis:6379/0

CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://kharandi.gn,https://www.kharandi.gn,http://212.95.33.158,http://localhost:5173
CSRF_TRUSTED_ORIGINS=https://kharandi.gn,https://www.kharandi.gn,http://212.95.33.158
FRONTEND_URL=https://kharandi.gn
ENABLE_HTTPS=False

NIMBA_ACCOUNT_SID=${NIMBA_ACCOUNT_SID}
NIMBA_AUTH_TOKEN=${NIMBA_AUTH_TOKEN}
NIMBA_SENDER_NAME=${NIMBA_SENDER_NAME}

LENGOPAY_SITE_ID=${LENGOPAY_SITE_ID}
LENGOPAY_LICENSE_KEY=${LENGOPAY_LICENSE_KEY}
LENGOPAY_CURRENCY=GNF
LENGOPAY_COUNTRY=GN
LENGOPAY_BASE_URL=https://portal.lengopay.com/api/v1
LENGOPAY_CALLBACK_TOKEN=${LENGOPAY_CALLBACK_TOKEN}
LENGOPAY_PUBLIC_BASE_URL=http://212.95.33.158
LENGOPAY_WEBHOOK_SECRET=${LENGOPAY_WEBHOOK_SECRET}
LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True
LENGOPAY_RECONCILE_EVERY_MIN=3
LENGOPAY_AMOUNT_TOLERANCE=1
LENGOPAY_TIMEOUT=20

OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
TAVILY_API_KEY=${TAVILY_API_KEY}

CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME}
CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY}
CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET}

ADMIN_PHONE=${ADMIN_PHONE}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

CRON_SECRET=${CRON_SECRET}
EOF

chmod 600 .env

echo
log "Fichier .env créé (permissions 600, lisible par root uniquement)."
grep -q 'À_REMPLIR' .env && die "Des valeurs À_REMPLIR subsistent." || true
echo
echo "  Secrets générés automatiquement (conservez-les hors du serveur) :"
echo "    Mot de passe PostgreSQL : ${POSTGRES_PASSWORD}"
echo "    CRON_SECRET             : ${CRON_SECRET}"
echo "    LENGOPAY_CALLBACK_TOKEN : ${LENGOPAY_CALLBACK_TOKEN}"

echo
echo "  Déclarez EXACTEMENT cette URL de callback dans votre tableau de bord"
echo "  LengoPay (le jeton final est indispensable) :"
echo "    http://212.95.33.158/api/v1/payments/webhook/${LENGOPAY_CALLBACK_TOKEN}/"
echo
echo "  Étape suivante, depuis votre machine :  bash deploy/deploy-yigui.sh"
