# ──────────────────────────────────────────────────────────────────────────────
# DÉPLOIEMENT KHARANDI SUR HOSTINGER VPS (KVM 2 — 8GB RAM / 2 vCPU)
# ──────────────────────────────────────────────────────────────────────────────

## 1. Acheter et configurer le VPS
Dans le panneau Hostinger → VPS → ton serveur :
- Système d'exploitation : choisis "Ubuntu 24.04" 
  (ou template "Ubuntu 24.04 + Docker" si proposé → saute l'étape 3)
- Note l'IP du serveur (ex: 82.180.xxx.xxx)
- Définis un mot de passe root OU ajoute ta clé SSH

## 2. Pointer le DNS
Chez le registrar de kharandi.gn, ajoute un enregistrement :
  api.kharandi.gn  →  Type A  →  <IP_HOSTINGER>

Attends ~10-30 min que le DNS se propage.
Vérifie avec : ping api.kharandi.gn

## 3. Se connecter et installer Docker
ssh root@<IP_HOSTINGER>

apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin git

# Vérifier :
docker --version
docker compose version

## 4. Récupérer le code
git clone https://github.com/<ton-compte>/<ton-repo>.git kharandi
cd kharandi

## 5. Créer le fichier .env
nano .env
# Colle ceci (remplace les <...>) :

SECRET_KEY=<génère avec: openssl rand -hex 40>
DEBUG=False
POSTGRES_DB=kharandi_db
POSTGRES_USER=kharandi_user
POSTGRES_PASSWORD=<mot de passe fort sans espaces>
ALLOWED_HOSTS=api.kharandi.gn
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://www.kharandi.gn,https://kharandi.gn
FRONTEND_URL=https://www.kharandi.gn
OPENROUTER_API_KEY=<ta clé>
TAVILY_API_KEY=<ta clé>
NIMBA_ACCOUNT_SID=<ton SID>
NIMBA_AUTH_TOKEN=<ton token>
NIMBA_SENDER_NAME=Kharandi
LENGOPAY_SITE_ID=<ton site>
LENGOPAY_LICENSE_KEY=<ta licence>
LENGOPAY_WEBHOOK_SECRET=<un secret partagé long et aléatoire>
CLOUDINARY_CLOUD_NAME=<ton cloud>
CLOUDINARY_API_KEY=<ta clé>
CLOUDINARY_API_SECRET=<ton secret>
USE_CLOUDINARY=True
ADMIN_PHONE=<numéro administrateur>
ADMIN_PASSWORD=<mot de passe administrateur fort>
CRON_SECRET=<un secret pour le cron>

# Ctrl+O pour sauver, Entrée, Ctrl+X pour quitter

## 6. Ouvrir le pare-feu (si Hostinger en a un actif)
# Dans le panneau Hostinger → Firewall → autoriser ports 80, 443, 22

## 7. Générer le certificat SSL (une seule fois)
# Démarrer nginx en HTTP pour le challenge Let's Encrypt :
docker compose up -d nginx
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d api.kharandi.gn --email ton@email.com --agree-tos --no-eff-email
docker compose down

## 8. Lancer toute la plateforme
docker compose up -d --build

# Suivre le démarrage (migrations, 250 sujets BAC, Celery, Gunicorn) :
docker compose logs -f api
# Attends de voir "Booting worker" → c'est prêt !

## 9. Tester
curl https://api.kharandi.gn/api/v1/
# Doit répondre du JSON

## 10. Brancher le frontend
# Là où est déployé www.kharandi.gn (Vercel/Netlify/Hostinger) :
VITE_API_URL=https://api.kharandi.gn/api/v1
# Redéploie le frontend.

# ──────────────────────────────────────────────────────────────────────────────
# COMMANDES UTILES AU QUOTIDIEN
# ──────────────────────────────────────────────────────────────────────────────

# Voir les logs
docker compose logs -f api

# Redémarrer
docker compose restart api

# Mettre à jour après un git push
git pull && docker compose up -d --build

# Voir l'usage RAM/CPU
docker stats

# Accéder au shell Django (créer admin, debug)
docker compose exec api python manage.py shell

# Sauvegarder la base de données
docker compose exec db pg_dump -U kharandi_user kharandi_db > backup_$(date +%F).sql

# ──────────────────────────────────────────────────────────────────────────────
# NOTES
# ──────────────────────────────────────────────────────────────────────────────
# - Le serveur ne dort JAMAIS → plus de cold start, plus de 503 Karamo
# - cron-job.org pour le ping : INUTILE maintenant
# - Garde le cron horaire run-cron pour expirer les abonnements :
#     https://api.kharandi.gn/api/v1/payments/run-cron/ (header X-Cron-Secret)
# - SSE notifications temps réel : réactivable (nginx déjà configuré proxy_buffering off)
# - Avec 8GB RAM : 4 workers Gunicorn + Celery concurrency 4 + Redis 512MB
#   → tient 300-400 élèves simultanés confortablement
# - Sauvegardes auto : active les backups Hostinger dans le panneau VPS
