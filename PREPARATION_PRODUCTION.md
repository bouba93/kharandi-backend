# Kharandi Backend — Préparation production et remplacement du VPS

Réponse point par point à la checklist de 37 points, puis procédure de
remplacement contrôlé du backend sur le VPS `212.95.33.158`.

Tout a été appliqué **dans les fichiers du dépôt**, pas seulement décrit.

---

## 1. Cause exacte des problèmes corrigés dans ce lot

Quatre défauts distincts, tous confirmés en exécutant le code — pas déduits par
lecture.

### 1.1 Aucune tâche périodique ne tournait (cause racine du problème de callback perdu)

`kharandi_backend/settings.py` déclarait les tâches périodiques via
`CRONJOBS` (django-crontab). Or **django-crontab a besoin d'un démon `cron`
dans le conteneur**, et l'image `python:3.12-slim` n'en contient pas : ni
`start.sh` ni `start-worker.sh` n'appelaient `manage.py crontab add`.

Conséquence directe et mesurable : la réconciliation des paiements, l'expiration
des abonnements et le nettoyage des OTP **n'ont jamais été exécutés une seule
fois en production**. Un callback LengoPay perdu restait perdu définitivement —
le client payait, son abonnement restait `PENDING`.

### 1.2 Un callback « SUCCESS » était appliqué sans confirmation serveur

`LENGOPAY_REQUIRE_STATUS_CONFIRMATION` valait `False`. Comme LengoPay **ne signe
pas ses callbacks** (aucun HMAC dans la documentation officielle, vérifié sur le
paquet de référence [lengopay_flutter](https://pub.dev/packages/lengopay_flutter)),
la seule protection restante était le jeton dans l'URL. Un jeton qui fuite (log
Nginx, historique de navigateur, capture réseau en HTTP clair) permettait
d'activer des abonnements gratuitement en envoyant un faux
`{"status":"SUCCESS"}`.

### 1.3 La sonde de santé du planificateur se validait elle-même

Défaut introduit puis corrigé pendant ce lot, mentionné parce qu'il illustre le
piège : `beat-healthcheck.py` cherchait la sous-chaîne `" beat"` dans la ligne
de commande des processus. Le script s'appelant `beat-healthcheck.py`, **il se
détectait lui-même** et annonçait `healthy` alors qu'aucun planificateur ne
tournait. Corrigé par une comparaison exacte sur la liste d'arguments, avec
exclusion de son propre PID.

### 1.4 Rien n'empêchait un déploiement avec une configuration dangereuse

`ALLOWED_HOSTS=*`, `CORS_ALLOW_ALL_ORIGINS=True` ou un `SECRET_KEY` par défaut
démarraient sans le moindre avertissement. Aucun garde-fou automatique
n'existait.

---

## 2. Liste des fichiers modifiés et créés

### Fichiers créés

| Fichier | Rôle |
|---|---|
| `payments/tasks.py` | Tâches Celery : réconciliation, rejeu des callbacks orphelins, expiration des abonnements, battement de cœur. Verrou distribué. |
| `start-beat.sh` | Point d'entrée du service `beat` : attente PostgreSQL, nettoyage du PID périmé, affichage du planning, lancement. |
| `beat-healthcheck.py` | Sonde locale du planificateur : processus vivant **et** fichier d'état écrit récemment. |
| `core/checks.py` | 19 contrôles de configuration production, bloquants pour les erreurs. |
| `.gitignore` | Empêche `.env`, clés, dumps SQL et caches d'entrer dans Git. |
| `.dockerignore` | Empêche le `.env` réel d'entrer dans l'image Docker. |
| `.env.production.example` | Modèle documenté pour `api.kharandi.gn` en HTTPS. |
| `PREPARATION_PRODUCTION.md` | Ce document. |

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `docker-compose.yml` | Service `beat` complet, volume `beat_data`, rotation des logs, avertissements sur les volumes à ne jamais supprimer. |
| `kharandi_backend/settings.py` | `CELERY_BEAT_SCHEDULE` (7 tâches), confirmation serveur obligatoire, fiabilité Celery, `CRONJOBS` vidé. |
| `payments/views.py` | Garde d'état terminal `FAILED → SUCCESS`, comptage des alertes d'expiration. |
| `payments/_doctor_helpers.py` | Nouvelles sections « planificateur » et « sécurité », résistance aux migrations manquantes. |
| `payments/management/commands/lengopay_doctor.py` | Réorganisation en 8 sections. |
| `payments/tests.py` | 3 nouvelles classes de tests (mode strict, planification, verrous). |
| `tests/test_api.py` | Contrat du webhook mis à jour (200 + `verified: false`). |
| `Dockerfile` | Création du dossier `beat/`, droits d'exécution sur les nouveaux scripts. |
| `deploy/update.sh` | Vérification du conteneur `beat` et attente du premier battement. |
| `deploy/enable-ssl.sh` | Bascule automatique de `LENGOPAY_PUBLIC_BASE_URL` en HTTPS, redémarrage de `worker` et `beat`, rappel de la nouvelle URL de callback. |
| `deploy/make-env.sh`, `.env.yigui.example` | `LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True`, `LENGOPAY_RECONCILE_EVERY_MIN=3`. |

---

## 3. Réponse aux 37 points de la checklist

### 🔴 Corrections obligatoires dans le backend

**1. Ajouter Celery Beat — fait.**
Trois services distincts : `api` (Gunicorn), `worker` (exécute les tâches),
`beat` (les déclenche). Le planificateur utilise le `PersistentScheduler`
fichier de Celery, pas `django-celery-beat` : aucune dépendance ni migration
supplémentaire, et l'état survit aux redémarrages via le volume `beat_data`.

Planning effectif, tel que déclaré dans `settings.py` :

| Tâche | Fréquence | Objet |
|---|---|---|
| `reconciliation-lengopay` | 3 min | Rattrape les paiements `PENDING` |
| `rejeu-callbacks-orphelins` | 60 s | Rejoue les callbacks `ORPHAN` / `UNVERIFIED` |
| `expiration-abonnements` | 15 min | Passe les abonnements échus en `EXPIRED` |
| `alerte-abonnements-expirants` | 1 h | Prévient avant échéance |
| `nettoyage-otp` | 30 min | Supprime les codes OTP périmés |
| `prechauffage-cache` | 6 h | Cache des matières |
| `battement-beat` | 60 s | Preuve de vie observable |

**2. Réconciliation automatique — fait, toutes les 3 minutes.**
Chaîne complète : `PENDING` → callback perdu → Beat déclenche →
`POST /transaction/status` chez LengoPay → `SUCCESS` (activation) ou `FAILED`.
Seules les transactions de plus de 2 minutes sont interrogées, pour ne pas
concurrencer un callback normal en cours de traitement. Délai maximal
d'attente pour un client dont le callback a été perdu : **3 minutes**.

**3. `LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True` — fait, c'est désormais la valeur par défaut.**
Un callback `SUCCESS` non confirmé par l'API est journalisé `UNVERIFIED`,
renvoie `200 {"received": true, "verified": false}` et **ne crédite rien**. La
réconciliation le rattrape ensuite.

Le `200` est délibéré : LengoPay rejoue les callbacks sur code d'erreur.
Renvoyer `4xx`/`5xx` provoquerait des rafales de rejeu sans rien résoudre.

⚠️ Contrepartie assumée : **ce réglage n'est sûr que si `beat` tourne.** Si le
planificateur est arrêté, les paiements restent en attente. C'est pourquoi
`core/checks.py` refuse de démarrer en mode strict sans réconciliation planifiée
(erreur `kharandi.E018`) et pourquoi `lengopay_doctor` remonte une erreur en
l'absence de battement.

**4. Idempotence — testée, pas seulement relue.**
Le test `test_double_callback_nactive_quune_seule_fois` envoie deux fois le même
`pay_id` et vérifie que `end_date` de l'abonnement est **inchangé** entre les
deux, et que le journal contient exactement 1 `APPLIED` + 2 `DUPLICATE`.

**5. Vérification du montant — faite dans les deux chemins.**
Callback comme réconciliation comparent le montant annoncé au montant de la
transaction (tolérance `LENGOPAY_AMOUNT_TOLERANCE`, 1 par défaut). Un écart
donne `MISMATCH` et **aucune activation**. Testé avec 100 000 annoncés contre
10 000 attendus.

### 🟠 Configuration production

**6. `api.kharandi.gn` → VPS.** DNS à créer par vous (section 4.1). Le backend
est prêt : `server_name` de Nginx inclut déjà `api.kharandi.gn`.

**7. `LENGOPAY_PUBLIC_BASE_URL=https://api.kharandi.gn` — fait** dans
`.env.production.example`, et `deploy/enable-ssl.sh` effectue désormais la
bascule automatiquement.

**8. URL de callback avec jeton long.** Format
`https://api.kharandi.gn/api/v1/payments/webhook/<TOKEN>/`. `core/checks.py`
refuse un jeton de moins de 24 caractères (`kharandi.E015`). Génération :
`openssl rand -hex 32`.

**9-11. CORS, CSRF, ALLOWED_HOSTS explicites — fait, et désormais contrôlés.**
`ALLOWED_HOSTS=*` déclenche `kharandi.E002`, `CORS_ALLOW_ALL_ORIGINS=True`
déclenche `kharandi.E004` : dans les deux cas Django **refuse de démarrer**.
Vérifié en pratique — un `.env` volontairement dangereux produit bien
`SystemCheckError` avec `E002`, `E004` et `E015`.

### 🟠 Docker / infrastructure

**12. Service Beat — fait.** **13. Sonde Beat — faite**, et c'est la partie la
plus subtile : une sonde qui ne vérifie que « le processus est vivant » ne
détecte pas un Beat bloqué. La sonde vérifie donc aussi que le fichier d'état a
été écrit depuis moins de 600 s. Le planificateur de Celery synchronise son
état au moins toutes les 180 s (`Scheduler.sync_every = 180`, vérifié dans la
version installée), soit une marge de 3,3×.

Les trois cas ont été testés : pas de processus → `exit 1` ; processus + fichier
récent → `exit 0` ; processus + fichier vieux de 2 h → `exit 1` avec le message
« le planificateur n'a rien écrit depuis 7200 s ».

**14. Sondes de tous les services.** `api`, `db`, `redis`, `nginx`, `worker`,
`beat` en ont une. À confirmer sur le VPS (section 5).

**15. Resolver `127.0.0.11`.** Non appliqué, et c'est volontaire : la
configuration Nginx utilise un bloc `upstream` avec un nom statique, résolu une
seule fois au démarrage. Le `resolver` interne de Docker n'est utile qu'avec des
`proxy_pass` à variables. L'ajouter ici ne changerait rien tout en donnant
l'illusion d'un correctif. Le vrai garde-fou est `depends_on: api` +
`restart: unless-stopped`.

**16. Volumes conservés — garanti.** `docker-compose.yml` porte un bloc
d'avertissement explicite et aucune commande de la procédure section 4 ne
contient `down -v`.

**17. Sauvegardes PostgreSQL avant déploiement.** Intégrées à la procédure
(étape 4.3) et à `deploy/update.sh`, qui sauvegarde avant toute action.

**18. Rotation des logs Docker — faite.** Ancre YAML `*default-logging` :
`json-file`, `max-size: 10m`, `max-file: 3`, appliquée aux 7 services. Plafond
de 30 Mo par conteneur au lieu d'une croissance illimitée.

### 🟢 Django

**19. Migrations.** `makemigrations --check --dry-run` → « No changes
detected ». `migrate --plan` → `payments.0001`, `0002`, `0003` uniquement,
**aucune opération destructive** (`0003_paymentcallback` est purement additive).

**20. Statiques.** `collectstatic --noinput` → **172 fichiers** copiés, servis
par Nginx sous `/static/`.

**21-22. `/healthz` et `/readyz`.** Déjà corrigés au lot précédent : `/healthz`
répond `200` sans toucher la base, `/readyz` teste réellement PostgreSQL et
Redis.

**23. Endpoints principaux.** Couverts par les 72 tests ; validation en ligne à
l'étape 5.

### 💳 Tests LengoPay (points 24 à 31)

Les 8 scénarios demandés sont couverts par des tests automatisés exécutables.
Résultat de `manage.py test` sur Python 3.12 (même version que l'image
Docker) : **72 tests, OK**.

| Scénario demandé | Test correspondant | Vérification |
|---|---|---|
| 24. Création de paiement | `test_corps_de_la_requete_de_creation` | Corps et en-têtes conformes |
| 25. Callback SUCCESS | `test_callback_confirme_par_lapi_active_labonnement` | Abonnement `ACTIVE` |
| 26. FAILED ne crédite rien | `test_callback_failed_ne_credite_rien` | Reste `PENDING` |
| 27. PENDING réconciliable | `test_pending_reste_en_attente_puis_devient_reconciliable` | Activé par Beat |
| 28. Double callback | `test_double_callback_nactive_quune_seule_fois` | `end_date` inchangé |
| 29. Mauvais montant | `test_montant_inferieur_a_lattendu_est_refuse` + `test_la_reconciliation_refuse_aussi_un_montant_incoherent` | `MISMATCH`, rien activé |
| 30. Faux `pay_id` | `test_faux_pay_id_naffecte_aucune_transaction` | `ORPHAN`, `transaction is None` |
| 31. **Perte du callback** | `test_un_callback_non_confirme_est_rattrape_par_la_reconciliation` + `test_reconciliation_rattrape_un_paiement_dont_le_callback_est_perdu` | **Rattrapé automatiquement** |

Le point 31 étant celui que vous avez signalé comme le plus important, il est
testé dans les deux sens : le callback non confirmé laisse l'abonnement en
attente, puis la réconciliation seule l'active — sans nouveau callback.

Trois tests supplémentaires renforcent le mode strict :
`test_un_success_non_confirme_ne_peut_pas_rouvrir_un_echec`,
`test_seule_lapi_lengopay_peut_rouvrir_un_echec` et
`test_deux_reconciliations_successives_nactivent_quune_fois`.

Deux tests couvrent le verrou distribué qui empêche deux réconciliations de se
chevaucher, ainsi que le cas où Redis est indisponible — la tâche ne doit alors
pas être bloquée (`test_un_cache_indisponible_ne_bloque_pas_la_tache`).

Un test structurel vérifie enfin que **chaque tâche de `CELERY_BEAT_SCHEDULE`
correspond à une tâche Celery réellement enregistrée**
(`test_toutes_les_taches_planifiees_existent`) — un nom mal orthographié ne peut
plus passer en production silencieusement. Deux autres vérifient que la
réconciliation est bien planifiée et assez fréquente.

### 🌐 Vercel (points 32 à 34)

Aucun fichier Vercel n'a été touché, conformément à votre consigne. Actions
côté Vercel en section 8.

### 🔐 Sécurité (points 35 à 37)

**35. License Key jamais côté frontend.** Elle n'est lue que par le backend
(`settings.LENGOPAY_LICENSE_KEY`). Le frontend appelle votre API, qui appelle
LengoPay. `core/checks.py` refuse de démarrer sans elle (`kharandi.E011`).

**36. `.env` hors Git, hors frontend, hors ZIP.** `.gitignore` et
`.dockerignore` ajoutés. **Le ZIP livré ne contient aucun `.env`** — seulement
`.env.production.example` et `.env.yigui.example`.

**37. Secrets à régénérer.** Liste et commandes en section 7.

---

## 4. Commandes exactes sur le VPS

⚠️ Aucune de ces commandes ne supprime de volume, ne recrée de base ni ne
réinitialise de migration.

### 4.1 Préalable — DNS (à faire avant de toucher au serveur)

Chez votre registrar :

| Nom | Type | Valeur |
|---|---|---|
| `api` | A | `212.95.33.158` |
| `@` et `www` | inchangés | Vercel |

Vérification, à répéter jusqu'à obtenir la bonne IP :

```bash
dig +short api.kharandi.gn
# attendu : 212.95.33.158
```

Ne lancez pas Let's Encrypt avant que cette commande réponde correctement.

### 4.2 Inventaire de l'existant (lecture seule)

Vous n'avez pas précisé quel backend occupe actuellement le VPS. Ces commandes
ne modifient rien et permettent de décider en connaissance de cause.

```bash
ssh root@212.95.33.158

# Que tourne-t-il actuellement ?
docker ps -a
docker compose ls

# Quels volumes existent, et lesquels contiennent des données ?
docker volume ls
docker volume ls --format '{{.Name}}' | while read v; do
  echo "== $v : $(docker run --rm -v "$v":/x alpine du -sh /x 2>/dev/null | cut -f1)"
done

# Où est installé l'ancien backend ?
ls -la /opt /srv /root /home 2>/dev/null | head -40

# Ports occupés
ss -tlnp | grep -E ':(80|443|5432|6379|8000)'

# Espace disque (le build Docker en consomme)
df -h /
```

**Conservez la sortie de ces commandes** : elle sert de référence pour le
rollback.

### 4.3 Sauvegarde complète de l'ancien backend

Rien n'est supprimé avant que cette étape soit terminée et vérifiée.

```bash
HORO=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/kharandi-backups/$HORO
cd /opt/kharandi-backups/$HORO

# 1) Base de données de l'ancien backend
#    Adapter le nom du conteneur d'après `docker ps`.
docker exec -t <conteneur_postgres_ancien> \
  pg_dumpall -U kharandi_user | gzip > ancien_dumpall.sql.gz

# 2) Fichiers de configuration et media
tar czf ancien_code.tar.gz -C /opt <ancien_dossier>

# 3) Copie de sécurité des volumes, volume par volume
for v in $(docker volume ls --format '{{.Name}}'); do
  docker run --rm -v "$v":/src -v "$PWD":/dst alpine \
    tar czf "/dst/volume_$v.tar.gz" -C /src . 2>/dev/null \
    && echo "sauvé : $v"
done

# 4) Vérification — un dump vide ou tronqué ne sert à rien
ls -lh
gzip -t *.gz && echo "Archives intègres."
zcat ancien_dumpall.sql.gz | head -20
zcat ancien_dumpall.sql.gz | wc -l   # doit être largement > 100
```

Copiez ensuite ces archives **hors du VPS** :

```bash
# depuis votre machine
scp -r root@212.95.33.158:/opt/kharandi-backups/$HORO ./sauvegarde-kharandi/
```

### 4.4 Arrêt contrôlé de l'ancien backend

```bash
cd /opt/<ancien_dossier>

# Arrêt SANS suppression de volume. Jamais `down -v`.
docker compose stop
docker compose down --remove-orphans   # conteneurs + réseau uniquement

# Contrôle : les volumes de données sont toujours là
docker volume ls
```

Si l'ancien backend n'était pas géré par Docker Compose :

```bash
systemctl stop <service>
systemctl disable <service>
```

### 4.5 Installation du nouveau backend

```bash
# Mettre l'ancien code de côté au lieu de le supprimer
mv /opt/<ancien_dossier> /opt/<ancien_dossier>.ancien_$HORO

mkdir -p /opt/kharandi && cd /opt/kharandi
# Téléverser et décompresser l'archive livrée
unzip -o /root/Backend-Kharandi-corrige.zip
mv Backend-Kharandi-main/* Backend-Kharandi-main/.[!.]* . 2>/dev/null
rmdir Backend-Kharandi-main

chmod +x start.sh start-worker.sh start-beat.sh beat-healthcheck.py deploy/*.sh
```

### 4.6 Fichier `.env` de production

```bash
cd /opt/kharandi
cp .env.production.example .env
chmod 600 .env
nano .env
```

Remplissez chaque valeur marquée `À_GÉNÉRER` ou `À_REMPLIR` (voir section 7),
puis contrôlez avant de démarrer :

```bash
grep -nE 'À_REMPLIR|À_GÉNÉRER' .env    # ne doit rien afficher
grep -E '^(ALLOWED_HOSTS|CORS_ALLOWED_ORIGINS|LENGOPAY_PUBLIC_BASE_URL|ENABLE_HTTPS)=' .env
```

`ENABLE_HTTPS` doit rester à `False` à ce stade : le certificat n'existe pas
encore. `deploy/enable-ssl.sh` le passera à `True` en étape 4.8. L'activer trop
tôt rendrait l'admin Django inaccessible — les cookies de session seraient
marqués « secure » sur une connexion en clair et ne seraient jamais renvoyés.

### 4.7 Démarrage progressif, service par service

Démarrer d'un coup masque l'origine d'une panne. On monte la pile dans l'ordre.

```bash
cd /opt/kharandi

# 1) Construction des images
docker compose build --pull

# 2) PostgreSQL seul
docker compose up -d db
sleep 15
docker compose ps db                       # doit afficher (healthy)
docker compose logs --tail=30 db

# 3) Redis
docker compose up -d redis
docker compose exec -T redis redis-cli ping   # attendu : PONG

# 4) Django — c'est ce service qui applique les migrations
docker compose up -d api
docker compose logs -f api                 # Ctrl-C quand Gunicorn écoute
docker compose exec -T api python manage.py migrate --check && echo "Schéma à jour."

# 5) Worker Celery
docker compose up -d worker
docker compose logs --tail=30 worker       # doit afficher "celery@… ready"

# 6) Celery Beat — le point critique de ce lot
docker compose up -d beat
docker compose logs --tail=40 beat         # doit lister les 7 tâches planifiées
sleep 180                                  # laisser la sonde sortir du start_period
docker compose ps beat                     # doit afficher (healthy)

# 7) Nginx
docker compose up -d nginx
docker compose exec -T nginx nginx -t
docker compose ps
```

### 4.8 HTTPS sur `api.kharandi.gn`

```bash
cd /opt/kharandi
bash deploy/enable-ssl.sh api.kharandi.gn admin@kharandi.gn
```

Le script vérifie le DNS, obtient le certificat, bascule la configuration
Nginx, ajoute le domaine à `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`, passe
`LENGOPAY_PUBLIC_BASE_URL` en `https://api.kharandi.gn`, redémarre `nginx`,
`api`, `worker` et `beat`, puis affiche la nouvelle URL de callback à déclarer
chez LengoPay. En cas d'échec, il indique la commande de restauration exacte.

### 4.9 Sauvegarde automatique quotidienne

```bash
crontab -e
# ajouter :
0 3 * * * cd /opt/kharandi && bash deploy/backup.sh >> /var/log/kharandi-backup.log 2>&1
```

---

## 5. Commandes de vérification

### 5.1 État de la pile

```bash
cd /opt/kharandi
docker compose ps
```

### 5.2 Sondes de santé

```bash
docker compose exec -T nginx wget -qO- http://127.0.0.1:8081/nginx-health
docker compose exec -T nginx wget -qO- http://127.0.0.1/healthz
docker compose exec -T nginx wget -qO- http://127.0.0.1/readyz
curl -fsS https://api.kharandi.gn/healthz
curl -fsS https://api.kharandi.gn/readyz
```

### 5.3 Diagnostic paiements — la commande à retenir

```bash
docker compose exec api python manage.py lengopay_doctor
```

Elle contrôle en 8 sections : configuration, sécurité, **planificateur**,
endpoint de statut LengoPay, journal des callbacks, transactions,
réconciliation. Elle affiche aussi l'URL de callback exacte à déclarer chez
LengoPay.

Diagnostic d'un paiement précis :

```bash
docker compose exec api python manage.py lengopay_doctor --pay-id <PAY_ID>
```

### 5.4 Le planificateur tourne-t-il réellement ?

Trois preuves indépendantes, de la plus faible à la plus forte :

```bash
# a) Le conteneur est sain
docker compose ps beat

# b) Beat émet effectivement les tâches
docker compose logs --tail=50 beat | grep -i "reconciliation-lengopay"

# c) Preuve de bout en bout : Beat → Redis → Worker
docker compose exec api python -c "
from django.core.cache import cache
print(cache.get('kharandi:beat:heartbeat') or 'AUCUN BATTEMENT')
"
```

La preuve (c) est la seule qui compte vraiment : le battement n'apparaît que si
Beat a émis la tâche **et** que le worker l'a exécutée. Il est réécrit chaque
minute.

### 5.5 Test de bout en bout du paiement (à faire avec un vrai petit montant)

```bash
# Avant : état de référence
docker compose exec api python manage.py lengopay_doctor | tail -20
```

1. Faire un paiement réel de petit montant depuis le frontend.
2. Vérifier l'arrivée du callback :

```bash
docker compose logs --tail=100 api | grep -i webhook
docker compose exec api python manage.py lengopay_doctor --pay-id <PAY_ID>
```

3. Vérifier que l'abonnement est bien `ACTIVE`.
4. **Test de la perte de callback** — le plus important. Simulez-le en
   observant une transaction restée `PENDING` : ne faites rien, attendez
   3 minutes, puis :

```bash
docker compose logs --tail=60 worker | grep -i reconcile
docker compose exec api python manage.py lengopay_doctor --pay-id <PAY_ID>
```

L'abonnement doit être activé **sans qu'aucun nouveau callback n'ait été reçu**.

5. **Test du double callback** : rejouez manuellement le même callback.

```bash
curl -sS -X POST "https://api.kharandi.gn/api/v1/payments/webhook/<TOKEN>/" \
  -H 'Content-Type: application/json' \
  -d '{"pay_id":"<PAY_ID>","status":"SUCCESS","amount":<MONTANT>,"message":"Transaction Successful","Client":"<TEL>"}'
```

Réponse attendue : `200`. Puis vérifiez que la date de fin d'abonnement est
**inchangée** et que le journal affiche `DUPLICATE`.

### 5.6 Rotation des logs

```bash
docker inspect kharandi-api-1 --format '{{json .HostConfig.LogConfig}}'
# attendu : max-size 10m, max-file 3
```

---

## 6. Résultats attendus

| Vérification | Résultat attendu |
|---|---|
| `docker compose ps` | 6 services `Up`, `api`/`db`/`redis`/`nginx`/`beat` `(healthy)` |
| `/nginx-health` | `ok` |
| `/healthz` | `200`, JSON `{"status": "ok"}` |
| `/readyz` | `200` (dégradé en `503` si base ou Redis indisponible) |
| `dig api.kharandi.gn` | `212.95.33.158` |
| `curl https://api.kharandi.gn/healthz` | `200`, certificat valide |
| `manage.py migrate --check` | Aucune migration en attente |
| `lengopay_doctor` § planificateur | « Réconciliation planifiée toutes les 3 min » + battement détecté |
| `lengopay_doctor` § endpoint statut | `HTTP 200` (un `401` signifie clé de licence invalide) |
| Battement dans le cache | Horodatage de moins de 2 minutes |
| Paiement réel | Abonnement `ACTIVE` en quelques secondes |
| Callback perdu | Abonnement `ACTIVE` sous 3 minutes, sans intervention |
| Double callback | `200`, `end_date` inchangé, journal `DUPLICATE` |
| Faux `pay_id` | `200`, journal `ORPHAN`, aucune activation |
| Volumes | `postgres_data`, `redis_data`, `media_data`, `static_data`, `beat_data` présents |

Signes d'échec et première action :

| Symptôme | Cause la plus probable | Action |
|---|---|---|
| `beat` reste `unhealthy` | Fichier d'état non écrit | `docker compose logs --tail=80 beat` |
| Aucun battement | Worker arrêté ou Redis muet | `docker compose ps worker` puis `redis-cli ping` |
| Paiements bloqués en `PENDING` | Mode strict + Beat arrêté | Redémarrer `beat`, ne pas désactiver le mode strict |
| `lengopay_doctor` → `401` | Clé de licence | Vérifier `LENGOPAY_LICENSE_KEY` |
| Aucun callback depuis 48 h | URL non déclarée chez LengoPay | Comparer avec l'URL affichée par `lengopay_doctor` |
| Django refuse de démarrer, `kharandi.E0xx` | Configuration dangereuse | Corriger le `.env` : le message indique quoi |

---

## 7. Variables d'environnement — changements

### 7.1 Nouvelles variables

| Variable | Valeur | Rôle |
|---|---|---|
| `LENGOPAY_RECONCILE_EVERY_MIN` | `3` | Cadence de la réconciliation |
| `BEAT_STATE_DIR` | `/app/beat` | Défini dans Compose |
| `BEAT_SCHEDULE_FILE` | `/app/beat/celerybeat-schedule` | Défini dans Compose |
| `BEAT_HEALTH_MAX_AGE` | `600` | Seuil de la sonde |

### 7.2 Valeurs par défaut modifiées

| Variable | Avant | Après |
|---|---|---|
| `LENGOPAY_REQUIRE_STATUS_CONFIRMATION` | `False` | **`True`** |
| `LENGOPAY_PUBLIC_BASE_URL` | `http://212.95.33.158` | `https://api.kharandi.gn` |
| `ENABLE_HTTPS` | `False` | `True` (après `enable-ssl.sh`) |

### 7.3 Secrets à régénérer obligatoirement

L'ancien backend a pu exposer ces valeurs. Générez-les toutes à neuf :

```bash
echo "SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n=' )"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"
echo "LENGOPAY_CALLBACK_TOKEN=$(openssl rand -hex 32)"
echo "CRON_SECRET=$(openssl rand -hex 24)"
```

`LENGOPAY_LICENSE_KEY` doit être **récupérée depuis le portail LengoPay**, pas
générée. Si l'ancien backend est compromis ou si la clé a circulé, demandez sa
rotation à LengoPay.

⚠️ Si vous changez `POSTGRES_PASSWORD` alors que vous **conservez le volume
PostgreSQL existant**, le mot de passe du volume ne change pas
automatiquement : PostgreSQL ne relit `POSTGRES_PASSWORD` qu'à
l'initialisation. Faites-le explicitement :

```bash
docker compose exec -T db psql -U kharandi_user -d kharandi_db \
  -c "ALTER USER kharandi_user WITH PASSWORD 'NOUVEAU_MOT_DE_PASSE';"
# puis mettre la même valeur dans .env, puis :
docker compose up -d api worker beat
```

Oublier cette étape provoque une erreur d'authentification au démarrage de
l'API — sans perte de données.

### 7.4 Valeurs de production à vérifier

```env
DEBUG=False
ALLOWED_HOSTS=api.kharandi.gn,212.95.33.158
CORS_ALLOWED_ORIGINS=https://kharandi.gn,https://www.kharandi.gn
CSRF_TRUSTED_ORIGINS=https://api.kharandi.gn,https://kharandi.gn,https://www.kharandi.gn
FRONTEND_URL=https://kharandi.gn
ENABLE_HTTPS=True
LENGOPAY_PUBLIC_BASE_URL=https://api.kharandi.gn
LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True
```

Retirez les origines `http://localhost:*` de `CORS_ALLOWED_ORIGINS` en
production — `lengopay_doctor` les signale (`kharandi.W005`).

---

## 8. Changements Vercel ↔ backend

Aucun fichier Vercel n'a été modifié. Trois actions dans l'interface Vercel,
après que `https://api.kharandi.gn/healthz` réponde.

**8.1 Variable d'environnement.** Project Settings → Environment Variables, sur
`Production` **et** `Preview` :

```
VITE_API_URL = https://api.kharandi.gn/api/v1
```

Le nom exact dépend de votre frontend (`VITE_API_URL`, `NEXT_PUBLIC_API_URL`,
`REACT_APP_API_URL`…). Conservez le nom déjà utilisé.

**8.2 Redéploiement.** Les variables ne sont injectées qu'au build : un
redéploiement est indispensable. Deployments → dernier déploiement →
Redeploy, **sans** cache de build.

**8.3 Vérifications côté navigateur.**

- Console : aucune erreur `Mixed Content`. Toute requête vers
  `http://212.95.33.158` indique une URL codée en dur dans le frontend, à
  corriger dans le code — pas côté backend.
- Onglet Réseau : les appels partent bien vers `https://api.kharandi.gn`.
- Aucune occurrence de la clé de licence LengoPay dans le bundle :

```bash
# depuis votre machine, sur le code frontend
grep -rn "LENGOPAY_LICENSE\|licenseKey\|websiteid" src/ | grep -v node_modules
```

`websiteid` côté frontend est acceptable (identifiant public). La **clé de
licence ne doit jamais y figurer**.

**8.4 Déclaration de l'URL de callback chez LengoPay.** Étape indispensable et
souvent oubliée : LengoPay continuera d'appeler l'ancienne URL tant qu'elle
n'est pas remplacée dans le portail.

```bash
docker compose exec api python manage.py lengopay_doctor | grep -A2 "Rappel"
```

Reportez l'URL affichée dans le portail LengoPay, en remplacement de
l'ancienne en `http://212.95.33.158/...`.

---

## 9. Procédure de rollback non destructive

Aucune étape ne supprime de données. À tout moment, on peut revenir en arrière.

### 9.1 Retour au code précédent (le plus fréquent)

`deploy/update.sh` sauvegarde la configuration dans
`/opt/kharandi-backups/config_<horodatage>/` avant toute modification.

```bash
cd /opt/kharandi
ls -1t /opt/kharandi-backups/ | head
CFG=/opt/kharandi-backups/config_<horodatage>

cp -a "$CFG/nginx/." nginx/
cp -a "$CFG/docker-compose.yml" docker-compose.yml
cp -a "$CFG/.env" .env
docker compose up -d --remove-orphans
```

### 9.2 Retour à l'ancien backend complet

```bash
cd /opt/kharandi
docker compose stop            # jamais `down -v`

cd /opt/<ancien_dossier>.ancien_$HORO
docker compose up -d
docker compose ps
```

Les volumes de l'ancien backend n'ayant jamais été supprimés, il redémarre avec
ses données intactes.

### 9.3 Restauration d'un dump PostgreSQL

À n'utiliser qu'en cas de corruption réelle des données. La restauration
**écrase** le contenu actuel : sauvegardez l'état présent d'abord.

```bash
cd /opt/kharandi

# 1) Sauvegarder l'état actuel AVANT de le remplacer
docker compose exec -T db pg_dump -U kharandi_user kharandi_db \
  | gzip > /opt/kharandi-backups/avant_restauration_$(date +%s).sql.gz

# 2) Arrêter les écritures, garder la base debout
docker compose stop api worker beat

# 3) Restaurer
zcat /opt/kharandi-backups/<HORO>/ancien_dumpall.sql.gz \
  | docker compose exec -T db psql -U kharandi_user -d kharandi_db

# 4) Redémarrer
docker compose up -d api worker beat
docker compose exec -T api python manage.py migrate --check
```

### 9.4 Neutraliser le mode strict en urgence

Si l'API LengoPay est durablement indisponible et que des paiements
s'accumulent :

```bash
cd /opt/kharandi
sed -i 's|^LENGOPAY_REQUIRE_STATUS_CONFIRMATION=.*|LENGOPAY_REQUIRE_STATUS_CONFIRMATION=False|' .env
docker compose up -d api worker beat
```

⚠️ Mesure temporaire uniquement. Dans cet état, un faux callback portant le bon
jeton peut activer un abonnement. **Rétablissez `True` dès que l'API
répond** et vérifiez le journal des callbacks appliqués pendant la fenêtre :

```bash
docker compose exec api python manage.py lengopay_doctor
```

Ne désactivez jamais ce mode « pour simplifier » : la réconciliation
automatique rend cette désactivation inutile dans le fonctionnement normal.

### 9.5 Rollback DNS et Vercel

```bash
# Revenir sur Vercel à l'ancienne valeur d'API, puis Redeploy.
# L'enregistrement A `api` peut rester en place : il ne gêne pas
# kharandi.gn ni www.kharandi.gn, qui pointent toujours vers Vercel.
```

---

## Ce qui reste à faire de votre côté

1. Créer l'enregistrement DNS `api.kharandi.gn` → `212.95.33.158`.
2. Exécuter l'inventaire lecture seule de la section 4.2 et me transmettre la
   sortie si vous voulez que j'adapte la procédure à ce qui tourne réellement.
3. Décider du sort des données de l'ancien backend : à reprendre dans la
   nouvelle base, ou à archiver seulement.
4. Régénérer les secrets de la section 7.3.
5. Récupérer la clé de licence LengoPay depuis le portail.
6. Déclarer la nouvelle URL de callback chez LengoPay.

## Sources

- Documentation LengoPay que vous avez fournie (création de paiement, endpoint
  de statut, format du callback).
- Paquet de référence [lengopay_flutter sur pub.dev](https://pub.dev/packages/lengopay_flutter),
  utilisé pour vérifier l'absence de signature HMAC et le format exact de
  `POST /transaction/status`.
- Comportement de synchronisation du planificateur constaté directement dans la
  version de Celery installée (`celery.beat.Scheduler.sync_every = 180`).
