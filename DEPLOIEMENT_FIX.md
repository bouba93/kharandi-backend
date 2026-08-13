# Kharandi Backend — Correctif Docker / Nginx / Healthcheck

Document de référence du correctif appliqué au dépôt.
Objectif : stack stable après `docker compose up -d --build`, après
`docker compose down && up -d`, et après un reboot complet du VPS.

Aucune opération destructive n'est nécessaire ni proposée : les volumes
`postgres_data`, `redis_data`, `media_data`, `static_data` sont intégralement
préservés, la base n'est pas recréée, les migrations ne sont pas réinitialisées.

---

## 1. Cause exacte du problème

Le healthcheck Nginx échouait avec **HTTP 400** parce que la location
`= /healthz` faisait un `proxy_pass` **sans définir l'en-tête `Host`** :

```nginx
location = /healthz {
    proxy_pass http://kharandi_api;   # ← aucun proxy_set_header Host
    access_log off;
}
```

Quand aucun `proxy_set_header Host` n'est présent, Nginx applique sa valeur par
défaut :

```
proxy_set_header Host $proxy_host;
```

`$proxy_host` vaut **le nom de l'upstream**, ici littéralement `kharandi_api`.
Django recevait donc `Host: kharandi_api`, absent de `ALLOWED_HOSTS`, et
répondait `400 Bad Request` (`DisallowedHost`) — sans écrire d'erreur visible
car `access_log off` était actif sur cette location.

Cela explique parfaitement les symptômes observés :

| Commande | Host envoyé | Résultat |
|---|---|---|
| `wget http://api:8000/healthz` (direct, sans Nginx) | `api` → présent dans `ALLOWED_HOSTS` | **200** |
| `curl http://127.0.0.1/healthz` (via Nginx) | `kharandi_api` (`$proxy_host`) | **400** |
| `curl http://212.95.33.158/healthz` (via Nginx) | `kharandi_api` (`$proxy_host`) | **400** |
| `curl http://212.95.33.158/api/v1/...` (location `/`) | `$host` correctement défini | OK |

Seule la location `/` définissait `Host $host`, d'où l'API fonctionnelle mais la
sonde cassée. La configuration était bien valide (`nginx -t` OK) : c'était un
bug **sémantique**, pas syntaxique.

### Causes secondaires corrigées

| # | Problème | Impact |
|---|---|---|
| 2 | `upstream { server api:8000; }` : Nginx résout `api` **une seule fois au démarrage** et met l'IP en cache indéfiniment | Après `up -d --build` ou un reboot, si le conteneur `api` est recréé avec une nouvelle IP, Nginx renvoie des **502 figés** jusqu'à `restart nginx`. C'est la vraie cause de l'instabilité « après redémarrage ». |
| 3 | Healthcheck Nginx dépendant de Django | Un incident applicatif faisait passer Nginx en `unhealthy` alors que Nginx allait très bien → diagnostic faussé |
| 4 | `/healthz` faisait un `SELECT 1` et renvoyait 503 | Un hoquet PostgreSQL rendait le conteneur `api` `unhealthy` (confusion liveness / readiness) |
| 5 | `USE_X_FORWARDED_HOST = True` alors que Nginx ne posait pas `X-Forwarded-Host` | Surface d'attaque par empoisonnement d'en-tête `Host` |
| 6 | Celery lancé en `nohup` dans le conteneur `api` | Worker non supervisé, invisible de Docker, perdu au moindre incident |
| 7 | `start.sh` rejouait `seed_data` / `load_bac_data` / le scraper à **chaque** démarrage | Démarrages lents, charge inutile après chaque reboot |
| 8 | `server_name _` en `default_server` | N'importe quel `Host` atteignait Django |
| 9 | Pas de rotation des logs Docker | Saturation disque du VPS à terme |

---

## 2. Fichiers modifiés

| Fichier | Nature |
|---|---|
| `nginx/proxy_params.conf` | **nouveau** — en-têtes de proxy partagés (`Host $host` forcé) |
| `nginx/health.conf` | **nouveau** — écouteur de santé interne `127.0.0.1:8081` |
| `nginx/kharandi.conf` | réécrit — resolver Docker, upstream en variable, `default_server` 444 |
| `nginx/kharandi-ssl.conf.template` | réécrit — mêmes règles en HTTPS |
| `docker-compose.yml` | réécrit — healthchecks, réseau nommé, service `worker`, logs |
| `start.sh` | réécrit — idempotent, attente DB, amorçage une-seule-fois |
| `start-worker.sh` | **nouveau** — worker Celery supervisé |
| `Dockerfile` | `chmod +x start-worker.sh` |
| `kharandi_backend/settings.py` | `ALLOWED_HOSTS`, `USE_X_FORWARDED_HOST`, `CSRF_TRUSTED_ORIGINS`, CORS Vercel |
| `kharandi_backend/urls.py` | `/healthz` = liveness, `/readyz` = readiness (nouveau) |
| `core/middleware.py` | sondes exemptées du rate-limiting |
| `deploy/enable-ssl.sh` | `nginx -t` avant rechargement |
| `.env.yigui.example` | variables mises à jour |

---

## 3. Stratégie de healthcheck retenue

**Le healthcheck du conteneur Nginx teste uniquement Nginx.** Justification :

1. **Sémantique Docker.** Un healthcheck répond à « ce conteneur peut-il servir
   du trafic ? ». Nginx sert des statiques, le challenge ACME et les pages
   d'erreur même quand Django est à terre : il est donc sain.
2. **Pas de cascade.** Avec un healthcheck couplé, un simple `restart api`
   marquerait Nginx `unhealthy`, ce qui empoisonne la supervision et peut
   déclencher des redémarrages en boucle avec un orchestrateur.
3. **Le diagnostic reste possible** : trois sondes distinctes sont exposées.

| Sonde | Où | Teste | Utilisée par |
|---|---|---|---|
| `127.0.0.1:8081/nginx-health` | Nginx (interne) | Nginx seul | **healthcheck Docker nginx** |
| `127.0.0.1:8081/api-health` | Nginx → Django | chaîne proxy | diagnostic |
| `127.0.0.1:8081/api-ready` | Nginx → Django | + PostgreSQL/Redis | diagnostic |
| `:8000/healthz` | Django | process vivant | **healthcheck Docker api** |
| `/readyz` | Django | PostgreSQL + Redis | monitoring externe |

L'écouteur interne sur `127.0.0.1:8081` n'est **jamais publié** (aucun `ports:`)
et ne dépend d'aucun `server_name` : le healthcheck ne peut donc plus être cassé
par un changement de domaine, de DNS, ou par `ALLOWED_HOSTS`. Il ne dépend
évidemment pas non plus du frontend Vercel.

---

## 4. Commandes à exécuter sur le VPS

```bash
cd /opt/kharandi           # adapter au chemin réel du dépôt

# 0. Sauvegarde de sécurité de la base (fortement recommandé)
docker compose exec -T db pg_dump -U kharandi_user kharandi_db \
  | gzip > ~/kharandi-$(date +%F-%H%M).sql.gz

# 1. Sauvegarde de la configuration actuelle
cp docker-compose.yml docker-compose.yml.bak
cp nginx/kharandi.conf nginx/kharandi.conf.bak
cp start.sh start.sh.bak

# 2. Récupérer les fichiers corrigés (git pull, ou copie manuelle)
git pull            # ou : scp des fichiers modifiés

# 3. Vérifier que .env est cohérent (voir §6)
grep -E '^(ALLOWED_HOSTS|CSRF_TRUSTED_ORIGINS|CORS_ALLOWED_ORIGINS)=' .env

# 4. Vérifier la composition SANS rien démarrer
docker compose config >/dev/null && echo "compose OK"

# 5. Reconstruire et relancer  (JAMAIS `down -v`)
docker compose up -d --build

# 6. Vérifier la syntaxe Nginx dans le conteneur
docker compose exec nginx nginx -t
```

> ⚠️ Ne jamais utiliser `docker compose down -v`. `up -d --build` suffit :
> les volumes nommés sont conservés lors de la recréation des conteneurs.

---

## 5. Commandes de vérification et résultats attendus

```bash
docker compose ps
```
```
NAME                 SERVICE   STATUS
kharandi-api-1       api       Up (healthy)
kharandi-db-1        db        Up (healthy)
kharandi-nginx-1     nginx     Up (healthy)
kharandi-redis-1     redis     Up (healthy)
kharandi-worker-1    worker    Up (healthy)
kharandi-certbot-1   certbot   Up
```

```bash
# Liveness Nginx (celle qu'utilise Docker)
docker compose exec nginx wget -qO- http://127.0.0.1:8081/nginx-health
# → nginx ok

# Idem via le port 80 public
docker compose exec nginx wget -qO- http://127.0.0.1/nginx-health
# → nginx ok

# Chaîne Nginx → Django (le test qui renvoyait 400)
docker compose exec nginx wget -S -O- http://127.0.0.1/healthz
# → HTTP/1.1 200 OK   {"status": "ok", "service": "kharandi-api"}

# Django direct
docker compose exec nginx wget -S -O- http://api:8000/healthz
# → HTTP/1.1 200 OK

# Readiness profonde (base + cache)
curl -s http://212.95.33.158/readyz
# → {"status": "ok", "checks": {"database": true, "cache": true}}

# Depuis Internet
curl -I http://212.95.33.158/healthz
# → HTTP/1.1 200 OK

# Host inconnu → rejeté par Nginx (protection anti Host-spoofing)
curl -I -H 'Host: evil.example' http://212.95.33.158/
# → connexion fermée sans réponse (444)

# Détail des sondes
docker inspect kharandi-api-1   --format='{{json .State.Health}}' | python3 -m json.tool
docker inspect kharandi-nginx-1 --format='{{json .State.Health}}' | python3 -m json.tool

# Logs
docker compose logs --tail=100 api
docker compose logs --tail=100 nginx

# Migrations : rien en attente, rien de rejoué
docker compose exec api python manage.py showmigrations users
docker compose exec api python manage.py migrate --check && echo "schéma à jour"

# Ports publiés : uniquement 80 et 443
docker compose ps --format '{{.Service}} {{.Ports}}'
# db et redis ne doivent afficher AUCUN port publié
```

### Test de résilience au reboot

```bash
sudo reboot
# puis, une fois reconnecté (~1 à 3 min) :
docker compose ps          # tous healthy sans intervention
curl -I http://212.95.33.158/healthz
```

`restart: unless-stopped` est actif sur `db`, `redis`, `api`, `worker`, `nginx`
et `certbot` : Docker relance la stack automatiquement au démarrage du VPS.
Vérifier que le démon Docker est bien activé :

```bash
sudo systemctl is-enabled docker    # → enabled
```

---

## 6. Variables d'environnement à ajuster dans `.env`

```dotenv
# Hôtes PUBLICS du backend uniquement.
# localhost / 127.0.0.1 / api / nginx sont ajoutés d'office par settings.py.
# Ne pas mettre "*" : Nginx filtre déjà les Host inconnus.
ALLOWED_HOSTS=212.95.33.158,api.kharandi.gn

# Origines du frontend Vercel autorisées à appeler l'API
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://kharandi.gn,https://www.kharandi.gn,http://localhost:5173
VERCEL_PREVIEW_CORS=False      # True pour autoriser https://*.vercel.app

# Le schéma est obligatoire
CSRF_TRUSTED_ORIGINS=https://kharandi.gn,https://www.kharandi.gn,http://212.95.33.158

# Laisser False : Nginx transmet déjà le vrai Host
USE_X_FORWARDED_HOST=False

# Démarrage
RUN_MIGRATIONS=1
RUN_COLLECTSTATIC=1
RUN_SEED=1
RUN_BAC_IMPORT=1
RUN_BAC_SCRAPER=0
RUN_CELERY_IN_API=0
```

Aucune variable existante n'est supprimée ; `VERCEL_PREVIEW_CORS`,
`USE_X_FORWARDED_HOST` et les `RUN_*` sont optionnelles (valeurs par défaut
sûres si absentes).

---

## 7. Communication frontend Vercel → backend VPS

Le frontend, le DNS et la configuration Vercel ne sont **pas** modifiés.

Côté Vercel, pointer simplement l'API vers le VPS :

```
VITE_API_URL=http://212.95.33.158/api/v1
```

⚠️ Limite connue : une page servie en **HTTPS** par Vercel ne peut pas appeler
une API en **HTTP** (blocage « mixed content » par le navigateur). Deux options :

**Option A — recommandée : un sous-domaine backend dédié en HTTPS.**
Ne touche pas au DNS de `kharandi.gn` utilisé par Vercel ; on ajoute uniquement
un enregistrement A supplémentaire :

```
api.kharandi.gn.   A   212.95.33.158
```

puis, sur le VPS :

```bash
bash deploy/enable-ssl.sh api.kharandi.gn admin@kharandi.gn
```

et côté Vercel : `VITE_API_URL=https://api.kharandi.gn/api/v1`.
`api.kharandi.gn` est déjà présent dans le `server_name` Nginx.

**Option B — provisoire :** utiliser `http://212.95.33.158/api/v1` depuis un
frontend servi en HTTP, ou en développement local uniquement.

CORS est déjà configuré pour accepter `https://kharandi.gn` et
`https://www.kharandi.gn` avec `CORS_ALLOW_CREDENTIALS = True`.

---

## 8. Procédure de rollback (non destructive)

Aucune donnée n'est touchée : le rollback consiste à restaurer des fichiers de
configuration.

```bash
cd /opt/kharandi

# Rollback complet
cp docker-compose.yml.bak docker-compose.yml
cp nginx/kharandi.conf.bak nginx/kharandi.conf
cp start.sh.bak start.sh
docker compose up -d --build

# Rollback partiel : seulement Nginx
cp nginx/kharandi.conf.bak nginx/kharandi.conf
docker compose restart nginx

# Rollback via git
git stash            # ou : git checkout -- <fichier>
docker compose up -d --build
```

Neutraliser temporairement le healthcheck Nginx sans rien réinstaller :

```bash
docker compose stop nginx && docker compose up -d nginx
```

**Interdits en toutes circonstances :** `docker compose down -v`,
`docker volume rm kharandi_postgres_data`, `DROP DATABASE`,
`manage.py flush`, suppression des fichiers de migrations.

---

## 9. Notes d'exploitation

- **Ajouter un domaine backend** : l'ajouter dans le `server_name` de
  `nginx/kharandi.conf` **et** dans `ALLOWED_HOSTS` du `.env`, puis
  `docker compose restart nginx api`.
- **Relancer l'amorçage** (seed / import BAC) :
  `docker compose exec api rm -f /app/media/.kharandi/bootstrap-v1.done`
  puis `docker compose restart api`.
- **Lancer le scraper BAC à la demande** :
  `docker compose exec -d api python manage.py scrape_bac_subjects --delay 2`
- **Logs du worker** : `docker compose logs -f worker` (il n'écrit plus dans
  `/tmp/celery_worker.log`, il est supervisé par Docker).
- **PostgreSQL / Redis** : aucun port publié, joignables uniquement depuis le
  réseau Docker `kharandi`. Pour un accès psql ponctuel :
  `docker compose exec db psql -U kharandi_user -d kharandi_db`.

---

## 10. Comment déployer

Trois scénarios. Le vôtre est le **A** (stack déjà en production avec des données).

### A. Mise à jour d'une stack existante — recommandé

Tout est automatisé par `deploy/update.sh` : sauvegarde base + configuration,
validation, build, démarrage, contrôle Nginx avec restauration automatique en
cas d'échec, puis sondes de santé.

```bash
ssh root@212.95.33.158
cd /opt/kharandi
git pull                      # ou rsync depuis votre machine
bash deploy/update.sh
```

Aucun volume n'est supprimé, la base n'est ni recréée ni migrée de force.

### B. Déploiement depuis votre machine locale

```bash
cd /chemin/vers/Backend-Kharandi
bash deploy/deploy-yigui.sh
```

Le script envoie le code par rsync (en préservant `.env`, `media` et
`staticfiles`), construit les images, démarre la stack, valide `nginx -t` et
attend que `/healthz` réponde.

Variables surchargeables : `VPS_HOST`, `VPS_USER`, `APP_DIR`.

### C. Déploiement manuel, étape par étape

```bash
ssh root@212.95.33.158
cd /opt/kharandi

docker compose exec -T db pg_dump -U kharandi_user kharandi_db \
  | gzip > /opt/kharandi-backups/db_$(date +%F_%H%M).sql.gz

cp -a docker-compose.yml start.sh nginx /opt/kharandi-backups/config_$(date +%F_%H%M)/

git pull
docker compose config >/dev/null
docker compose build --pull
docker compose up -d --remove-orphans
docker compose exec nginx nginx -t
docker compose ps
```

### D. VPS neuf (première installation)

```bash
# 1. Sur le serveur, en root — une seule fois
ssh root@212.95.33.158
bash bootstrap-yigui.sh          # Docker, UFW (22/80/443), fail2ban, swap

# 2. Envoyer le code depuis votre machine
bash deploy/deploy-yigui.sh      # s'arrête pour vous faire remplir le .env

# 3. Générer le .env sur le serveur
ssh root@212.95.33.158 'cd /opt/kharandi && bash deploy/make-env.sh'

# 4. Relancer le déploiement
bash deploy/deploy-yigui.sh

# 5. Optionnel — HTTPS sur un sous-domaine backend dédié
ssh root@212.95.33.158 'cd /opt/kharandi && bash deploy/enable-ssl.sh api.kharandi.gn admin@kharandi.gn'
```

### Après le déploiement

```bash
docker compose ps                                  # tout en (healthy)
curl -I http://212.95.33.158/healthz               # 200 OK
curl -s http://212.95.33.158/readyz                # database: true
docker compose logs --tail=100 api
```

Sauvegardes automatiques quotidiennes (cron root) :

```bash
0 3 * * * bash /opt/kharandi/deploy/backup.sh >> /var/log/kharandi-backup.log 2>&1
```
