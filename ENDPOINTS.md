# API Kharandi — Liste complète des endpoints

**Généré le 10/08/2026** depuis le routeur Django · `python3 gen_endpoints_doc.py`

- **107 routes** exposées, soit **156 opérations HTTP**
- **URL de base** : `http://212.95.33.158/api/v1` (VPS YIGUI) — variable `VITE_API_URL` côté frontend
- **Documentation interactive** : `/api/docs/` · **Schéma OpenAPI** : `/api/schema/`
- Les endpoints marqués **NOUVEAU** ont été ajoutés pour combler les appels du frontend restés sans route.

## Conventions

**Authentification** — jeton JWT dans l'en-tête, plus l'identifiant d'appareil de confiance :

```http
Authorization: Bearer <access_token>
X-Device-Token: <device_token>
```

Le jeton d'accès expire ; le frontend le renouvelle automatiquement via `POST /auth/token/refresh/`.

**Format de réponse** — uniforme sur toute l'API :

```json
{ "success": true, "message": "Succès", "data": { } }
```

```json
{ "success": false, "message": "Code OTP incorrect.", "errors": { } }
```

**Codes de statut** — `200` succès · `201` créé · `400` requête invalide · `401` jeton absent ou expiré · `403` droits insuffisants · `404` introuvable · `500` erreur serveur.

**Colonne Accès** — `Public` : aucun jeton requis · `Connecté` : jeton JWT valide · `Admin Kharandi` : rôle administrateur · `Lecture connecté · écriture admin` : consultation ouverte aux comptes connectés, création et suppression réservées aux administrateurs.

**Pagination** — les listes acceptent `?page=` et `?page_size=` et renvoient `{ count, next, previous, results }` dans `data`.

## Sommaire

| Module | Préfixe | Routes |
|---|---|---|
| [Racine et documentation](#racine-et-documentation) | — | 4 |
| [Authentification et comptes](#authentification-et-comptes) | `/api/v1/auth/` | 22 |
| [Portefeuille de points (libre-service)](#portefeuille-de-points-libre-service) | `/api/v1/users/` | 4 |
| [Intelligence artificielle — Karamo](#intelligence-artificielle-karamo) | `/api/v1/ai/` | 6 |
| [Bibliothèque pédagogique](#bibliothèque-pédagogique) | `/api/v1/learning/` | 4 |
| [Contenu éditorial](#contenu-éditorial) | `/api/v1/content/` | 14 |
| [Espace École](#espace-école) | `/api/v1/ecole/` | 23 |
| [Notes](#notes) | `/api/v1/grades/` | 2 |
| [Marketplace](#marketplace) | `/api/v1/marketplace/` | 9 |
| [Boutique (commandes)](#boutique-commandes) | `/api/v1/store/` | 2 |
| [Paiements et abonnements](#paiements-et-abonnements) | `/api/v1/payments/` | 8 |
| [Notifications](#notifications) | `/api/v1/notifications/` | 3 |
| [Support client](#support-client) | `/api/v1/support/` | 2 |
| [Rapports et exports](#rapports-et-exports) | `/api/v1/reports/` | 3 |
| [Recherche globale](#recherche-globale) | `/api/v1/search/` | 1 |
| **Total** | | **107** |

## Racine et documentation

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` | `/` | Public | Statut de l'API et numéro de version. |
| `GET` | `/api/docs/` | Public | Documentation interactive Swagger UI. |
| `GET` | `/api/schema/` | Public | Schéma OpenAPI 3 brut (YAML). |
| `GET` | `/healthz` **NOUVEAU** | Public | Sonde de santé : vérifie l'API et la connexion PostgreSQL. |

## Authentification et comptes

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `POST` | `/auth/avatar/` | Connecté | Envoi de la photo de profil (multipart). |
| `GET` `DELETE` | `/auth/devices/` | Connecté | Appareils de confiance : liste et révocation. |
| `POST` | `/auth/devices/reset/` | Public | Réinitialise l'appareil de confiance (perte de téléphone). |
| `POST` | `/auth/login/` | Public | Connexion : renvoie un JWT si appareil connu, sinon déclenche un OTP. |
| `POST` | `/auth/login/password/` | Public | Connexion directe par numéro et mot de passe. |
| `POST` | `/auth/login/verify/` | Public | Valide le code OTP de connexion et renvoie les jetons. |
| `GET` `PATCH` | `/auth/me/` | Connecté | Profil de l'utilisateur connecté (GET) et mise à jour (PATCH). |
| `POST` | `/auth/me/points/` | Lecture connecté · écriture admin | Ajustement de points réservé aux administrateurs. |
| `POST` | `/auth/otp/send/` | Public | Envoi d'un OTP (voie historique). |
| `POST` | `/auth/otp/verify/` | Public | Vérification d'un OTP (voie historique). |
| `POST` | `/auth/password/reset/confirm/` | Public | Confirme la réinitialisation avec le code OTP. |
| `POST` | `/auth/password/reset/request/` | Public | Demande de réinitialisation du mot de passe (envoi OTP). |
| `POST` | `/auth/register/` **NOUVEAU** | Public | Inscription universelle (OTP + mot de passe + rôle). |
| `POST` | `/auth/register/eleve/` | Public | Inscription d'un élève (niveau, série). |
| `POST` | `/auth/register/otp/send/` | Public | Envoie le code OTP d'inscription par SMS. |
| `POST` | `/auth/register/parent/` | Public | Inscription d'un parent, avec liaison à un enfant. |
| `POST` | `/auth/register/repetiteur/` | Public | Inscription d'un répétiteur. |
| `POST` | `/auth/register/vendeur/` | Public | Inscription d'un vendeur marketplace. |
| `POST` | `/auth/token/refresh/` | Public | Renouvelle le jeton d'accès à partir du jeton de rafraîchissement. |
| `GET` `POST` | `/auth/users/` | Lecture connecté · écriture admin | Annuaire des utilisateurs (filtre `?role=`), création par un admin. |
| `PATCH` `DELETE` | `/auth/users/<uuid:user_id>/` | Lecture connecté · écriture admin | Modification ou suppression d'un utilisateur. |
| `GET` | `/auth/wallet/` | Connecté | Solde du portefeuille et historique. |

## Portefeuille de points (libre-service)

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `PATCH` | `/users/me/` **NOUVEAU** | Connecté | Alias de `/auth/me/`. |
| `POST` | `/users/me/avatar/` **NOUVEAU** | Connecté | Alias de `/auth/avatar/`. |
| `GET` `POST` | `/users/me/points/` **NOUVEAU** | Connecté | Portefeuille : solde et historique (GET), crédit ou débit (POST, `points` négatif = dépense). |
| `GET` | `/users/me/wallet/` **NOUVEAU** | Connecté | Alias de `/auth/wallet/`. |

## Intelligence artificielle — Karamo

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `POST` | `/ai/ask-image/` | Connecté | Analyse d'une image ou d'un énoncé photographié. |
| `POST` | `/ai/ask/` | Connecté | Pose une question à Karamo (réponse complète). |
| `POST` | `/ai/ask/stream/` | Connecté | Réponse de Karamo en flux continu (SSE). |
| `POST` | `/ai/generate-qcm/` | Connecté | Génère un QCM sur une matière et un niveau donnés. |
| `POST` | `/ai/qcm/<uuid:qcm_id>/submit/` | Connecté | Soumet les réponses d'un QCM et renvoie le score. |
| `GET` | `/ai/status/` | Connecté | Disponibilité du moteur IA et quota restant. |

## Bibliothèque pédagogique

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `POST` | `/learning/documents/` | Connecté | Documents pédagogiques : liste filtrable et création. |
| `GET` `PUT` `PATCH` `DELETE` | `/learning/documents/<uuid:pk>/` | Lecture connecté · écriture admin | Détail, modification ou suppression d'un document. |
| `POST` | `/learning/documents/upload/` | Connecté | Téléversement d'un fichier (PDF, image). |
| `GET` | `/learning/subjects/` | Connecté | Liste des matières. |

## Contenu éditorial

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `POST` | `/content/news/` | Lecture connecté · écriture admin | Actualités : liste publiée et publication. |
| `PATCH` `DELETE` | `/content/news/<uuid:pk>/` | Lecture connecté · écriture admin | Modification ou suppression d'une actualité. |
| `GET` | `/content/notifications/` | Connecté | Notifications de l'utilisateur connecté. |
| `POST` | `/content/notifications/<uuid:pk>/read/` | Connecté | Marque une notification comme lue. |
| `POST` | `/content/notifications/read/` | Connecté | Marque toutes les notifications comme lues. |
| `GET` `POST` | `/content/reading-progress/<str:document_id>/` | Connecté | Progression de lecture d'un document. |
| `GET` `POST` | `/content/scholarships/` **NOUVEAU** | Lecture connecté · écriture admin | Bourses d'études (filtres `?country=`, `?level=`, `?search=`). |
| `GET` `PATCH` `DELETE` | `/content/scholarships/<uuid:pk>/` **NOUVEAU** | Lecture connecté · écriture admin | Détail, modification ou suppression d'une bourse. |
| `GET` `POST` | `/content/school-rankings/` | Lecture connecté · écriture admin | Palmarès des établissements. |
| `GET` `PATCH` `DELETE` | `/content/school-rankings/<uuid:pk>/` **NOUVEAU** | Lecture connecté · écriture admin | Détail, modification ou retrait du palmarès. |
| `GET` `POST` | `/content/study-abroad/` | Lecture connecté · écriture admin | Programmes d'études à l'étranger. |
| `GET` `PATCH` `DELETE` | `/content/study-abroad/<uuid:pk>/` **NOUVEAU** | Lecture connecté · écriture admin | Détail, modification ou suppression d'un programme. |
| `GET` `POST` | `/content/tutor-ads/` | Connecté | Annonces de répétiteurs (filtres `?type=`, `?subject=`, `?location=`). |
| `DELETE` | `/content/tutor-ads/<uuid:pk>/` | Connecté | Suppression d'une annonce (auteur ou admin). |

## Espace École

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `POST` | `/ecole/absences/` | Portail école ou admin Kharandi | Absences : liste et déclaration. |
| `POST` | `/ecole/activate/` | Public | Active un établissement à partir de sa clé de licence. |
| `GET` `POST` | `/ecole/classes/` | Portail école ou admin Kharandi | Classes : liste et création. |
| `GET` `POST` | `/ecole/grades/` | Portail école ou admin Kharandi | Notes scolaires : consultation et saisie. |
| `POST` | `/ecole/login/` | Public | Connexion de l'administration d'un établissement. |
| `GET` | `/ecole/parent/<str:matricule>/` | Connecté | Consultation parent par matricule de l'élève. |
| `GET` | `/ecole/parents/students/<str:student_id>/badges/` | Connecté | Badges d'un élève, côté parent. |
| `GET` | `/ecole/parents/students/<str:student_id>/badges/<str:badge_id>/pdf/` | Connecté | Badge au format PDF. |
| `GET` `POST` `PATCH` | `/ecole/payments/` | Direction école ou admin Kharandi | Frais de scolarité : liste et enregistrement. |
| `GET` `POST` `PATCH` | `/ecole/payments/<str:payment_id>/` | Direction école ou admin Kharandi | Détail ou mise à jour d'un paiement scolaire. |
| `GET` `POST` | `/ecole/schools/` | Portail école ou admin Kharandi | Établissements : liste et création. |
| `GET` `PATCH` `DELETE` | `/ecole/schools/<str:school_id>/` | Portail école ou admin Kharandi | Détail, modification ou suppression d'un établissement. |
| `GET` `POST` | `/ecole/schools/<str:school_id>/students/` | Portail école ou admin Kharandi | Élèves d'un établissement : liste et inscription. |
| `DELETE` | `/ecole/schools/badges/<str:badge_id>/` | Direction école ou admin Kharandi | Révoque un badge. |
| `GET` | `/ecole/schools/badges/history/<str:school_id>/` | Direction école ou admin Kharandi | Historique des badges émis. |
| `POST` | `/ecole/schools/badges/issue/` | Direction école ou admin Kharandi | Émet un badge scolaire pour un élève. |
| `PATCH` `DELETE` | `/ecole/students/<str:student_id>/` | Direction école ou admin Kharandi | Modification ou radiation d'un élève. |
| `POST` | `/ecole/subscriptions/checkout-session/` | Direction école ou admin Kharandi | Crée une session de paiement d'abonnement. |
| `GET` | `/ecole/subscriptions/pricing/` | Public | Grille tarifaire des abonnements écoles. |
| `GET` | `/ecole/subscriptions/status/<str:school_id>/` | Direction école ou admin Kharandi | État de l'abonnement d'un établissement. |
| `POST` | `/ecole/teacher/login/` | Public | Connexion d'un enseignant. |
| `GET` `POST` `DELETE` | `/ecole/teachers/` | Direction école ou admin Kharandi | Enseignants : liste, ajout et suppression. |
| `GET` `POST` `DELETE` | `/ecole/teachers/<str:teacher_id>/` | Direction école ou admin Kharandi | Détail ou suppression d'un enseignant. |

## Notes

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `POST` | `/grades/` | Connecté | Notes de l'utilisateur : consultation et saisie. |
| `GET` | `/grades/students/` | Connecté | Élèves rattachés (vue parent ou enseignant). |

## Marketplace

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `POST` | `/marketplace/orders/` | Connecté | Passe une commande marketplace. |
| `POST` | `/marketplace/orders/redeem/` | Connecté | Règle une commande avec des points Kharandi. |
| `GET` `POST` | `/marketplace/products/` | Connecté | Produits : catalogue filtrable et mise en vente. |
| `PATCH` `DELETE` | `/marketplace/products/<uuid:pk>/` | Connecté | Modification ou retrait d'un produit. |
| `GET` | `/marketplace/products/mine/` | Connecté | Produits du vendeur connecté. |
| `GET` `POST` | `/marketplace/promos/` | Connecté | Codes promotionnels : liste et création. |
| `POST` | `/marketplace/promos/check/` | Connecté | Vérifie la validité d'un code promo. |
| `GET` `PATCH` | `/marketplace/seller/orders/` | Connecté | Commandes reçues par le vendeur. |
| `GET` `PATCH` | `/marketplace/seller/orders/<uuid:pk>/` | Connecté | Détail et changement de statut d'une commande. |

## Boutique (commandes)

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` | `/store/orders/` | Connecté | Historique des commandes de l'utilisateur. |
| `POST` | `/store/orders/create/` | Connecté | Création d'une commande à partir du panier. |

## Paiements et abonnements

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `POST` | `/payments/initiate/` | Connecté | Initie un paiement LengoPay (Orange Money, MTN). |
| `GET` `POST` | `/payments/plans/` | Lecture connecté · écriture admin | Formules d'abonnement : liste et création. |
| `PATCH` `DELETE` | `/payments/plans/<uuid:pk>/` | Lecture connecté · écriture admin | Modification ou suppression d'une formule. |
| `POST` | `/payments/run-cron/` | Public | Déclenche les tâches planifiées (protégé par `CRON_SECRET`). |
| `POST` | `/payments/subscriptions/initiate/` | Connecté | Souscription à une formule payante. |
| `GET` | `/payments/subscriptions/status/` | Connecté | État de l'abonnement de l'utilisateur. |
| `GET` | `/payments/transactions/` | Connecté | Historique des transactions. |
| `POST` | `/payments/webhook/` | Signature du prestataire | Callback LengoPay de confirmation de paiement. |

## Notifications

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `POST` | `/notifications/custom/` | Lecture connecté · écriture admin | Envoie une notification personnalisée (admin). |
| `GET` | `/notifications/stream/` | Connecté | Flux temps réel des notifications (SSE). |
| `POST` | `/notifications/welcome/` | Connecté | Envoie le SMS de bienvenue. |

## Support client

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` `POST` | `/support/tickets/` | Connecté | Tickets d'assistance : liste et ouverture. |
| `GET` `PATCH` | `/support/tickets/<uuid:pk>/` | Connecté | Détail et mise à jour d'un ticket. |

## Rapports et exports

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` | `/reports/stats/excel/` | Connecté | Export des statistiques au format Excel. |
| `GET` | `/reports/student/pdf/` | Connecté | Bulletin de l'élève au format PDF. |
| `GET` | `/reports/transactions/pdf/` | Connecté | Relevé des transactions au format PDF. |

## Recherche globale

| Méthodes | Endpoint | Accès | Description |
|---|---|---|---|
| `GET` | `/search/` | Connecté | Recherche transversale (documents, produits, actualités). |

## Endpoints ajoutés pour le frontend

Ces routes étaient appelées par le frontend Kharandi mais absentes du backend.

| Endpoint | Appelé depuis | Anomalie corrigée |
|---|---|---|
| `POST /auth/register/` | `Login.tsx` | Seules les variantes par rôle existaient — l'inscription générique renvoyait 404 |
| `GET` `POST /users/me/points/` | `Exercises.tsx`, `Marketplace.tsx` | Le préfixe `/users/` n'existait pas ; `/auth/me/points/` était réservé aux admins et refusait les valeurs négatives |
| `GET` `POST /content/scholarships/` | `content.ts` | Aucun modèle Bourse — le frontend retombait toujours sur les données fictives |
| `GET` `PATCH` `DELETE /content/scholarships/<uuid>/` | `AdminDashboard.tsx` | Administration des bourses impossible |
| `GET` `PATCH` `DELETE /content/school-rankings/<uuid>/` | `AdminDashboard.tsx` | Seule la vue liste existait |
| `GET` `PATCH` `DELETE /content/study-abroad/<uuid>/` | `AdminDashboard.tsx` | Seule la vue liste existait |
| `GET /healthz` | Infrastructure | Aucune sonde de santé pour Docker et Nginx |

Les routes `/users/me/`, `/users/me/avatar/` et `/users/me/wallet/` sont de simples alias de leurs équivalents `/auth/`, ajoutés par cohérence d'espace de noms.

## Hors périmètre du backend Django

| Endpoint | Servi par |
|---|---|
| `GET /api/results/search` | Serveur Express du frontend (`server.ts`) — recherche dans les résultats d'examens nationaux |
| `GET /api/results/cee2026` | Serveur Express du frontend — résultats CEE 2026 |
| `POST /api/chat` | Serveur Express du frontend — passerelle relayant vers `/api/v1/ai/ask/` |
