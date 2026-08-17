# Kharandi École — Liste des endpoints (portail scolaire)

**23 endpoints**, tous sous `/api/v1/ecole/`. L'application grand public est documentée à part (`ENDPOINTS_KHARANDI.md`, 84 endpoints).

Base de production : `https://api.kharandi.gn`


## Authentification : différente de celle de Kharandi

C'est le point le plus important à retenir. Le portail scolaire **n'utilise pas
le JWT de l'application Kharandi**. Il a son propre mécanisme :

| | Kharandi | Kharandi École |
|---|---|---|
| Comptes | `users.User` (téléphone + OTP) | `ecole.School` et `ecole.SchoolTeacher` (email + mot de passe) |
| Jeton | JWT `Authorization: Bearer <token>` | Jeton signé Django `X-School-Token: <token>` |
| Variante acceptée | — | `Authorization: School <token>` |
| Durée de vie | selon la configuration JWT | 12 h (`SCHOOL_TOKEN_MAX_AGE`) |
| Rafraîchissement | `/api/v1/auth/token/refresh/` | **aucun** — il faut se reconnecter |
| Révocation | — | changement de mot de passe (le jeton embarque une empreinte du hachage) |

Le jeton est produit par `issue_portal_token()` et contient le type d'acteur
(`school` ou `teacher`), son identifiant, l'identifiant de l'établissement et une
empreinte SHA-256 du hachage du mot de passe. Cette dernière est vérifiée à
chaque requête : **changer le mot de passe invalide immédiatement tous les jetons
en circulation**, ce qui est un bon choix de conception.

Deux niveaux d'accès en découlent :

- **Jeton portail (direction ou enseignant)** — `IsPortalOrKharandiAdmin`
- **Jeton portail (direction seule)** — `IsSchoolAdminOrKharandiAdmin`

Dans les deux cas, un administrateur Kharandi (`users.User` avec `role="ADMIN"`,
authentifié en JWT) est également accepté.

## Parcours d'entrée

1. `POST /api/v1/ecole/activate/` sans mot de passe → vérifie le couple
   code d'activation + email, renvoie le nom de l'établissement.
2. `POST /api/v1/ecole/activate/` avec un mot de passe (6 caractères minimum) →
   active l'établissement.
3. `POST /api/v1/ecole/login/` → jeton portail « direction ».
4. `POST /api/v1/ecole/teacher/login/` → jeton portail « enseignant ».

La connexion direction refuse l'accès si `School.is_activated` est faux (`403`)
ou si `School.subscription_active` est faux (`403`).


## Activation et connexion

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/ecole/activate/` | Public |
| `POST` | `/api/v1/ecole/login/` | Public |
| `POST` | `/api/v1/ecole/teacher/login/` | Public |

## Établissements

2 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/ecole/schools/` | Jeton portail (direction ou enseignant) |
| `DELETE,GET,PATCH` | `/api/v1/ecole/schools/<str:school_id>/` | Jeton portail (direction ou enseignant) |

## Élèves

2 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/ecole/schools/<str:school_id>/students/` | Jeton portail (direction ou enseignant) |
| `DELETE,PATCH` | `/api/v1/ecole/students/<str:student_id>/` | Jeton portail (direction seule) |

## Enseignants et classes

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/ecole/classes/` | Jeton portail (direction ou enseignant) |
| `DELETE,GET,POST` | `/api/v1/ecole/teachers/` | Jeton portail (direction seule) |
| `DELETE,GET,POST` | `/api/v1/ecole/teachers/<str:teacher_id>/` | Jeton portail (direction seule) |

## Vie scolaire — notes, absences, frais

4 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET,POST` | `/api/v1/ecole/absences/` | Jeton portail (direction ou enseignant) |
| `GET,POST` | `/api/v1/ecole/grades/` | Jeton portail (direction ou enseignant) |
| `GET,PATCH,POST` | `/api/v1/ecole/payments/` | Jeton portail (direction seule) |
| `GET,PATCH,POST` | `/api/v1/ecole/payments/<str:payment_id>/` | Jeton portail (direction seule) |

## Abonnement de l'établissement

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `POST` | `/api/v1/ecole/subscriptions/checkout-session/` | Jeton portail (direction seule) |
| `GET` | `/api/v1/ecole/subscriptions/pricing/` | Public |
| `GET` | `/api/v1/ecole/subscriptions/status/<str:school_id>/` | Jeton portail (direction seule) |

## Badges et certificats

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `DELETE` | `/api/v1/ecole/schools/badges/<str:badge_id>/` | Jeton portail (direction seule) |
| `GET` | `/api/v1/ecole/schools/badges/history/<str:school_id>/` | Jeton portail (direction seule) |
| `POST` | `/api/v1/ecole/schools/badges/issue/` | Jeton portail (direction seule) |

## Espace parent (authentification Kharandi)

3 endpoints.

| Méthodes | Chemin | Accès |
|---|---|---|
| `GET` | `/api/v1/ecole/parent/<str:matricule>/` | JWT Kharandi |
| `GET` | `/api/v1/ecole/parents/students/<str:student_id>/badges/` | JWT Kharandi |
| `GET` | `/api/v1/ecole/parents/students/<str:student_id>/badges/<str:badge_id>/pdf/` | JWT Kharandi |

## Le pont entre les deux produits

Les trois routes de l'espace parent sont les seules du portail à utiliser le
**JWT Kharandi** (`IsAuthenticated`) et non le jeton portail. C'est cohérent : un
parent est un utilisateur de l'application Kharandi qui consulte les données
scolaires de son enfant. Ce sont les seuls points de contact entre les deux
produits.

`GET /api/v1/ecole/parent/<matricule>/` prend le matricule de l'élève, pas un
identifiant de parent.

## Trois écarts relevés dans le code

Ces constats sortent du périmètre du lot de correctifs livré (Docker, Nginx,
LengoPay, Celery Beat). Je les signale parce qu'ils touchent au fonctionnement
même du portail, mais je ne les ai pas corrigés.

### 1. Le paiement d'abonnement école est une simulation

`POST /api/v1/ecole/subscriptions/checkout-session/` crée bien un
`SchoolSubscription` au statut `PENDING`, puis renvoie une URL fabriquée de
toutes pièces :

```python
# Simuler une URL de paiement (à remplacer par LengoPay ou Orange Money API)
payment_url = f"https://pay.kharandi.gn/checkout/{sub.id}"
```

Ce domaine n'apparaît nulle part ailleurs dans le dépôt. **Aucun paiement réel
n'est déclenché**, et tout le travail de fiabilisation LengoPay livré
précédemment (confirmation serveur, réconciliation automatique, idempotence,
contrôle du montant) ne s'applique **pas** au portail école : il ne couvre que
`/api/v1/payments/`.

### 2. Aucun abonnement école ne peut passer à l'état actif

`SchoolSubscription` n'est jamais créé qu'avec `status=PENDING`, et **aucune
ligne du dépôt ne le fait passer à `ACTIVE`** — conséquence directe du point 1,
puisqu'il n'y a pas de confirmation de paiement. Le seul moyen aujourd'hui est de
modifier l'enregistrement à la main dans l'admin Django.

Deux fonctionnalités en dépendent et se comportent donc de façon dégradée :

- `GET /api/v1/ecole/subscriptions/status/<school_id>/` renvoie toujours
  `subscription_status: "none"` avec un quota de licences à `0`.
- Le contrôle de l'option badges ne bloque jamais rien (point 3).

### 3. Le contrôle de l'option badges échoue en mode ouvert

Dans `BadgeIssueView` :

```python
active_sub = Sub.objects.filter(school=school, status=Sub.Status.ACTIVE)...first()
if active_sub and not active_sub.unlocked_badges_option:
    return error_response("L'option Badges/Certificats n'est pas activée…", 403)
```

Comme aucun abonnement n'est jamais `ACTIVE`, `active_sub` vaut toujours `None`,
la condition est toujours fausse et **l'émission de badges n'est jamais
refusée**. Toute école activée peut émettre des badges sans avoir souscrit
l'option.

La logique est écrite en « fail-open » : l'absence d'abonnement autorise au lieu
de refuser. Si l'intention est que l'option soit payante, la condition doit être
inversée — refuser quand `active_sub` est absent.

À noter dans le même esprit : `School.subscription_active` vaut `True` par défaut
dans le modèle, et la création d'école le fixe explicitement à `True`. Le contrôle
d'abonnement à la connexion est donc ouvert par défaut.

## Régénérer cette liste

```bash
docker compose exec api python manage.py spectacular --file /tmp/schema.yaml
docker compose exec api grep -E '^  /api/v1/ecole/' /tmp/schema.yaml
```

