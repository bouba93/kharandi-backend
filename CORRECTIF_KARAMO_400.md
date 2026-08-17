# Correctif Karamo — HTTP 400 sur `/api/v1/ai/ask/` et `/api/v1/ai/ask/stream/`

Backend Django Kharandi · application `ai_features`
Correction backend uniquement. Aucune modification du frontend, de Vercel, des
migrations, des données BAC ni de `learning.Document`.

---

## 1. Avertissement méthodologique

Ce document ne contient que ce qui est **vérifiable dans le code backend que vous
avez fourni**. Deux points dépendent du frontend et sont signalés comme tels
(section 9) : je ne les ai pas devinés.

Un point de votre brief est également **factuellement inexact** dans le dépôt
fourni ; c'est traité honnêtement en section 5 plutôt que confirmé.

---

## 2. Cause exacte du HTTP 400

### Méthode

Avant de modifier une seule ligne, j'ai écrit un test jetable qui rejoue
**23 formes de requêtes réalistes** contre `POST /api/v1/ai/ask/` et affiche le
code HTTP obtenu. Cela évite de corriger au hasard.

Résultat : **`{"message": "Bonjour Karamo", "history": []}` fonctionnait déjà
(HTTP 200).** Mais **19 des 23 variantes renvoyaient 400.** Le sérialiseur
d'origine (`ai_features/serializers.py`) n'acceptait qu'un seul contrat, très
strict.

### Les causes, par ordre de probabilité

| # | Cause | Message d'erreur d'origine | Verdict |
|---|---|---|---|
| 1 | **`history` de plus de 10 messages** | `L'historique est limité à 10 messages.` | **Cause la plus probable** : une conversation normale casse après ~6 échanges. Le champ était un `ListField(max_length=10)` : au-delà, rejet total de la requête. |
| 2 | **Nom du champ texte différent** : `prompt`, `question`, `content`, `text`, `query`, ou format OpenAI `messages[]` | `{"message": ["Ce champ est obligatoire."]}` | Très probable si le frontend a été écrit contre une autre API. |
| 3 | **`role` hors de `["user","assistant"]`** : `system`, `bot`, `ai`, `model` | `"role": ["« bot » n'est pas un choix valide."]` | Probable : `bot` et `ai` sont des conventions frontend fréquentes. |
| 4 | **Contenu de l'historique sous une autre clé** : `text`, `message`, `parts` au lieu de `content` | `{"content": ["Ce champ est obligatoire."]}` | Probable. |
| 5 | **`history` avec `content: null` ou `""`** (message en cours de génération) | `{"content": ["Ce champ ne peut être nul."]}` | Probable en streaming : le frontend renvoie souvent le tour vide. |
| 6 | `history` en liste de chaînes, ou `history: null` | erreur de type | Possible. |
| 7 | `message` vide, ou uniquement des espaces | `Ce champ ne peut être vide.` | Comportement voulu, conservé. |
| 8 | `message` de plus de 4000 caractères | `max_length` | Comportement voulu, conservé. |

### Après correctif

**21 des 23 variantes renvoient désormais 200.** Les 2 refus restants sont
**volontaires** : message vide et message de plus de 4000 caractères.

---

## 3. Fichiers modifiés et pourquoi

### 3.1 `ai_features/serializers.py` — réécrit

Le sérialiseur normalise maintenant la requête **avant** de la valider, dans
`to_internal_value()`.

Constantes ajoutées :

```python
ALIAS_MESSAGE = ("message", "prompt", "question", "content", "text", "query", "input", "q")
ALIAS_CONTENU = ("content", "text", "message", "contenu", "value", "parts")
ALIAS_ROLE    = ("role", "author", "sender", "from", "type")

CORRESPONDANCE_ROLES = {
    "user": "user", "utilisateur": "user", "human": "user", "me": "user",
    "assistant": "assistant", "bot": "assistant", "ai": "assistant",
    "karamo": "assistant", "model": "assistant", "system": None,
}

HISTORIQUE_MAX = 10      # nombre de messages de contexte conservés
CONTENU_MAX    = 4000
MESSAGE_MAX    = 4000
```

Règles appliquées :

1. **Le texte de la question** est cherché dans `message`, puis les alias, puis
   en dernier recours dans le dernier tour `user` d'un tableau `messages[]` au
   format OpenAI. Le nom historique `message` reste prioritaire : **aucune
   rupture de compatibilité**.
2. **L'historique est tronqué, pas refusé.** Au-delà de 10 messages, on garde
   les **10 plus récents**. C'est le correctif de la cause n° 1.
3. Les rôles inconnus sont ramenés à `user` ou `assistant`. Les rôles
   `system`, `tool` et `developer` sont **supprimés**, pas convertis :
   c'est une protection contre l'injection de consigne par le client. Cette
   validation de sécurité n'a pas été affaiblie.
4. Les tours d'historique vides ou illisibles sont **ignorés** (ce n'est que du
   contexte), au lieu de faire échouer toute la requête.
5. Les messages d'erreur restants sont en français et explicites
   (`error_messages` sur le champ `message`).

`HistoryMessageSerializer` est conservé pour que le schéma OpenAPI
(`/api/docs/`) continue de documenter la forme canonique.

### 3.2 `ai_features/views.py`

- Nouvelle réponse 400 explicite, via `_reponse_400_karamo()` :

```json
{
  "success": false,
  "error": "Requête Karamo invalide.",
  "message": "Requête Karamo invalide.",
  "details": { "message": ["Ce champ est obligatoire."] },
  "champs_recus": ["prompt", "history"],
  "champs_attendus": ["message", "history"],
  "exemple": { "message": "Bonjour Karamo", "history": [] }
}
```

  `champs_recus` est décisif en production : il montre ce que le frontend a
  réellement envoyé, sans avoir à lire son code.

- **Correction du masquage des codes HTTP** — le même défaut que sur les
  paiements :

```python
except API_EXCEPTIONS:
    # 400 / 401 / 403 / 404 / 429 : laisser DRF produire le bon code.
    raise
except Exception:
    return internal_error_response(logger, "appel Karamo", status=503)
```

  Sans la première clause, un `except Exception` global transforme une
  `ValidationError` (400) en 500.

- Une panne du fournisseur renvoie **503**, pas 500 : c'est temporaire, pas une
  requête invalide. Une **référence d'incident** de 12 caractères est renvoyée
  au client et écrite dans le journal, sans jamais exposer la trace interne.

- **Régression corrigée en cours de route** : l'en-tête `Connection: keep-alive`
  que j'avais d'abord ajouté sur la réponse SSE est **interdit par WSGI**
  (en-tête hop-by-hop, PEP 3333). Gunicorn refuse la réponse et renvoie un
  **HTTP 500 `text/plain`** — c'est-à-dire exactement le symptôme à éviter. Il a
  été retiré et un test de non-régression le verrouille
  (`test_aucun_entete_hop_by_hop_sur_le_flux`). Ce bug n'a été visible qu'en
  testant par HTTP réel, pas par le client de test Django.

### 3.3 `ai_features/views.py` — streaming SSE

**L'endpoint reste un endpoint de streaming.** Il n'a pas été transformé en
endpoint JSON classique.

- Les évènements nominaux sont inchangés :
  `data: {"type":"token","text":"..."}` puis `data: {"type":"done"}`.
- **Les erreurs de validation et de quota sont désormais émises en SSE**, pas en
  JSON :

```
HTTP/1.1 400 Bad Request
Content-Type: text/event-stream

data: {"type": "error", "code": "requete_invalide", "message": "…", "details": {…}, "champs_recus": ["history"], "champs_attendus": ["message", "history"]}

event: end
data: {}
```

  Le code HTTP correct (400, 401, 429, 503) est **conservé** : un client qui lit
  `response.status` n'est pas trompé.
- Repli : si le client envoie `Accept: application/json` **sans** accepter
  `text/event-stream`, il reçoit du JSON. Détection dans
  `core/utils.client_attend_sse()`.
- Le générateur se termine par un `finally: yield "event: end\ndata: {}\n\n"` :
  le client sait toujours que le flux s'est refermé proprement, même après une
  exception.

### 3.4 `core/middleware.py` — nouveau `ErreursJsonMiddleware`

Placé **en premier** dans `MIDDLEWARE`. Il convertit en JSON toute réponse
d'erreur HTML sur `/api/`, `/healthz` et `/readyz`.

Il **ne touche pas** : les réponses en succès, les réponses déjà JSON, les
réponses `text/event-stream`, les réponses en streaming, et tout ce qui est hors
`/api/` — l'administration Django garde donc ses pages HTML.

Les en-têtes `Allow`, `WWW-Authenticate`, `Retry-After` et `Vary` sont préservés.

Le cas `DisallowedHost` est nommé explicitement, car c'est l'erreur la plus
difficile à diagnostiquer derrière un reverse proxy :

```
{"success": false,
 "message": "Hôte HTTP non autorisé par le serveur (ALLOWED_HOSTS). Vérifiez l'en-tête Host transmis par le reverse proxy.",
 "errors": {"host_recu": "pirate.example"}, "status": 400}
```

`RateLimitMiddleware` a également été corrigé sur deux points :

1. Les limites sont lues **par requête** depuis les réglages, et non figées à
   l'import : changer la variable d'environnement suffit désormais.
2. La clé de comptage était l'adresse IP pour un utilisateur non identifié.
   Derrière un NAT partagé — cas courant sur mobile en Guinée — un utilisateur
   consommait le quota des autres. La clé est maintenant, dans l'ordre :
   `u<id>` → empreinte SHA-256 du jeton → adresse IP.

### 3.5 `kharandi_backend/urls.py`

`handler400`, `handler403`, `handler404` et `handler500` sont branchés sur
`core.middleware.erreur_json`. Pour un chemin hors `/api/`, la fonction délègue
à `django.views.defaults` : l'administration n'est pas dégradée.

### 3.6 `kharandi_backend/settings.py` et `core/redis_utils.py`

Les quatre valeurs sont désormais pilotables par variable d'environnement, avec
les valeurs par défaut que vous attendiez :

```python
RATE_LIMIT_ENABLED       = env.bool("RATE_LIMIT_ENABLED", default=True)
RATE_LIMIT_PER_MIN       = env.int("RATE_LIMIT_PER_MIN", default=300)
RATE_LIMIT_AI_MIN        = env.int("RATE_LIMIT_AI_MIN", default=30)
KARAMO_FREE_DAILY_LIMIT  = env.int("KARAMO_FREE_DAILY_LIMIT", default=50)
```

`core/redis_utils.py` lit maintenant `settings.KARAMO_FREE_DAILY_LIMIT`
dynamiquement (`limite_gratuite_karamo()`) au lieu d'une constante figée.

### 3.7 `nginx/kharandi.conf` et `nginx/kharandi-ssl.conf.template`

Objectif : même en cas de panne de l'API, Nginx ne doit pas renvoyer sa page
HTML d'erreur à un client qui attend du JSON.

```nginx
location @erreur_api_json {
    default_type application/json;
    return 503 '{"success": false, "error": "Service temporairement indisponible.", "message": "Service temporairement indisponible.", "status": 503}';
}

location @erreur_sse {
    default_type text/event-stream;
    return 200 "data: {\"type\": \"error\", \"code\": \"passerelle_indisponible\", \"message\": \"Service temporairement indisponible.\"}\n\nevent: end\ndata: {}\n\n";
}
```

avec `error_page 500 502 503 504 = @erreur_api_json;` et `error_page 413 = …`
sur `location /`, et `error_page 500 502 503 504 = @erreur_sse;` sur
l'emplacement SSE.

**`chunked_transfer_encoding off;` a été supprimé** de l'emplacement SSE : en
HTTP/1.1 sans `Content-Length`, il empêche la délimitation correcte des
évènements. Les directives `proxy_buffering off`, `proxy_cache off` et
`proxy_read_timeout 3600s` étaient déjà en place et sont conservées.

### 3.8 Diagnostic et tests ajoutés

- `ai_features/management/commands/karamo_doctor.py` (nouveau) — affiche les
  valeurs de quota et de limitation **réellement chargées** avec leur origine
  (variable d'environnement ou valeur par défaut du code), les routes Karamo, et
  l'empreinte SHA-256 de 6 fichiers sources. **C'est l'outil qui prouve si
  l'image Docker est périmée.**
- `ai_features/test_karamo_contrat.py` (nouveau, 36 tests) en 6 classes :
  `FormatsAcceptes`, `ValidationsConservees`, `StreamingSSE`, `ApiToujoursJson`,
  `QuotaEtDebit`, `Normalisation`.
- `tests/test_api.py` — la classe `KaramoSafetyTests` est désormais annotée
  `@override_settings(KARAMO_FREE_DAILY_LIMIT=5)` : elle teste la **mécanique**
  de débit et de remboursement, plus une valeur commerciale de quota. Changer le
  quota en production ne cassera plus ces tests.

---

## 4. Aucune fonctionnalité supprimée

Vérifié : les 6 endpoints de `/api/v1/ai/` sont intacts.

| Route | Nom | Authentification |
|---|---|---|
| `POST /api/v1/ai/ask/` | `ai-ask` | `IsAuthenticated` |
| `POST /api/v1/ai/ask/stream/` | `ai-ask-stream` | `IsAuthenticated` |
| `POST /api/v1/ai/ask-image/` | `ai-ask-image` | `IsAuthenticated` |
| `POST /api/v1/ai/generate-qcm/` | `ai-generate-qcm` | `IsAuthenticated` |
| `POST /api/v1/ai/qcm/<uuid>/submit/` | `ai-qcm-submit` | `IsAuthenticated` |
| `GET /api/v1/ai/status/` | `ai-status` | `IsAuthenticated` |

Les préfixes `/api/v1/` sont corrects : ils n'étaient pas la cause du 400.

Aucune migration créée ni modifiée. `manage.py makemigrations --check` →
`No changes detected`. Les données BAC, `learning.Document` et les résultats
d'examens n'ont pas été touchés.

---

## 5. Point n° 4 de votre brief : votre prémisse était inexacte

Vous avez écrit que le code source contient `KARAMO_FREE_DAILY_LIMIT = 50` et
`RATE_LIMIT_PER_MIN = 300`, et que le conteneur affichant `5` et `60` prouvait
une image périmée.

**Le dépôt que vous m'avez fourni contenait en réalité :**

| Emplacement | Valeur dans votre archive |
|---|---|
| `core/redis_utils.py`, ligne 18 | `KARAMO_FREE_DAILY_LIMIT = 5` |
| `kharandi_backend/settings.py`, ~ligne 660 | `RATE_LIMIT_PER_MIN = 60` |
| `kharandi_backend/settings.py`, ~ligne 661 | `RATE_LIMIT_AI_MIN = 10` |

Ces trois valeurs étaient **codées en dur**, sans lecture d'environnement. Le
conteneur disait donc la vérité : `5` et `60` étaient bien les valeurs du code.
Les valeurs 50 et 300 n'existaient pas dans l'archive fournie.

Je l'indique clairement parce que corriger une image sur la base d'un diagnostic
erroné aurait fait perdre du temps sur le vrai problème (le sérialiseur).

**En revanche, une preuve réelle d'image périmée existe :** `requirements.txt`
ajoute `django-unfold>=0.50,<1.0`, indispensable au tableau de bord
d'administration présent dans cette version. Si l'image n'a pas été
reconstruite, `unfold` est absent et **Django ne démarre pas du tout**
(`ModuleNotFoundError` sur `INSTALLED_APPS`). Le conteneur en service ne
correspond donc certainement pas à cette arborescence.

**Mécanisme confirmé, et important :** le `Dockerfile` fait `COPY . .`, et le
service `api` de `docker-compose.yml` ne monte que `media_data` et
`static_data` — **jamais le code**. Toute modification Python exige donc un
`docker compose build`. À l'inverse, Nginx monte ses fichiers de configuration
depuis l'hôte (`./nginx/*.conf:ro`) : un changement Nginx ne nécessite qu'un
redémarrage, sans reconstruction.

Ces valeurs sont désormais dans `.env.production.example` et
`.env.yigui.example`, donc modifiables **sans reconstruire l'image**.

---

## 6. Aucune route `/api/` ne renvoie du HTML — vérifié par HTTP réel

Ces réponses ont été relevées sur un serveur Django réel, pas simulées.

| Cas | Résultat | Content-Type |
|---|---|---|
| `POST /api/v1/ai/ask/` sans jeton | 401 | `application/json` |
| En-tête `Host` non autorisé | 400, message nommant `ALLOWED_HOSTS` | `application/json` |
| Route inexistante `/api/v1/ai/inexistant/` | 404 | `application/json` |
| JSON malformé | 400, message en français | `application/json` |
| `GET` sur un endpoint `POST` | 405, en-tête `Allow` conservé | `application/json` |
| Panne du fournisseur, non-streaming | 503 + référence d'incident | `application/json` |
| Panne du fournisseur, **streaming** | 200 + `data: {"type":"error",…}` + `event: end` | `text/event-stream` |
| Requête invalide, **streaming** | 400 + évènement SSE d'erreur | `text/event-stream` |
| Historique de 30 messages | accepté (tronqué à 10) | — |
| Alias `prompt` + `role: "bot"` + clé `text` | accepté | — |
| `/healthz` et `/readyz` | 200 | `application/json` |

---

## 7. Commandes de déploiement

Rappel de vos contraintes, respectées : **jamais** `docker compose down -v`,
aucune suppression de volume, aucune réinitialisation de migration.

```bash
cd /opt/kharandi

# 1. Sauvegarde de la base AVANT toute opération.
docker compose exec -T db pg_dump -U kharandi_user kharandi_db \
  | gzip > /opt/kharandi-backups/avant-correctif-karamo-$(date +%F-%H%M).sql.gz

# 2. Mise en place du nouveau code (git pull, ou copie de l'archive).

# 3. Reconstruction de l'image : OBLIGATOIRE, le code est copié dans l'image.
docker compose build api worker beat

# 4. Redémarrage sans toucher aux volumes.
docker compose up -d api worker beat

# 5. Rechargement de la configuration Nginx (montée depuis l'hôte,
#    aucune reconstruction nécessaire).
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# 6. Vérification.
docker compose ps
docker compose logs --tail=80 api
```

### Vérifier les deux valeurs de configuration

```bash
docker compose exec api python manage.py karamo_doctor
```

Sortie attendue :

```
== Quota et limitation de débit ==
  KARAMO_FREE_DAILY_LIMIT        50   [variable d'environnement]
  RATE_LIMIT_PER_MIN             300   [variable d'environnement]
  RATE_LIMIT_AI_MIN              30   [variable d'environnement]
  RATE_LIMIT_ENABLED             True   [variable d'environnement]
```

Si la mention est `[valeur par défaut du code]`, les variables ne sont pas dans
`/opt/kharandi/.env`. Ajoutez-les puis `docker compose up -d api` — sans
reconstruction.

Contrôle direct, sans passer par la commande de diagnostic :

```bash
docker compose exec api python -c "
from django.conf import settings; import django; django.setup()
print('KARAMO_FREE_DAILY_LIMIT =', settings.KARAMO_FREE_DAILY_LIMIT)
print('RATE_LIMIT_PER_MIN      =', settings.RATE_LIMIT_PER_MIN)"
```

### Confirmer que l'image n'est plus périmée

```bash
# Empreintes vues par le conteneur :
docker compose exec api python manage.py karamo_doctor | sed -n '/Empreinte/,$p'

# Empreintes de votre dépôt local (doivent être identiques) :
for f in ai_features/serializers.py ai_features/views.py core/middleware.py \
         core/redis_utils.py core/utils.py kharandi_backend/settings.py; do
  printf "%-32s %s\n" "$f" "$(sha256sum "$f" | cut -c1-16)"
done
```

---

## 8. Tests `curl`

```bash
# Jeton d'accès.
JETON=$(curl -s -X POST https://api.kharandi.gn/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"6XXXXXXXX","password":"VOTRE_MOT_DE_PASSE"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access'])")
```

### Endpoint non-streaming

```bash
curl -i -X POST https://api.kharandi.gn/api/v1/ai/ask/ \
  -H "Authorization: Bearer $JETON" \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour Karamo", "history": []}'
```

Attendu : `200`, `Content-Type: application/json`, corps contenant la réponse et
le quota restant.

### Endpoint streaming

```bash
curl -N -X POST https://api.kharandi.gn/api/v1/ai/ask/stream/ \
  -H "Authorization: Bearer $JETON" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Bonjour Karamo", "history": []}'
```

Attendu : `Content-Type: text/event-stream`, puis

```
data: {"type": "token", "text": "Bon"}

data: {"type": "token", "text": "jour"}

data: {"type": "done", ...}

event: end
data: {}
```

L'option `-N` est indispensable : sans elle, `curl` tamponne et le flux paraît
figé.

### Contrôles supplémentaires utiles

```bash
# 1. Une erreur de validation reste du SSE, jamais du HTML.
curl -N -X POST https://api.kharandi.gn/api/v1/ai/ask/stream/ \
  -H "Authorization: Bearer $JETON" -H "Content-Type: application/json" \
  -d '{"history": []}'
# → 400 + Content-Type: text/event-stream + data: {"type":"error",...}

# 2. Un autre nom de champ est accepté (plus de 400).
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" \
  -X POST https://api.kharandi.gn/api/v1/ai/ask/ \
  -H "Authorization: Bearer $JETON" -H "Content-Type: application/json" \
  -d '{"prompt": "Bonjour", "history": [{"role": "bot", "text": "salut"}]}'

# 3. Un historique long est accepté (tronqué à 10, plus de 400).
python3 -c "import json;print(json.dumps({'message':'Et ensuite ?','history':[{'role':'user' if i%2==0 else 'assistant','content':f'msg {i}'} for i in range(30)]}))" \
  | curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://api.kharandi.gn/api/v1/ai/ask/ \
    -H "Authorization: Bearer $JETON" -H "Content-Type: application/json" \
    --data-binary @-

# 4. Aucune route /api/ ne renvoie du HTML.
for u in /api/v1/ai/ask/ /api/v1/ai/inexistant/ /api/v1/ai/status/; do
  printf "%-28s %s\n" "$u" \
    "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' https://api.kharandi.gn$u)"
done

# 5. Diagnostic complet côté serveur.
docker compose exec api python manage.py karamo_doctor
```

---

## 9. Ce qui dépend du frontend et que je ne peux pas trancher

Conformément à votre consigne, je ne fais aucune supposition sur le frontend.

### 9.1 `Error fetching search results: Expected JSON, got HTML or other (200)`

**Un HTTP 200 accompagné de HTML ne peut pas venir de ce backend Django sur un
chemin `/api/`.** Toutes les routes `/api/` renvoient du JSON, et c'est
désormais verrouillé par `ErreursJsonMiddleware` et par des tests (section 6).

L'hypothèse la plus cohérente est que la requête **n'atteint pas
`api.kharandi.gn`** : une URL de base mal configurée côté frontend (variable
`VITE_API_URL` / `NEXT_PUBLIC_API_URL` vide ou relative) fait porter l'appel sur
l'origine Vercel, qui répond `200` avec l'`index.html` de la SPA. C'est
exactement cette signature.

**Cela reste une hypothèse.** Pour la confirmer, ouvrez l'onglet Réseau du
navigateur et relevez le **domaine réel** de la requête en échec. Si ce n'est pas
`api.kharandi.gn`, le correctif est côté frontend — et vous m'avez demandé de ne
pas y toucher pour l'instant.

### 9.2 Quel nom de champ le frontend envoie-t-il réellement ?

Le backend accepte désormais 8 alias, ce qui rend la question moins critique.
Mais pour l'identifier avec certitude, la réponse 400 contient maintenant
`champs_recus` : un seul appel en échec suffit à le lire dans les journaux.

```bash
docker compose logs api | grep "Karamo — requête refusée"
```

Ligne journalisée :

```
Karamo — requête refusée (400). Champs reçus=['prompt'] erreurs={'message': [...]}
```

---

## 10. Correctif paiements réappliqué

Le correctif du HTTP 500 sur l'initiation d'abonnement, produit sur la version
précédente du dépôt, n'était pas présent dans l'archive que vous venez de
fournir. Il a été réappliqué sur cette nouvelle base :
`payments/views.py`, `reports/views.py`, `payments/tests.py`,
`payments/management/commands/seed_plans.py`.

Le tableau de bord d'administration `django-unfold` de votre nouvelle version a
été **intégralement conservé** (`kharandi_backend/admin_site.py`,
`admin_dashboard.py`, `admin_context.py`, `templates/admin/`).

Détails : voir `CORRECTIF_500_ABONNEMENT.md`.

---

## 11. État des vérifications

| Contrôle | Résultat |
|---|---|
| `manage.py check` | aucun problème |
| `manage.py test` (suite complète) | **128 tests, OK** |
| `manage.py makemigrations --check` | `No changes detected` |
| `manage.py collectstatic --noinput` | 195 fichiers |
| `manage.py karamo_doctor` | 50 / 300 / 30, routes correctes |
| Matrice de 23 formes de requêtes | 21 acceptées, 2 refus volontaires |
| Vérifications par HTTP réel | 11 cas, aucun HTML sur `/api/` |

Environnement de validation : Python 3.12, Django 5.0.6, DRF 3.15.2,
`django-unfold` installé.

---

## 12. Fichiers modifiés — récapitulatif

**Karamo (objet de ce correctif)**

- `ai_features/serializers.py` — réécrit
- `ai_features/views.py` — validation, erreurs, SSE
- `ai_features/management/commands/karamo_doctor.py` — nouveau
- `ai_features/test_karamo_contrat.py` — nouveau, 36 tests
- `core/middleware.py` — `ErreursJsonMiddleware`, `erreur_json`, clé de quota
- `core/utils.py` — `API_EXCEPTIONS`, `internal_error_response`, `sse_error_response`
- `core/redis_utils.py` — quota lu dynamiquement
- `kharandi_backend/settings.py` — 4 réglages par environnement, middleware
- `kharandi_backend/urls.py` — `handler400/403/404/500`
- `nginx/kharandi.conf`, `nginx/kharandi-ssl.conf.template` — erreurs JSON et SSE
- `tests/test_api.py` — quota épinglé, 2 tests mis à jour
- `.env.production.example`, `.env.yigui.example` — 4 variables documentées

**Correctif paiements réappliqué**

- `payments/views.py`, `reports/views.py`, `payments/tests.py`,
  `payments/management/commands/seed_plans.py`, `.dockerignore`

**Non touchés** : migrations, données BAC, `learning.Document`, résultats
d'examens, jeux de données, configuration Vercel, volumes Docker.
