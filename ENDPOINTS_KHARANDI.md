# Kharandi — Liste des endpoints (application grand public)

**84 endpoints.** Le portail scolaire est documenté à part (`ENDPOINTS_ECOLE.md`, 23 endpoints) : il n'utilise ni la même authentification, ni les mêmes tables.

Liste extraite du résolveur d'URL de Django chargé, pas d'une lecture des fichiers `urls.py`. Recoupée avec `manage.py spectacular` : même total.

Base de production : `https://api.kharandi.gn`

**Authentification : JWT.** En-tête `Authorization: Bearer <access_token>`, obtenu via `/api/v1/auth/login/` puis `/api/v1/auth/login/verify/`, renouvelé via `/api/v1/auth/token/refresh/`.

Les méthodes `OPTIONS`, `HEAD` et `TRACE` sont omises.


## Routes techniques et documentation

Communes aux deux produits.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/` | voir note |
| `GET` | `/api/docs/` | Public |
| `GET` | `/api/schema/` | Public |
| `GET` | `/healthz` | voir note |
| `GET` | `/readyz` | voir note |

`/healthz` ne touche ni la base ni Redis : c'est la sonde du conteneur `api`. `/readyz` teste réellement PostgreSQL et Redis et renvoie `503` si une dépendance critique est indisponible.


## Authentification et comptes — `/api/v1/auth/`

22 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/auth/avatar/` | JWT Kharandi |
| `DELETE,GET` | `/api/v1/auth/devices/` | JWT Kharandi |
| `POST` | `/api/v1/auth/devices/reset/` | Public |
| `POST` | `/api/v1/auth/login/` | Public |
| `POST` | `/api/v1/auth/login/password/` | Public |
| `POST` | `/api/v1/auth/login/verify/` | Public |
| `GET,PATCH` | `/api/v1/auth/me/` | JWT Kharandi |
| `POST` | `/api/v1/auth/me/points/` | JWT Kharandi |
| `POST` | `/api/v1/auth/otp/send/` | Public |
| `POST` | `/api/v1/auth/otp/verify/` | Public |
| `POST` | `/api/v1/auth/password/reset/confirm/` | Public |
| `POST` | `/api/v1/auth/password/reset/request/` | Public |
| `POST` | `/api/v1/auth/register/` | Public |
| `POST` | `/api/v1/auth/register/eleve/` | Public |
| `POST` | `/api/v1/auth/register/otp/send/` | Public |
| `POST` | `/api/v1/auth/register/parent/` | Public |
| `POST` | `/api/v1/auth/register/repetiteur/` | Public |
| `POST` | `/api/v1/auth/register/vendeur/` | Public |
| `POST` | `/api/v1/auth/token/refresh/` | voir note |
| `GET,POST` | `/api/v1/auth/users/` | JWT Kharandi |
| `DELETE,PATCH` | `/api/v1/auth/users/<uuid:user_id>/` | JWT Kharandi |
| `GET` | `/api/v1/auth/wallet/` | JWT Kharandi |

## Profil de l'utilisateur connecté — `/api/v1/users/`

4 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,PATCH` | `/api/v1/users/me/` | JWT Kharandi |
| `POST` | `/api/v1/users/me/avatar/` | JWT Kharandi |
| `GET,POST` | `/api/v1/users/me/points/` | JWT Kharandi |
| `GET` | `/api/v1/users/me/wallet/` | JWT Kharandi |

## Paiements et abonnements — `/api/v1/payments/`

12 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/api/v1/payments/callbacks/` | JWT Kharandi — admin |
| `POST` | `/api/v1/payments/initiate/` | JWT Kharandi |
| `GET,POST` | `/api/v1/payments/plans/` | JWT Kharandi |
| `DELETE,PATCH` | `/api/v1/payments/plans/<uuid:pk>/` | JWT Kharandi |
| `POST` | `/api/v1/payments/run-cron/` | voir note |
| `POST` | `/api/v1/payments/subscriptions/initiate/` | JWT Kharandi |
| `GET` | `/api/v1/payments/subscriptions/status/` | JWT Kharandi |
| `GET` | `/api/v1/payments/transactions/` | JWT Kharandi |
| `GET,POST` | `/api/v1/payments/webhook` | Jeton de callback |
| `GET,POST` | `/api/v1/payments/webhook/` | Jeton de callback |
| `GET,POST` | `/api/v1/payments/webhook/<str:token>` | Jeton de callback |
| `GET,POST` | `/api/v1/payments/webhook/<str:token>/` | Jeton de callback |

## Apprentissage — `/api/v1/learning/`

4 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/learning/documents/` | JWT Kharandi |
| `DELETE,GET,PATCH,PUT` | `/api/v1/learning/documents/<uuid:pk>/` | Lecture publique / écriture admin |
| `POST` | `/api/v1/learning/documents/upload/` | JWT Kharandi |
| `GET` | `/api/v1/learning/subjects/` | JWT Kharandi |

## Intelligence artificielle — `/api/v1/ai/`

6 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/ai/ask-image/` | JWT Kharandi |
| `POST` | `/api/v1/ai/ask/` | JWT Kharandi |
| `POST` | `/api/v1/ai/ask/stream/` | JWT Kharandi |
| `POST` | `/api/v1/ai/generate-qcm/` | JWT Kharandi |
| `POST` | `/api/v1/ai/qcm/<uuid:qcm_id>/submit/` | JWT Kharandi |
| `GET` | `/api/v1/ai/status/` | JWT Kharandi |

## Notes des répétiteurs — `/api/v1/grades/`

2 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/grades/` | JWT Kharandi |
| `GET` | `/api/v1/grades/students/` | JWT Kharandi |

## Contenus éditoriaux — `/api/v1/content/`

14 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/content/news/` | JWT Kharandi |
| `DELETE,PATCH` | `/api/v1/content/news/<uuid:pk>/` | JWT Kharandi |
| `GET` | `/api/v1/content/notifications/` | JWT Kharandi |
| `POST` | `/api/v1/content/notifications/<uuid:pk>/read/` | JWT Kharandi |
| `POST` | `/api/v1/content/notifications/read/` | JWT Kharandi |
| `GET,POST` | `/api/v1/content/reading-progress/<str:document_id>/` | JWT Kharandi |
| `GET,POST` | `/api/v1/content/scholarships/` | JWT Kharandi |
| `DELETE,GET,PATCH` | `/api/v1/content/scholarships/<uuid:pk>/` | JWT Kharandi |
| `GET,POST` | `/api/v1/content/school-rankings/` | JWT Kharandi |
| `DELETE,GET,PATCH` | `/api/v1/content/school-rankings/<uuid:pk>/` | JWT Kharandi |
| `GET,POST` | `/api/v1/content/study-abroad/` | JWT Kharandi |
| `DELETE,GET,PATCH` | `/api/v1/content/study-abroad/<uuid:pk>/` | JWT Kharandi |
| `GET,POST` | `/api/v1/content/tutor-ads/` | JWT Kharandi |
| `DELETE` | `/api/v1/content/tutor-ads/<uuid:pk>/` | JWT Kharandi |

## Place de marché — `/api/v1/marketplace/`

9 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/marketplace/orders/` | JWT Kharandi |
| `POST` | `/api/v1/marketplace/orders/redeem/` | JWT Kharandi |
| `GET,POST` | `/api/v1/marketplace/products/` | JWT Kharandi |
| `DELETE,PATCH` | `/api/v1/marketplace/products/<uuid:pk>/` | JWT Kharandi |
| `GET` | `/api/v1/marketplace/products/mine/` | JWT Kharandi |
| `GET,POST` | `/api/v1/marketplace/promos/` | JWT Kharandi |
| `POST` | `/api/v1/marketplace/promos/check/` | JWT Kharandi |
| `GET,PATCH` | `/api/v1/marketplace/seller/orders/` | JWT Kharandi |
| `GET,PATCH` | `/api/v1/marketplace/seller/orders/<uuid:pk>/` | JWT Kharandi |

## Boutique — `/api/v1/store/`

2 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/api/v1/store/orders/` | JWT Kharandi |
| `POST` | `/api/v1/store/orders/create/` | JWT Kharandi |

## Notifications — `/api/v1/notifications/`

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/notifications/custom/` | JWT Kharandi |
| `GET` | `/api/v1/notifications/stream/` | JWT Kharandi |
| `POST` | `/api/v1/notifications/welcome/` | JWT Kharandi |

## Support — `/api/v1/support/`

2 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/support/tickets/` | JWT Kharandi |
| `GET,PATCH` | `/api/v1/support/tickets/<uuid:pk>/` | JWT Kharandi |

## Rapports et exports — `/api/v1/reports/`

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/api/v1/reports/stats/excel/` | JWT Kharandi |
| `GET` | `/api/v1/reports/student/pdf/` | JWT Kharandi |
| `GET` | `/api/v1/reports/transactions/pdf/` | JWT Kharandi |

## Recherche — `/api/v1/search/`

1 endpoint.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/api/v1/search/` | JWT Kharandi |

## Notes sur les accès marqués « voir note »

- `/`, `/healthz`, `/readyz` — vues Django simples, publiques par nature. Elles
  ne renvoient aucune donnée métier. `/readyz` expose l'état de PostgreSQL et de
  Redis sous forme de booléens uniquement.
- `/api/v1/auth/token/refresh/` — vue standard de
  `djangorestframework-simplejwt`. Publique par construction : le jeton de
  rafraîchissement fourni dans le corps de la requête sert lui-même
  d'authentification.
- `/api/v1/payments/run-cron/` — `permission_classes = []` et
  `authentication_classes = []`, mais la vue exige l'en-tête `X-Cron-Secret`
  égal à `CRON_SECRET`, et refuse avec un `403` si `CRON_SECRET` est vide. Un
  secret non renseigné ferme donc l'endpoint au lieu de l'ouvrir.

## Points à connaître

**Quatre variantes du webhook LengoPay.** `/api/v1/payments/webhook`,
`/webhook/`, `/webhook/<token>` et `/webhook/<token>/` — avec et sans barre
oblique finale, avec et sans jeton. Cette redondance est volontaire : une
redirection `301` de Django vers la variante avec barre oblique transformerait le
`POST` de LengoPay en `GET`, faisant perdre le corps de la notification. **La
seule à déclarer chez LengoPay est
`https://api.kharandi.gn/api/v1/payments/webhook/<TOKEN>/`.** Le `GET` accepté
ne traite aucun paiement : il sert à vérifier depuis un navigateur que l'URL est
joignable.

**Profil utilisateur exposé sous deux préfixes.** `/api/v1/auth/me/` et
`/api/v1/users/me/` pointent vers la même vue `MeView` ; de même pour
`/api/v1/auth/avatar/` et `/api/v1/users/me/avatar/`, ainsi que pour
`/api/v1/auth/wallet/` et `/api/v1/users/me/wallet/`. Le module
`users/self_urls.py` indique que ce second préfixe a été ajouté pour coller aux
appels du frontend.

Attention : `/api/v1/auth/me/points/` et `/api/v1/users/me/points/` ne sont
**pas** équivalents — le premier utilise `PointsAddView` (`POST` seulement), le
second `MyPointsView` (`GET` et `POST`). Ce ne sont pas des alias.

**`/api/v1/auth/devices/reset/` est public, et c'est justifié.** L'endpoint sert
à un utilisateur bloqué sur un ancien appareil, donc incapable de
s'authentifier. La protection réelle est un code OTP envoyé par SMS au numéro
concerné : sans code valide et non expiré, aucun appareil n'est supprimé.

**`/api/v1/grades/` n'a aucun lien avec les notes scolaires.** Le modèle
`grades.Grade` relie deux comptes `users.User` (un répétiteur et son élève).
Les notes des établissements vivent dans `ecole.SchoolGrade`, exposées sous
`/api/v1/ecole/grades/`. Deux systèmes de notes parallèles, sans passerelle
entre eux.

**Surface d'écriture large sur les contenus.** `/api/v1/content/news/`,
`scholarships/`, `school-rankings/`, `study-abroad/` et `tutor-ads/` acceptent
`POST`, `PATCH` ou `DELETE` avec la seule permission `IsAuthenticated`. Si
l'intention est que seuls des administrateurs publient ces contenus, la
vérification du rôle doit se faire dans la vue. Je n'ai pas audité ce point : il
sort du périmètre du lot de correctifs livré.

## Réserve sur `/api/docs/`

La génération du schéma fonctionne, mais produit **93 avertissements « unable to
guess serializer »** : ces vues sont des `APIView` écrites à la main sans
`serializer_class`. Swagger listera les chemins et les méthodes, mais les corps
de requête et de réponse y seront souvent vides ou approximatifs. Les chemins et
méthodes de ce document sont fiables ; pour connaître les champs attendus par
une route, il faut lire la vue correspondante.

## Régénérer cette liste

```bash
docker compose exec api python manage.py spectacular --file /tmp/schema.yaml
docker compose exec api grep -E '^  /' /tmp/schema.yaml
```

Ou dans un navigateur : `https://api.kharandi.gn/api/docs/`.

