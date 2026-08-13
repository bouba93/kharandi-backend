# Déploiement du backend Kharandi sur le VPS YIGUI

**Serveur** : `212.95.33.158` — utilisateur `root` — accès SSH
**Répertoire cible** : `/opt/kharandi`
**Stack** : Docker Compose → PostgreSQL 16 · Redis 7 · Django/Gunicorn · Celery · Nginx · Certbot

---

## Vue d'ensemble

```
Internet ──▶ Nginx (80/443) ──▶ Gunicorn / Django (api:8000)
                 │                      │
                 │                      ├──▶ PostgreSQL (db:5432, réseau interne)
                 │                      └──▶ Redis (redis:6379, réseau interne)
                 └──▶ /static/ et /media/ (volumes Docker)
```

PostgreSQL et Redis ne sont **jamais** exposés à Internet : ils vivent uniquement sur le réseau Docker interne.

---

## Étape 1 — Préparer le serveur (une seule fois)

```bash
scp deploy/bootstrap-yigui.sh root@212.95.33.158:/root/
ssh root@212.95.33.158 'bash /root/bootstrap-yigui.sh'
```

Ce script installe Docker Engine + Compose v2, crée un swap de 2 Go, configure le pare-feu UFW (ports 22, 80, 443 uniquement), active fail2ban et limite la taille des logs Docker.

## Étape 2 — Premier déploiement

Depuis la racine du backend, sur votre machine :

```bash
bash deploy/deploy-yigui.sh
```

Au premier passage, le script copie `.env.yigui.example` en `.env` sur le serveur puis s'arrête.

> **Le fichier `.env` se crée uniquement sur le serveur, jamais dans le code.** Il n'est ni versionné (`.gitignore`) ni transféré par le script de déploiement (`--exclude '.env'`). Il survit donc à toutes les mises à jour.

Deux façons de le remplir.

**Option A — assistant guidé (recommandé)**

```bash
ssh root@212.95.33.158
cd /opt/kharandi && bash deploy/make-env.sh
```

L'assistant génère seul les secrets techniques (`SECRET_KEY`, `CRON_SECRET`, mot de passe PostgreSQL, secret webhook), vous demande uniquement les clés fournisseurs, puis écrit le fichier en permissions `600`.

**Option B — édition manuelle**

```bash
ssh root@212.95.33.158
nano /opt/kharandi/.env
chmod 600 /opt/kharandi/.env
```

Valeurs obligatoires (toutes les lignes marquées `À_REMPLIR`) :

| Variable | Comment l'obtenir |
|---|---|
| `SECRET_KEY` | `python3 -c "import secrets;print(secrets.token_urlsafe(64))"` |
| `POSTGRES_PASSWORD` | mot de passe fort de votre choix |
| `NIMBA_ACCOUNT_SID` / `NIMBA_AUTH_TOKEN` | tableau de bord Nimba SMS (OTP) |
| `LENGOPAY_SITE_ID` / `LENGOPAY_LICENSE_KEY` | tableau de bord LengoPay |
| `OPENROUTER_API_KEY` | clé IA pour Karamo |
| `ADMIN_PHONE` / `ADMIN_PASSWORD` | compte super-administrateur créé au démarrage |
| `CRON_SECRET` | `python3 -c "import secrets;print(secrets.token_urlsafe(32))"` |

Les variables laissées vides (`GEMINI_API_KEY`, `TAVILY_API_KEY`, les trois `CLOUDINARY_*`) sont facultatives : sans Cloudinary, les médias sont stockés sur le disque du serveur dans le volume `media`.

`DATABASE_URL` n'apparaît pas dans le fichier : docker-compose la reconstruit à partir des variables `POSTGRES_*`. Ne l'ajoutez pas à la main.

`ENABLE_HTTPS` doit rester à `False` tant que vous accédez au serveur par son adresse IP. Le script `deploy/enable-ssl.sh` le bascule automatiquement le jour où vous branchez un domaine.

Puis relancez le déploiement :

```bash
bash deploy/deploy-yigui.sh
```

Le script envoie le code, construit les images, démarre la stack et attend que `/healthz` réponde.

## Étape 3 — Vérifier

| Point d'entrée | URL |
|---|---|
| Santé | http://212.95.33.158/healthz |
| Racine API | http://212.95.33.158/ |
| Documentation Swagger | http://212.95.33.158/api/docs/ |
| Administration Django | http://212.95.33.158/admin/ |

Test rapide d'un nouvel endpoint :

```bash
curl -s http://212.95.33.158/healthz
curl -s http://212.95.33.158/api/v1/content/scholarships/   # 401 attendu sans jeton
```

### Vérifier les trois prestataires (Nimba, LengoPay, OpenRouter)

Une clé mal copiée ne provoque aucune erreur au démarrage : le service tombe en
panne silencieusement au premier usage réel. Cette commande interroge les trois
API avec vos vraies clés et vous dit immédiatement lesquelles fonctionnent.

```bash
cd /opt/kharandi
docker compose exec api python manage.py check_services
```

Pour recevoir un vrai SMS de test sur votre téléphone (consomme 1 crédit Nimba) :

```bash
docker compose exec api python manage.py check_services --sms +224XXXXXXXXX
```

Ce que la commande contrôle :

| Prestataire | Contrôle effectué |
|---|---|
| Nimba SMS | Identifiants acceptés, solde de SMS restant, envoi réel en option |
| LengoPay | Création d'un paiement de test, URL de callback cohérente, vérification serveur à serveur opérationnelle |
| OpenRouter | Clé acceptée, crédit restant |

Les clés ne sont jamais affichées en entier : seuls les 4 premiers et 4 derniers
caractères apparaissent, ce qui suffit à repérer une erreur de copie.

### Confirmation des paiements LengoPay

LengoPay n'envoie **aucune signature** avec ses callbacks : le corps reçu est un
simple JSON `{pay_id, status, amount, message, client}`. On ne peut donc pas
faire confiance à ce que le callback annonce. Le backend fonctionne ainsi :

1. À la réception d'un callback, il rappelle LengoPay (`LENGOPAY_STATUS_URL`)
   pour demander le vrai statut du paiement.
2. L'abonnement n'est activé que si LengoPay confirme lui-même `SUCCESS`.
3. Si les deux statuts divergent, une alerte de fraude est écrite dans les logs
   et c'est le statut réel qui fait foi.
4. Si LengoPay est injoignable, la transaction reste en attente et une tâche de
   réconciliation la reprend automatiquement (voir ci-dessous).

Conséquence : `LENGOPAY_WEBHOOK_SECRET` doit rester **vide**. Un secret que nous
générerions nous-mêmes ne protégerait rien puisque LengoPay ne l'utiliserait pas.

> À vérifier auprès du support LengoPay : l'adresse exacte de consultation d'un
> paiement. La valeur par défaut est
> `https://portal.lengopay.com/api/v1/payments/{pay_id}`. Si `check_services`
> signale que la vérification serveur à serveur échoue, corrigez
> `LENGOPAY_STATUS_URL` dans le `.env`.

### Rattrapage des paiements dont le callback s'est perdu

Si le serveur était en cours de redémarrage au moment où LengoPay a envoyé son
callback, le paiement resterait bloqué en attente. Une tâche de réconciliation
reprend toutes les transactions en attente de plus de 2 minutes et interroge
LengoPay pour chacune. Elle s'exécute avec les autres tâches planifiées :

```bash
curl -s -X POST http://212.95.33.158/api/v1/payments/run-cron/ \
     -H "X-Cron-Secret: VOTRE_CRON_SECRET"
```

Programmez-la toutes les 10 minutes sur le serveur (`crontab -e`) :

```
*/10 * * * * curl -s -X POST http://212.95.33.158/api/v1/payments/run-cron/ -H "X-Cron-Secret: VOTRE_CRON_SECRET" >/dev/null 2>&1
```

## Étape 4 — Connecter le frontend

Dans le `.env` du frontend Kharandi :

```
VITE_API_URL=http://212.95.33.158/api/v1
```

Ajoutez ensuite l'origine du frontend dans `CORS_ALLOWED_ORIGINS` du `.env` serveur, puis `docker compose restart api`.

## Étape 5 (recommandé) — Activer HTTPS

Créez un enregistrement DNS de type A : `api.kharandi.gn → 212.95.33.158`, puis sur le serveur :

```bash
cd /opt/kharandi
bash deploy/enable-ssl.sh api.kharandi.gn votre@email.com
```

Le certificat Let's Encrypt est renouvelé automatiquement toutes les 12 heures par le conteneur `certbot`.

---

## Mises à jour ultérieures

```bash
bash deploy/deploy-yigui.sh
```

Le fichier `.env` du serveur est toujours préservé.

## Sauvegardes

```bash
ssh root@212.95.33.158 'bash /opt/kharandi/deploy/backup.sh'
```

Automatisation quotidienne (cron root sur le serveur) :

```
0 3 * * * bash /opt/kharandi/deploy/backup.sh >> /var/log/kharandi-backup.log 2>&1
```

Les archives sont conservées 14 jours dans `/opt/kharandi-backups`.

## Exploitation courante

```bash
cd /opt/kharandi

docker compose ps                        # état des conteneurs
docker compose logs -f api               # logs Django en direct
docker compose logs --tail=100 nginx     # logs Nginx
docker compose restart api               # redémarrer l'API
docker compose down && docker compose up -d   # redémarrage complet

docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
docker compose exec api python manage.py shell
docker compose exec db psql -U kharandi_user -d kharandi_db
```

## Diagnostic

| Symptôme | Piste |
|---|---|
| `502 Bad Gateway` | l'API démarre encore — `docker compose logs api` |
| `/healthz` renvoie `degraded` | PostgreSQL indisponible — `docker compose logs db` |
| Erreur CORS côté navigateur | ajoutez l'origine dans `CORS_ALLOWED_ORIGINS` puis `docker compose restart api` |
| `DisallowedHost` | ajoutez le domaine ou l'IP dans `ALLOWED_HOSTS` |
| Certbot échoue | le DNS ne pointe pas encore vers l'IP, ou le port 80 est fermé |
| Build très lent / OOM | le swap de 2 Go du script bootstrap doit être actif : `swapon --show` |
