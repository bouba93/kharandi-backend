# Correctif LengoPay — Callback de paiement

Backend Kharandi · Django 5 / DRF · VPS `212.95.33.158`
Correctif appliqué et validé le 12 août 2026.

---

## 1. Cause exacte du problème

Le callback LengoPay arrivait **bien** sur le serveur, mais il était
**systématiquement rejeté sans jamais activer l'abonnement**. Il ne s'agissait
pas d'un problème réseau, ni de pare-feu, ni de DNS : le bogue était dans le
code.

### La cause racine

Le fichier `payments/views.py` contenait :

```python
LENGOPAY_URL = "https://portal.lengopay.com/api/v1/payments"

def _lengopay_status(pay_id):
    r = requests.get(f"{LENGOPAY_URL}/{pay_id}", headers=..., timeout=15)
```

**Cet endpoint n'existe pas.** La documentation officielle LengoPay ne prévoit
aucun `GET /api/v1/payments/{pay_id}`. La vérification du statut se fait par un
**POST** sur `/api/v1/transaction/status` avec le corps
`{"pay_id": ..., "websiteid": ...}`.

Vérification empirique effectuée pendant ce correctif :

| Requête | Réponse réelle |
|---|---|
| `GET https://portal.lengopay.com/api/v1/payments/<pay_id>` | **HTTP 404** (page HTML « 404 - Page introuvable ») |
| `POST https://portal.lengopay.com/api/v1/transaction/status` | **HTTP 401** `{"error":"Unauthorized !"}` → la route existe, seule la clé de test était invalide |
| `POST https://portal.lengopay.com/api/v1/payments` | **HTTP 401** `{"error":"Unauthorized !"}` → la route existe |

`_lengopay_status()` retournait donc **toujours** `(None, None)`.

### L'enchaînement fatal

`PaymentWebhookView.post()` exigeait, pour appliquer un paiement, **l'une** de
ces deux conditions :

1. une **signature HMAC valide** — impossible : `LENGOPAY_WEBHOOK_SECRET` est
   vide, car **LengoPay ne signe pas ses callbacks** (aucune signature n'existe
   dans sa documentation). `_verify_signature()` retournait donc toujours
   `False` ;
2. **ou** une confirmation par l'API — impossible, à cause du mauvais endpoint
   ci-dessus.

Les deux chemins échouant à 100 %, la vue journalisait « Callback NON vérifié »
et renvoyait :

```json
HTTP 200 {"received": true, "verified": false}
```

… **sans activer l'abonnement, sans confirmer la commande**. Le HTTP 200
indiquait à LengoPay que tout allait bien : aucun rejeu n'était déclenché. La
transaction restait `PENDING` **pour toujours**, alors que l'argent était bel et
bien encaissé.

Pire : la tâche de réconciliation (`payments/cron.py`) appelait **la même
fonction cassée**, elle ne pouvait donc rien rattraper. Aucun filet de sécurité.

### Défauts aggravants corrigés au passage

| # | Défaut | Conséquence |
|---|---|---|
| 1 | Aucun mécanisme d'authentification exploitable du callback | Soit on refusait tout (le cas), soit il fallait faire aveuglément confiance à n'importe quel POST public → activation d'abonnements non payés |
| 2 | Aucune journalisation de la charge utile brute | Panne indiagnosticable : aucune trace de ce que LengoPay envoyait réellement |
| 3 | Champ `Client` (numéro du payeur) ignoré | Impossible de rapprocher un paiement d'un numéro Mobile Money |
| 4 | Seule l'URL `webhook/` avec slash existait | Un POST sur `…/webhook` → **301** `APPEND_SLASH` → **corps de requête perdu** |
| 5 | `RateLimitMiddleware` s'appliquait au webhook | Une rafale de callbacks pouvait être bloquée en 429 |
| 6 | Course d'exécution non gérée | Un callback Mobile Money arrivant avant l'enregistrement du `gateway_ref` était définitivement perdu |
| 7 | `nginx/kharandi-ssl.conf.template` redirigeait `location /` en 301 sur le port 80 | À la future activation HTTPS, **tous les callbacks POST auraient été détruits** |
| 8 | Aucun contrôle du montant | Un callback annonçant 100 GNF pouvait activer un abonnement à 50 000 GNF |

---

## 2. Liste des fichiers modifiés

### Nouveaux fichiers

| Fichier | Rôle |
|---|---|
| `payments/lengopay.py` | Client HTTP LengoPay strictement conforme à la documentation officielle |
| `payments/migrations/0003_paymentcallback.py` | Migration **additive uniquement** (2 index + 1 table) |
| `payments/admin.py` | Journal des callbacks dans l'admin, en lecture seule |
| `payments/tests.py` | **22 tests** de non-régression du callback |
| `payments/management/commands/lengopay_doctor.py` | Commande de diagnostic en une ligne |
| `payments/_doctor_helpers.py` | Contrôles utilisés par la commande de diagnostic |
| `payments/management/__init__.py`, `payments/management/commands/__init__.py` | Paquets Python requis par Django |

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `kharandi_backend/settings.py` | Bloc LengoPay réécrit et documenté : nouveaux réglages, endpoints corrects, jeton de callback, construction automatique de l'URL |
| `payments/views.py` | `PaymentWebhookView` entièrement réécrite ; `_call_lengopay` et `_lengopay_status` délèguent au nouveau client ; ajout de `notify_payment_result()`, `claim_orphan_callbacks()` et `CallbackLogView` |
| `payments/models.py` | Nouveau modèle `PaymentCallback` ; 2 index sur `Transaction` (`gateway_ref`, `status`+`created_at`) |
| `payments/cron.py` | Réconciliation réécrite ; ajout du rejeu des callbacks orphelins |
| `payments/urls.py` | Routes `webhook/<token>/`, variantes sans slash, `callbacks/` |
| `core/middleware.py` | Le webhook est exempté du rate limiting |
| `nginx/kharandi-ssl.conf.template` | Exception explicite : le webhook n'est pas redirigé en 301 sur le port 80 |
| `deploy/make-env.sh` | Génère automatiquement `LENGOPAY_CALLBACK_TOKEN` et affiche l'URL exacte à déclarer chez LengoPay |
| `.env.yigui.example` | Documente les 10 nouvelles variables |

**Aucun fichier supprimé. Aucune modification du frontend, de Vercel ou du DNS.
Aucune opération destructive sur la base de données.**

---

## 3. Contenu des éléments importants

### 3.1 Le client LengoPay — `payments/lengopay.py`

Conforme à la documentation officielle, section « Collect payments (Cash In) ».

**Création d'un paiement** — `POST {base}/payments`

```python
headers = {
    "Authorization": f"Basic {settings.LENGOPAY_LICENSE_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
body = {
    "websiteid":    settings.LENGOPAY_SITE_ID,
    "amount":       int(montant.to_integral_value()),  # GNF/XOF : pas de sous-unité
    "currency":     "GNF",
    "country":      "GN",
    "callback_url": settings.LENGOPAY_CALLBACK_URL,
    "return_url":   f"{settings.FRONTEND_URL}/payment/success?ref={reference}",
    "failure_url":  f"{settings.FRONTEND_URL}/payment/failure?ref={reference}",
}
```

**Vérification du statut — LA correction centrale** — `POST {base}/transaction/status`

```python
def transaction_status(pay_id: str):
    # Compatibilité ascendante : une ancienne configuration pouvait contenir un
    # gabarit « …/payments/{pay_id} ». Ce format n'existe pas : on le corrige.
    if "{pay_id}" in url:
        url = f"{settings.LENGOPAY_BASE_URL}/transaction/status"

    body = {"pay_id": pay_id, "websiteid": settings.LENGOPAY_SITE_ID}
    resp = requests.post(url, json=body, headers=_headers(), timeout=...)
    ...
    return normalize_status(data.get("status")), to_decimal(data.get("amount"))
```

Cette fonction retourne `(None, None)` quand la vérification **n'aboutit pas**
(API injoignable, HTTP ≠ 200, statut non documenté). Ce `None` signifie
« je ne sais pas », **jamais** « le paiement a échoué » — c'est précisément la
confusion qui bloquait les transactions.

`normalize_status()` traduit tous les libellés observés vers trois valeurs
canoniques (`SUCCESS` / `FAILED` / `PENDING`) et retourne `None` pour un libellé
inconnu, plutôt que de deviner.

`extract_phone()` accepte les trois graphies du numéro du payeur rencontrées
dans les différentes versions de l'API : `Client` (documentation officielle),
`client` (documentation du paquet) et `account` (Cash In v2).

### 3.2 Le webhook — `payments/views.py`

Nouvelle logique de décision, en cascade :

```
1. AUTHENTIFICATION
   jeton d'URL valide (comparaison en temps constant)  → auth = "url_token"
   sinon signature HMAC valide (si un secret existe)   → auth = "hmac"
   sinon                                               → auth = ""

2. CONFIRMATION (au mieux, non bloquante)
   api_state, api_amount = transaction_status(pay_id)

3. STATUT RETENU
   si l'API a répondu            → l'API fait foi
                                   (écart avec le statut annoncé = alerte fraude)
   sinon si l'appel est authentifié → statut annoncé accepté
   sinon                          → RIEN n'est appliqué, laissé au cron

4. CONTRÔLE DU MONTANT
   |montant_transaction − montant_reçu| > LENGOPAY_AMOUNT_TOLERANCE
       → refus d'activation, journalisé en MISMATCH

5. APPLICATION, sous verrou et idempotente
   select_for_update()
   déjà SUCCESS  → DUPLICATE, aucune action
   déjà REFUNDED → ignoré
   SUCCESS       → activation de l'abonnement + confirmation de la commande

6. EFFETS SECONDAIRES NON BLOQUANTS
   SMS + notification temps réel : une panne Redis/Celery ne doit JAMAIS
   renvoyer une erreur, sinon LengoPay rejouerait en boucle un paiement
   déjà encaissé.
```

Codes de retour : **200** dès que la charge utile est exploitable (LengoPay ne
rejoue pas inutilement), **400** si `pay_id` ou `status` est absent ou
illisible, **500** uniquement sur erreur interne — cas où le rejeu par LengoPay
est justement souhaitable puisque rien n'a été enregistré.

**Authentification, puisque LengoPay ne signe pas.** Un jeton secret est placé
dans l'URL de callback :

```
POST http://212.95.33.158/api/v1/payments/webhook/<LENGOPAY_CALLBACK_TOKEN>/
```

Seul un émetteur connaissant l'URL complète peut déclencher une activation. Ce
jeton est complété par deux garde-fous : la confirmation serveur-à-serveur
auprès de LengoPay et le contrôle du montant.

### 3.3 Journal des callbacks — `payments/models.py`

Chaque appel reçu est tracé, quel qu'en soit le sort :

```python
class PaymentCallback(models.Model):
    class Outcome(models.TextChoices):
        APPLIED    = "APPLIED"      # statut appliqué
        DUPLICATE  = "DUPLICATE"    # déjà traité
        PENDING    = "PENDING"      # paiement encore en cours
        ORPHAN     = "ORPHAN"       # gateway_ref inconnu → à rejouer
        UNVERIFIED = "UNVERIFIED"   # ni authentifié ni confirmé
        MISMATCH   = "MISMATCH"     # montant incohérent
        INVALID    = "INVALID"      # charge utile illisible
        ERROR      = "ERROR"        # erreur interne

    pay_id, transaction, announced_status, applied_status, outcome,
    auth_method, source_ip, payload (JSON brut), detail, replayed, created_at
```

C'est ce qui manquait le plus : sans ce journal, un « souci de callback » est
indiagnosticable.

### 3.4 Routes — `payments/urls.py`

```python
path("webhook/",                PaymentWebhookView.as_view()),
path("webhook",                 PaymentWebhookView.as_view()),   # pas de 301
path("webhook/<str:token>/",    PaymentWebhookView.as_view()),
path("webhook/<str:token>",     PaymentWebhookView.as_view()),   # pas de 301
path("callbacks/",              CallbackLogView.as_view()),      # admin
```

Les variantes sans slash sont **indispensables** : sur un POST, `APPEND_SLASH`
provoque une redirection 301 qui fait perdre le corps de la requête — donc la
notification de paiement.

### 3.5 Nginx — `nginx/kharandi-ssl.conf.template`

```nginx
server {
    listen 80;
    server_name __DOMAIN__;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }

    # EXCEPTION DÉLIBÉRÉE : le callback LengoPay ne doit JAMAIS être redirigé.
    # Une 301 sur un POST fait perdre le corps de la requête, donc le paiement.
    location ^~ /api/v1/payments/webhook {
        proxy_pass http://$kharandi_api;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location / { return 301 https://__DOMAIN__$request_uri; }
}
```

Ce point est préventif : il garantit que l'activation future d'HTTPS ne cassera
pas les paiements.

---

## 4. Commandes exactes à exécuter sur le VPS

Aucune de ces commandes n'est destructive. Les volumes `postgres_data`,
`redis_data`, `media_data`, `static_data` ne sont **jamais** touchés.

```bash
ssh root@212.95.33.158
cd /opt/kharandi

# ── 4.1 Sauvegarde préalable (obligatoire) ───────────────────────────────────
bash deploy/backup.sh
cp .env /opt/kharandi-backups/.env.avant-correctif-lengopay
docker compose exec -T db pg_dump -U kharandi_user kharandi_db \
  | gzip > /opt/kharandi-backups/avant-lengopay-$(date +%F-%H%M).sql.gz
ls -lh /opt/kharandi-backups/ | tail -5

# ── 4.2 Récupération du code corrigé ─────────────────────────────────────────
git stash list                       # vérifier qu'aucun travail local ne traîne
git pull

# ── 4.3 Génération du jeton de callback ──────────────────────────────────────
NOUVEAU_JETON=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "JETON : $NOUVEAU_JETON"        # à conserver hors du serveur

# Ajout dans .env, en supprimant d'abord les anciennes valeurs si elles existent
sed -i '/^LENGOPAY_CALLBACK_TOKEN=/d;/^LENGOPAY_PUBLIC_BASE_URL=/d' .env
sed -i '/^LENGOPAY_BASE_URL=/d;/^LENGOPAY_STATUS_URL=/d;/^LENGOPAY_PAYMENT_URL=/d' .env
sed -i '/^LENGOPAY_CALLBACK_URL=/d;/^LENGOPAY_TIMEOUT=/d' .env
sed -i '/^LENGOPAY_REQUIRE_STATUS_CONFIRMATION=/d;/^LENGOPAY_AMOUNT_TOLERANCE=/d' .env

cat >> .env <<EOF

# ─── LengoPay — correctif callback du 12/08/2026 ──────────────────────────────
LENGOPAY_BASE_URL=https://portal.lengopay.com/api/v1
LENGOPAY_CALLBACK_TOKEN=${NOUVEAU_JETON}
LENGOPAY_PUBLIC_BASE_URL=http://212.95.33.158
LENGOPAY_REQUIRE_STATUS_CONFIRMATION=False
LENGOPAY_AMOUNT_TOLERANCE=1
LENGOPAY_TIMEOUT=20
EOF

chmod 600 .env
grep LENGOPAY .env                   # relire avant de continuer

# ── 4.4 Reconstruction et migration (additive) ───────────────────────────────
docker compose build api worker
docker compose run --rm api python manage.py migrate --plan   # LIRE le plan
docker compose run --rm api python manage.py migrate
docker compose up -d api worker nginx

# ── 4.5 Diagnostic intégré ───────────────────────────────────────────────────
docker compose exec api python manage.py lengopay_doctor
```

La dernière commande affiche notamment **l'URL de callback exacte à déclarer
dans votre tableau de bord LengoPay**. C'est l'étape la plus importante :

```
http://212.95.33.158/api/v1/payments/webhook/<VOTRE_JETON>/
```

> **Sans cette déclaration côté LengoPay, rien ne fonctionnera** : LengoPay
> continuerait d'appeler l'ancienne URL sans jeton, et les callbacks seraient
> classés `UNVERIFIED` (donc non appliqués, mais désormais **tracés et
> rattrapables**, ce qui n'était pas le cas avant).

### 4.6 Rattrapage des paiements bloqués

Les transactions historiquement coincées en `PENDING` peuvent être récupérées
sans aucune intervention manuelle en base :

```bash
docker compose exec api python manage.py lengopay_doctor --reconcile --hours 720
```

Cette commande interroge LengoPay transaction par transaction et applique les
statuts réels. Elle est idempotente : elle peut être relancée sans risque.

---

## 5. Commandes de vérification

```bash
# 5.1 Aucun problème de configuration Django
docker compose exec api python manage.py check

# 5.2 Suite de tests du callback (22 tests)
docker compose exec api python manage.py test payments -v 2

# 5.3 Diagnostic complet
docker compose exec api python manage.py lengopay_doctor

# 5.4 L'URL de callback est joignable de l'extérieur (depuis votre machine)
JETON="<votre_jeton>"
curl -i http://212.95.33.158/api/v1/payments/webhook/$JETON/

# 5.5 Simulation d'un callback réel, avec la charge utile officielle
#     Remplacer <PAY_ID> par le gateway_ref d'une transaction PENDING réelle.
curl -i -X POST http://212.95.33.158/api/v1/payments/webhook/$JETON/ \
  -H "Content-Type: application/json" \
  -d '{"pay_id":"<PAY_ID>","status":"SUCCESS","amount":50000,
       "message":"Transaction Successful","Client":"624897845"}'

# 5.6 Un appel SANS jeton doit être refusé (contrôle de sécurité)
curl -i -X POST http://212.95.33.158/api/v1/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"pay_id":"faux","status":"SUCCESS","amount":50000}'

# 5.7 Le journal des callbacks (jeton admin requis)
curl -s http://212.95.33.158/api/v1/payments/callbacks/?limit=20 \
  -H "Authorization: Bearer <JETON_ADMIN>" | python3 -m json.tool

# 5.8 Journaux applicatifs en direct
docker compose logs -f --tail=100 api | grep -i "lengopay\|webhook\|callback"

# 5.9 Le webhook n'est pas soumis au rate limiting
for i in $(seq 1 40); do
  curl -s -o /dev/null -w "%{http_code} " \
    -X POST http://212.95.33.158/api/v1/payments/webhook/$JETON/ \
    -H "Content-Type: application/json" -d '{}'
done; echo
```

Vérification en base, en lecture seule :

```bash
docker compose exec -T db psql -U kharandi_user -d kharandi_db <<'SQL'
SELECT outcome, count(*) FROM payments_paymentcallback GROUP BY outcome;
SELECT created_at, pay_id, outcome, announced_status, applied_status, auth_method
  FROM payments_paymentcallback ORDER BY created_at DESC LIMIT 20;
SELECT status, count(*) FROM payments_transaction GROUP BY status;
SQL
```

---

## 6. Résultats attendus

| Vérification | Résultat attendu |
|---|---|
| 5.1 `check` | `System check identified no issues (0 silenced).` |
| 5.2 tests | `Ran 22 tests … OK` |
| 5.3 diagnostic | Section 1 en `OK`, section 2 : `HTTP 200` (ou `400`/`404` sur un `pay_id` factice — la route répond, c'est l'essentiel). Un **`HTTP 401` signifie que `LENGOPAY_LICENSE_KEY` est invalide** |
| 5.4 `curl` GET | `HTTP/1.1 200 OK` + `{"detail":"Endpoint de callback LengoPay actif. Utiliser POST."}` |
| 5.5 callback authentifié | `HTTP/1.1 200 OK` + `{"received":true,"status":"SUCCESS"}` ; la transaction passe à `SUCCESS`, l'abonnement à `ACTIVE` avec une `end_date`, la commande à `PAID` |
| 5.6 callback sans jeton | `HTTP/1.1 200 OK` + `{"received":true,"verified":false}` ; **aucune** activation ; une ligne `UNVERIFIED` dans le journal |
| 5.7 journal | Liste JSON des callbacks avec leur `outcome` |
| 5.9 rate limit | 40 réponses, **aucun `429`** |

Signature dans les journaux d'un callback correctement appliqué :

```
INFO  Webhook LengoPay | pay_id=… | statut annoncé='SUCCESS' | ip=…
INFO  Callback … appliqué : SUCCESS (api).
```

Les messages `Callback NON vérifié` ne doivent plus apparaître pour un callback
authentifié.

---

## 7. Changements de variables d'environnement

### À ajouter — obligatoire

| Variable | Valeur | Rôle |
|---|---|---|
| `LENGOPAY_CALLBACK_TOKEN` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` | **Authentifie le callback.** LengoPay ne signant pas ses notifications, c'est le seul élément qui empêche un tiers d'activer un abonnement non payé |
| `LENGOPAY_PUBLIC_BASE_URL` | `http://212.95.33.158` | Base publique servant à construire l'URL de callback |

### À ajouter — recommandé

| Variable | Défaut | Rôle |
|---|---|---|
| `LENGOPAY_BASE_URL` | `https://portal.lengopay.com/api/v1` | Racine de l'API. Sandbox : `https://sandbox.lengopay.com/api/v1` |
| `LENGOPAY_REQUIRE_STATUS_CONFIRMATION` | `False` | `True` = n'appliquer un callback que si l'API le confirme. Plus strict, mais une panne de l'API repousse l'activation au passage du cron |
| `LENGOPAY_AMOUNT_TOLERANCE` | `1` | Écart de montant toléré, en unités de devise |
| `LENGOPAY_TIMEOUT` | `20` | Délai maximal des appels HTTP vers LengoPay |

### À supprimer

| Variable | Raison |
|---|---|
| `LENGOPAY_STATUS_URL=https://portal.lengopay.com/api/v1/payments/{pay_id}` | **Endpoint inexistant : c'est la cause du bogue.** Le code corrige automatiquement cette valeur héritée, mais autant l'enlever |
| `LENGOPAY_CALLBACK_URL=http://212.95.33.158/api/v1/payments/webhook/` | Désormais construite automatiquement avec le jeton. Ne la renseigner que pour forcer une URL différente |

### Inchangées

`LENGOPAY_SITE_ID` (`websiteid`), `LENGOPAY_LICENSE_KEY`, `LENGOPAY_CURRENCY`
(`GNF`), `LENGOPAY_COUNTRY` (`GN`), `LENGOPAY_WEBHOOK_SECRET` (laisser vide :
LengoPay ne fournit pas de signature).

### Action côté LengoPay — indispensable

Dans le tableau de bord marchand LengoPay, remplacer l'URL de callback par :

```
http://212.95.33.158/api/v1/payments/webhook/<LENGOPAY_CALLBACK_TOKEN>/
```

---

## 8. Changements côté Vercel et liaison frontend ↔ backend

**Aucun changement n'est nécessaire. Aucun fichier frontend, aucune
configuration Vercel, aucun enregistrement DNS n'a été touché.**

- Le contrat de l'API d'initiation est **inchangé** : le frontend continue
  d'appeler `POST /api/v1/subscriptions/initiate/` et
  `POST /api/v1/payments/initiate/` et reçoit la même réponse
  (`payment_url`, `reference`).
- `return_url` et `failure_url` pointent toujours vers `FRONTEND_URL`
  (`https://kharandi.gn`), c'est-à-dire Vercel. Le parcours utilisateur est
  identique : redirection vers LengoPay, puis retour sur le site Vercel.
- Le `callback_url` est une communication **serveur-à-serveur** entre LengoPay
  et le VPS. Le frontend n'y participe pas, Vercel n'est pas concerné.
- `CORS_ALLOWED_ORIGINS` et `CSRF_TRUSTED_ORIGINS` sont inchangés.

Un seul point d'attention, non bloquant : la page de retour Vercel affiche
l'état du paiement en interrogeant `GET /api/v1/payments/transactions/`. Comme
le callback LengoPay peut arriver quelques secondes après le retour de
l'utilisateur, cette page doit **rafraîchir le statut** (interrogation toutes
les 3 s pendant ~30 s) plutôt que de conclure « échec » sur une première réponse
`PENDING`. C'est un ajustement d'affichage côté frontend, indépendant de ce
correctif.

---

## 9. Procédure de rollback non destructive

Aucune donnée n'est perdue, dans un sens comme dans l'autre. La migration
`0003` est **purement additive** (deux index + une table) : elle ne modifie ni
ne supprime aucune donnée métier existante.

### Retour en arrière du code — recommandé

```bash
ssh root@212.95.33.158
cd /opt/kharandi

git log --oneline -5                 # repérer le commit précédent
git checkout <COMMIT_PRECEDENT>

cp /opt/kharandi-backups/.env.avant-correctif-lengopay .env
chmod 600 .env

docker compose build api worker
docker compose up -d api worker nginx
docker compose ps
```

**La migration `0003` peut rester en place** : l'ancien code ignore simplement
la table `payments_paymentcallback` et les nouveaux index. C'est l'option la
plus sûre, et elle conserve le journal des callbacks reçus — précieux pour
comprendre ce qui s'est passé.

### Retour en arrière de la migration — uniquement si nécessaire

```bash
docker compose exec api python manage.py migrate payments 0002 --plan   # LIRE
docker compose exec api python manage.py migrate payments 0002
```

Cette opération supprime la table `payments_paymentcallback` (journal de
diagnostic) et deux index. **Aucune table métier n'est touchée** :
`payments_transaction`, `payments_subscription` et `payments_plan` restent
intactes. Le journal étant la seule trace des callbacks reçus, exportez-le
avant :

```bash
docker compose exec -T db psql -U kharandi_user -d kharandi_db \
  -c "\copy (SELECT * FROM payments_paymentcallback) TO STDOUT WITH CSV HEADER" \
  > /opt/kharandi-backups/callbacks-export-$(date +%F).csv
```

### Rollback partiel — le plus souple

Si le comportement du callback vous semble trop permissif ou trop strict,
**aucun retour de code n'est nécessaire** : deux variables suffisent.

```bash
# Mode strict : n'appliquer un callback que si l'API LengoPay le confirme
sed -i 's/^LENGOPAY_REQUIRE_STATUS_CONFIRMATION=.*/LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True/' .env

# Neutraliser le contrôle de jeton (revenir au comportement historique)
sed -i 's/^LENGOPAY_CALLBACK_TOKEN=.*/LENGOPAY_CALLBACK_TOKEN=/' .env

docker compose up -d api worker
```

### À ne jamais faire

```bash
docker compose down -v          # ❌ détruit postgres_data
docker volume rm …              # ❌
manage.py migrate payments zero # ❌ supprimerait les tables de paiement
DROP DATABASE / DROP TABLE      # ❌
```

---

## Recommandation complémentaire — HTTPS, optionnelle

Le jeton de callback circule aujourd'hui **en clair sur HTTP**, puisqu'aucun
certificat ne peut être émis pour une adresse IP nue. C'est acceptable — le
contrôle du montant et la confirmation serveur-à-serveur limitent fortement
l'impact d'une interception — mais ce n'est pas idéal.

Le passage en HTTPS suppose **une décision DNS de votre part**, que ce correctif
ne prend pas : faire pointer un sous-domaine, par exemple `api.kharandi.gn`,
vers `212.95.33.158`. Cela ne touche **ni** `kharandi.gn`, **ni**
`www.kharandi.gn`, donc **ni Vercel**.

```bash
# 1. Créer l'enregistrement DNS : api.kharandi.gn  A  212.95.33.158
# 2. Sur le VPS :
bash deploy/enable-ssl.sh api.kharandi.gn admin@kharandi.gn
sed -i 's|^LENGOPAY_PUBLIC_BASE_URL=.*|LENGOPAY_PUBLIC_BASE_URL=https://api.kharandi.gn|' .env
docker compose up -d api worker nginx
docker compose exec api python manage.py lengopay_doctor
# 3. Mettre à jour l'URL de callback dans le tableau de bord LengoPay.
```

L'exception nginx du point 3.5 garantit que cette bascule ne cassera pas les
callbacks.

---

## Validation effectuée

Cette correction n'a pas seulement été écrite, elle a été **exécutée** :

- `manage.py check` → aucun problème ;
- `manage.py makemigrations --check` → « No changes detected » : la migration
  écrite à la main correspond exactement aux modèles ;
- `manage.py test payments` → **22 tests, tous passants**, dont : callback
  appliqué même quand l'API de statut est muette, callback sans jeton refusé,
  jeton erroné refusé, montant incohérent refusé, statut de l'API prioritaire
  sur le statut annoncé, idempotence sur rejeu, URL sans slash final,
  enregistrement du champ `Client`, callback orphelin conservé puis rejoué,
  réconciliation d'un paiement dont le callback a été perdu, conformité exacte
  du corps des requêtes de création et de statut ;
- endpoints LengoPay testés en réel : `POST /transaction/status` et
  `POST /payments` répondent (401 avec une clé factice), `GET /payments/{pay_id}`
  renvoie **404** — la cause racine est confirmée empiriquement.

### Sources

- Documentation officielle LengoPay (fournie), section « Collect payments
  (Cash In) » : création, statut de transaction, callback, Cash In v2.
- Paquet [`lengopay_flutter` sur pub.dev](https://pub.dev/packages/lengopay_flutter)
  version 1.3.0 — implémentation de référence des endpoints, des en-têtes et de
  la charge utile du callback.
- [Exemple d'intégration du paquet](https://pub.dev/packages/lengopay_flutter/example).
