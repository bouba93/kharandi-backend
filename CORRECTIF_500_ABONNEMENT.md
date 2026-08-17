# Correctif — 500 sur `POST /api/v1/payments/initiate/`

## Ce qui se passe

L'erreur est reproduite en local, à l'identique. `POST /api/v1/payments/initiate/`
renvoie un **500** dès que le corps de la requête ne contient pas un `order_id`
au format UUID :

```
>>> corps vide          : 500  Erreur interne : {'order_id': ['Ce champ est obligatoire.']}
>>> {"plan_id":"mensuel"}: 500  Erreur interne : {'order_id': ['Ce champ est obligatoire.']}
>>> {"order_id":"abc"}   : 500  Erreur interne : {'order_id': ['Must be a valid UUID.']}
```

Deux problèmes distincts se cumulent.

### Problème 1 — le mauvais endpoint est appelé

`/api/v1/payments/initiate/` **règle une commande de la boutique**. Il exige un
`order_id` qui pointe vers un `ecommerce.Order` existant, appartenant à
l'utilisateur, au statut `PENDING`.

L'endpoint des abonnements est un autre :

| Besoin | Endpoint | Corps |
|---|---|---|
| Abonnement | `POST /api/v1/payments/subscriptions/initiate/` | `{"plan_id": "mensuel"}` |
| Commande boutique | `POST /api/v1/payments/initiate/` | `{"order_id": "<uuid>"}` |

`plan_id` accepte un UUID de plan ou un alias : `gratuit`, `mensuel`, `annuel`,
`seller` / `boutique`.

### Problème 2 — le backend transformait un 400 en 500

```python
try:
    s = PaymentInitiateSerializer(data=request.data)
    s.is_valid(raise_exception=True)      # lève ValidationError → doit donner 400
    ...
except Exception as exc:                   # ← capture aussi la ValidationError
    return error_response(f"Erreur interne : {str(exc)}", status=500)
```

`s.is_valid(raise_exception=True)` lève une `rest_framework.exceptions.ValidationError`.
Le projet a bien un `custom_exception_handler` qui la traduirait en `400` propre,
mais le bloc `except Exception` de la vue l'intercepte **avant** que DRF ne la
voie. Résultat : un `500` là où un `400` explicite était attendu.

C'est ce second point qui a rendu le premier indiagnosticable côté frontend : au
lieu de « order_id est obligatoire », le navigateur reçoit
« Internal Server Error » sans indication.

Au passage, `str(exc)` était renvoyé au client. Sur une vraie panne (base
indisponible, erreur de configuration), le message d'exception peut contenir un
extrait de requête SQL, un chemin de fichier ou une valeur de configuration.

### Problème 3 — aucun plan d'abonnement n'existe en base

Constat annexe mais bloquant : **la table `payments_plan` est vide sur une base
neuve**. Aucune migration, aucun script du dépôt ne l'alimente. Or
`SubscriptionInitiateView` résout le plan puis renvoie `404 Plan introuvable`
s'il n'existe pas.

Donc même en appelant le bon endpoint, l'abonnement échouait — en `404` cette
fois. Il faut amorcer les plans.

## Ce que j'ai modifié

### `core/utils.py`

Ajout de deux éléments réutilisables :

- `API_EXCEPTIONS` — le tuple des exceptions que DRF sait traduire lui-même en
  code HTTP correct (`APIException`, `Http404`, `PermissionDenied`,
  `ValidationError` Django). À relancer dans tout `except Exception` de vue.
- `internal_error_response(logger, contexte, ...)` — journalise la trace
  complète avec une **référence d'incident** de 12 caractères et ne renvoie que
  cette référence au client. Le message d'exception n'est plus exposé.

### `payments/views.py`

Les deux vues d'initiation suivent maintenant ce schéma :

```python
except API_EXCEPTIONS:
    # 400/403/404/429… : laisser DRF produire le bon code HTTP.
    raise
except Exception:
    return internal_error_response(logger, "initiation d'un abonnement", ...)
```

Ajout d'un aiguillage explicite dans `PaymentInitiateView` : un appel qui porte
`plan_id` (ou `plan`) sans `order_id` reçoit un `400` qui nomme l'endpoint à
utiliser, au lieu d'une erreur de validation incompréhensible sur `order_id`.

### `reports/views.py`

Même traitement pour les deux exports PDF, qui renvoyaient
`f"Erreur PDF : {e}"` en `500`. Ils renvoient désormais un `503` — la génération
dépend de WeasyPrint et de ses bibliothèques système, une indisponibilité est
temporaire — sans divulguer l'exception.

### `payments/management/commands/seed_plans.py` (nouveau)

Commande d'amorçage des quatre plans attendus par le frontend. Les noms
correspondent exactement à la table d'alias de `_get_plan()`, sinon les alias ne
résolvent rien.

| Plan | Période | Prix |
|---|---|---|
| Gratuit | GRATUIT | 0 GNF |
| Premium Mensuel | MENSUEL | 25 000 GNF |
| Premium Annuel | ANNUEL | 250 000 GNF |
| Boutique Vendeur | MENSUEL | 50 000 GNF |

**Ces montants sont des valeurs de départ que j'ai posées, pas une grille tarifaire
validée.** Corrigez-les dans le fichier avant de lancer la commande, ou depuis
l'admin Django ensuite.

Garanties de non-destruction :

- résolution par nom, sans doublon : rejouer la commande ne crée rien de plus ;
- un plan déjà présent n'est **pas** modifié, y compris son prix, sauf si
  `--maj-tarifs` est passé explicitement ;
- aucune suppression, aucune désactivation, aucun plan hors liste touché ;
- `--simulation` affiche le résultat et annule la transaction.

### `payments/tests.py`

19 tests ajoutés (91 au total, tous verts) :

- chaque code HTTP de l'initiation : `400` corps vide, `400` UUID invalide,
  `400` avec `plan_id`, `404` commande inexistante, `401` sans jeton, `400`
  abonnement sans `plan_id`, `404` plan inconnu, `502` LengoPay injoignable ;
- une vraie panne renvoie bien `500`, **sans** que le message d'exception
  n'apparaisse dans la réponse, avec une référence d'incident de 12 caractères ;
- amorçage : création, idempotence sur trois passages, non-modification d'un
  tarif existant, effet de `--maj-tarifs`, mode simulation, préservation d'un
  plan maison hors liste ;
- parcours complet : les 4 plans visibles, plan gratuit activé sans paiement,
  plan payant produisant un `pay_id` et une transaction à 25 000 GNF.

## À faire sur le VPS

### 1. Vérifier la cause dans les journaux, avant tout

```bash
cd /opt/kharandi
docker compose logs --since 2h api | grep -A 25 "ERREUR paiement"
```

Vous devriez y voir la trace se terminant par
`ValidationError: {'order_id': [...]}`. **Si la trace montre autre chose,
envoyez-la moi** : le diagnostic ci-dessus serait alors incomplet et la
correction resterait valable sans être suffisante.

### 2. Déployer

```bash
cd /opt/kharandi
bash deploy/update.sh
```

Rappel : aucune nouvelle migration n'est introduite (`makemigrations --check` →
`No changes detected`). Les volumes ne sont pas touchés.

### 3. Amorcer les plans

```bash
docker compose exec api python manage.py seed_plans --simulation   # contrôle
docker compose exec api python manage.py seed_plans                # application
docker compose exec api python manage.py seed_plans                # doit être sans effet
```

Puis vérifier :

```bash
curl -s https://api.kharandi.gn/api/v1/payments/plans/ \
     -H "Authorization: Bearer <ACCESS_TOKEN>" | python3 -m json.tool
```

### 4. Corriger l'appel côté frontend

Le frontend est sur Vercel, hors de ce dépôt — je n'y ai pas touché. Cherchez
dans le code du frontend :

```
payments/initiate
```

Sur l'écran d'abonnement, remplacez par :

```js
await api.post("/api/v1/payments/subscriptions/initiate/", { plan_id: planId });
// réponse : { data: { reference, pay_id, payment_url } }
// → rediriger l'utilisateur vers payment_url
```

Laissez `payments/initiate/` en place partout où il s'agit de régler une
commande de la boutique, avec `order_id`.

### 5. Contrôler que le 500 a disparu

```bash
# Sans order_id → doit répondre 400, plus 500
curl -s -o /dev/null -w "%{http_code}\n" \
     -X POST https://api.kharandi.gn/api/v1/payments/initiate/ \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     -H "Content-Type: application/json" -d '{}'

# Abonnement mensuel → doit répondre 201 avec payment_url
curl -s -X POST https://api.kharandi.gn/api/v1/payments/subscriptions/initiate/ \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     -H "Content-Type: application/json" -d '{"plan_id":"mensuel"}'
```

## Si un 500 revient

La réponse contient désormais une référence d'incident :

```json
{"success": false, "message": "Impossible de démarrer l'abonnement…",
 "errors": {"incident": "4d27bd5e370f"}, "incident": "4d27bd5e370f"}
```

Elle permet de retrouver la trace exacte, sans rien exposer au client :

```bash
docker compose logs api | grep 4d27bd5e370f -A 25
```

## Réserve

Le correctif garantit que l'API renvoie le bon code HTTP et un message
exploitable. Il ne garantit pas que le paiement aboutisse : cela dépend de
`LENGOPAY_LICENSE_KEY` et `LENGOPAY_SITE_ID` en production. Pour les vérifier :

```bash
docker compose exec api python manage.py lengopay_doctor
```

Un `502 Impossible de générer le lien de paiement` après ce correctif désigne la
configuration LengoPay, pas le code.
