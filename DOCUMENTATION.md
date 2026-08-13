# 📚 Documentation Complète — Kharandi Backend v4

> **Backend Django 5** · **PostgreSQL** · **JWT** · **Nimba SMS** · **LengoPay** · **Gemini AI** · **Cloudinary**
> URL : `https://backfinal-xxxl.onrender.com/api/v1`
> Swagger : `https://backfinal-xxxl.onrender.com/api/docs/`

---

## 📋 Table des matières

1. [Déploiement Render](#1-déploiement-render)
2. [Variables d'environnement](#2-variables-denvironnement)
3. [Authentification](#3-authentification)
4. [Onboarding](#4-onboarding)
5. [Documents & Librairie](#5-documents--librairie)
6. [IA & QCM](#6-ia--qcm)
7. [Paiements LengoPay](#7-paiements-lengopay)
8. [Abonnements](#8-abonnements)
9. [Boutique Vendeur](#9-boutique-vendeur)
10. [Support Tickets](#10-support-tickets)
11. [Notifications SMS](#11-notifications-sms)
12. [Rapports](#12-rapports)
13. [Recherche](#13-recherche)
14. [Tableau récapitulatif des endpoints](#14-tableau-récapitulatif)
15. [Codes d'erreur](#15-codes-derreur)
16. [Format des réponses](#16-format-des-réponses)

---

## 1. Déploiement Render

### Build Command
```
pip install -r requirements.txt
```

### Start Command
```
bash start.sh
```

Ce que fait `start.sh` automatiquement :
1. Teste la connexion base de données
2. Lance `python manage.py migrate`
3. Crée la table de cache
4. Copie les fichiers statiques
5. Crée les données initiales (plans + matières)
6. Crée le superadmin si inexistant
7. Lance Gunicorn sur `$PORT`

---

## 2. Variables d'environnement

| Variable | Obligatoire | Description |
|---|:---:|---|
| `SECRET_KEY` | ✅ | Clé secrète Django (longue chaîne aléatoire) |
| `DATABASE_URL` | ✅ | URL PostgreSQL Render (Internal URL) |
| `ALLOWED_HOSTS` | ✅ | Ex: `backfinal-xxxl.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | ✅ | Ex: `https://kharandi.gn,https://www.kharandi.gn` |
| `NIMBA_ACCOUNT_SID` | ✅ | Service ID Nimba SMS |
| `NIMBA_AUTH_TOKEN` | ✅ | Secret Token Nimba SMS |
| `NIMBA_SENDER_NAME` | ✅ | `Kharandi` |
| `LENGOPAY_SITE_ID` | ✅ | ID Site LengoPay |
| `LENGOPAY_LICENSE_KEY` | ✅ | Clé licence LengoPay |
| `LENGOPAY_CURRENCY` | ✅ | `GNF` |
| `LENGOPAY_COUNTRY` | ✅ | `GN` |
| `GEMINI_API_KEY` | ✅ | Clé Google AI Studio |
| `FRONTEND_URL` | ✅ | `https://kharandi.gn` |
| `ADMIN_PHONE` | ✅ | `+224627382173` |
| `ADMIN_PASSWORD` | ✅ | Mot de passe admin |
| `USE_CLOUDINARY` | ❌ | `True` pour activer Cloudinary |
| `CLOUDINARY_CLOUD_NAME` | ❌ | Nom cloud Cloudinary |
| `CLOUDINARY_API_KEY` | ❌ | Clé API Cloudinary |
| `CLOUDINARY_API_SECRET` | ❌ | Secret API Cloudinary |
| `DEBUG` | ❌ | `False` en production |

---

## 3. Authentification

### Connexion (compte existant) — SANS OTP
```http
POST /api/v1/auth/login/
Content-Type: application/json

{ "phone": "+224XXXXXXXXX" }
```

**Réponse 200 :**
```json
{
  "success": true,
  "data": {
    "user": { "id": "uuid", "phone": "+224...", "role": "STUDENT", "profile": {...} },
    "tokens": { "access": "eyJ...", "refresh": "eyJ..." }
  }
}
```

**Erreur 404 :** Aucun compte — doit s'inscrire.

---

### Inscription — AVEC OTP

**Étape 1 : Envoyer le code**
```http
POST /api/v1/auth/otp/send/
{ "phone": "+224XXXXXXXXX" }
```

**Étape 2 : Vérifier le code**
```http
POST /api/v1/auth/otp/verify/
{
  "phone": "+224XXXXXXXXX",
  "code":  "123456",
  "role":  "STUDENT"  // STUDENT | TUTOR | PARENT
}
```
→ Retourne `{ user, tokens }`. `onboarding_completed: false` → déclenche l'onboarding.

---

### Rafraîchir le token
```http
POST /api/v1/auth/token/refresh/
{ "refresh": "eyJ..." }
```

---

### Header d'authentification
Toutes les requêtes protégées doivent inclure :
```http
Authorization: Bearer <access_token>
```

---

## 4. Onboarding

L'onboarding est géré côté frontend (`Onboarding.tsx`).
Le backend expose deux endpoints :

### Mettre à jour le profil (étapes 1 et 2)
```http
PATCH /api/v1/auth/me/
{
  "first_name": "Sékou",
  "last_name":  "Camara",
  "city":       "Ratoma",
  "school_level": "Terminale",
  "role":       "STUDENT"
}
```

### Finaliser l'onboarding (étape 3)
```http
PATCH /api/v1/auth/me/
{ "onboarding_completed": true }
```
→ Après cet appel, `App.tsx` arrête d'afficher l'Onboarding et redirige vers le Dashboard.

---

### Upload avatar
```http
POST /api/v1/auth/avatar/
Content-Type: multipart/form-data

avatar: <fichier image>
```

---

## 5. Documents & Librairie

### Lister les documents
```http
GET /api/v1/learning/documents/
```
**Filtres disponibles :**
- `?level=Terminale`
- `?doc_type=COURS` (COURS | LIVRE | EXERCICE | CORRECTION | VIDEO)
- `?is_free=true`
- `?subject=<id>`
- `?search=mathématiques`

> Les utilisateurs sans abonnement actif ne voient que `is_free=true`.

### Détail d'un document
```http
GET /api/v1/learning/documents/<uuid>/
```

### Upload document (admin uniquement)
```http
POST /api/v1/learning/documents/upload/
Content-Type: multipart/form-data

title:       "Cours Maths Terminale"
doc_type:    "COURS"
subject:     <id matière>
level:       "Terminale"
is_free:     false
description: "Cours complet..."
file:        <fichier PDF ou MP4>
thumbnail:   <image de couverture>
```

### Lister les matières
```http
GET /api/v1/learning/subjects/
```

---

## 6. IA & QCM

### Chat avec Kharandi AI
```http
POST /api/v1/ai/ask/
{
  "message": "Explique-moi le théorème de Pythagore",
  "history": [
    { "role": "user",      "content": "Bonjour" },
    { "role": "assistant", "content": "Bonjour ! Comment puis-je t'aider ?" }
  ]
}
```

La réponse précise `web_search` et `guinea_knowledge`. Le second vaut `true` lorsque Karamo a injecté des fiches sourcées de sa base guinéenne. Les fiches initiales sont chargées avec `python manage.py seed_guinea_knowledge` et restent modifiables depuis l'administration Django.

### Générer un QCM
```http
POST /api/v1/ai/generate-qcm/
{
  "subject":    "Mathématiques",
  "level":      "Terminale",
  "topic":      "Dérivées et primitives",
  "difficulty": "MOYEN"  // FACILE | MOYEN | DIFFICILE
}
```
→ Retourne `{ qcm_id, questions: [{id, question, options}] }`. Les solutions et explications restent privées jusqu'à la soumission.

### Soumettre les réponses
```http
POST /api/v1/ai/qcm/<qcm_id>/submit/
{ "answers": { "1": 2, "2": 0, "3": 3 } }
```
→ Retourne `{ score, correct, total, results, points_earned }`, avec les solutions et explications.

---

## 7. Paiements LengoPay

### Flux de paiement

```
1. Frontend → POST /payments/subscriptions/initiate/
   Backend  → POST portal.lengopay.com/api/v1/payments
   Réponse  → { payment_url }

2. Frontend → window.location.href = payment_url
   Utilisateur paie sur LengoPay

3. LengoPay → POST /payments/webhook/ (callback automatique)
   Backend  → active l'abonnement + envoie SMS confirmation

4. LengoPay → redirige vers return_url (/payment/success?ref=KHR-xxx)
```

### Initier un paiement abonnement
```http
POST /api/v1/payments/subscriptions/initiate/
{
  "plan_id":  "uuid-du-plan",  // OU "seller" | "mensuel" | "annuel"
  "currency": "GNF"
}
```

### Paiement direct (commande)
```http
POST /api/v1/payments/initiate/
{
  "amount":   25000,
  "currency": "GNF",
  "order_id": "uuid"  // optionnel
}
```

### Webhook LengoPay (interne)
```http
POST /api/v1/payments/webhook/
{
  "pay_id": "WTVWaT...",
  "status": "SUCCESS",
  "amount": 25000,
  "message": "Transaction Successful",
  "Client": "624897845"
}
```

---

## 8. Abonnements

### Voir les plans disponibles
```http
GET /api/v1/payments/plans/
```

### Statut d'abonnement
```http
GET /api/v1/payments/subscriptions/status/
```
→ `{ is_premium, status, plan, end_date }`

### Historique des transactions
```http
GET /api/v1/payments/transactions/
```

---

## 9. Boutique Vendeur

Le plan **"Boutique Vendeur"** (50 000 GNF / semestre) est créé automatiquement par `seed_data`.

### Initier le paiement boutique depuis l'Onboarding
```http
POST /api/v1/payments/subscriptions/initiate/
{
  "plan_id":  "seller",  // ✅ accepté (pas besoin de l'UUID)
  "currency": "GNF"
}
```
ou avec le montant direct :
```http
POST /api/v1/payments/subscriptions/initiate/
{
  "amount":   50000,
  "currency": "GNF"
}
```

---

## 10. Support Tickets

### Créer un ticket
```http
POST /api/v1/support/tickets/
{
  "title":       "Problème de connexion",
  "description": "Je n'arrive pas à me connecter depuis hier.",
  "category":    "TECHNIQUE",  // PAIEMENT | TECHNIQUE | CONTENU | ABONNEMENT | AUTRE
  "priority":    2
}
```

### Lister mes tickets
```http
GET /api/v1/support/tickets/
GET /api/v1/support/tickets/?status=OUVERT
```

### Répondre / changer statut (admin)
```http
PATCH /api/v1/support/tickets/<uuid>/
{
  "message": "Votre problème a été résolu.",
  "status":  "RESOLU"
}
```

---

## 11. Notifications SMS

### SMS de bienvenue
```http
POST /api/v1/notifications/welcome/
```

### SMS personnalisé (admin uniquement)
```http
POST /api/v1/notifications/custom/
{
  "phones":  ["+224XXXXXXXXX", "+224YYYYYYYYY"],
  "message": "📚 Nouveaux cours disponibles !"
}
```

---

## 12. Rapports

### PDF transactions
```http
GET /api/v1/reports/transactions/pdf/
```

### PDF bulletin élève
```http
GET /api/v1/reports/student/pdf/
```

### Excel statistiques (admin)
```http
GET /api/v1/reports/stats/excel/
```

---

## 13. Recherche

```http
GET /api/v1/search/?q=mathématiques&type=all&limit=10
```
**Paramètres :**
- `q` : terme de recherche (min 2 caractères)
- `type` : `docs` | `qcm` | `all`
- `limit` : max 50

---

## 14. Tableau récapitulatif

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|:----:|
| POST | `/auth/login/` | Connexion directe sans OTP | ❌ |
| POST | `/auth/otp/send/` | Envoyer code OTP (inscription) | ❌ |
| POST | `/auth/otp/verify/` | Vérifier OTP + créer compte | ❌ |
| GET | `/auth/me/` | Mon profil | ✅ |
| PATCH | `/auth/me/` | Modifier profil + finaliser onboarding | ✅ |
| POST | `/auth/avatar/` | Upload photo de profil | ✅ |
| POST | `/auth/token/refresh/` | Renouveler token JWT | ❌ |
| GET | `/auth/users/` | Liste utilisateurs (admin) | ✅ |
| PATCH | `/auth/users/<id>/` | Modifier user (admin) | ✅ |
| GET | `/learning/documents/` | Liste documents | ✅ |
| POST | `/learning/documents/upload/` | Upload document (admin) | ✅ |
| GET | `/learning/documents/<id>/` | Détail document | ✅ |
| DELETE | `/learning/documents/<id>/` | Supprimer document (admin) | ✅ |
| GET | `/learning/subjects/` | Liste matières | ✅ |
| POST | `/ai/ask/` | Chat Kharandi AI | ✅ |
| POST | `/ai/generate-qcm/` | Générer QCM | ✅ |
| POST | `/ai/qcm/<id>/submit/` | Soumettre réponses QCM | ✅ |
| GET | `/payments/plans/` | Plans disponibles | ✅ |
| GET | `/payments/subscriptions/status/` | Mon abonnement | ✅ |
| POST | `/payments/subscriptions/initiate/` | Initier paiement (UUID ou "seller") | ✅ |
| POST | `/payments/initiate/` | Paiement direct | ✅ |
| POST | `/payments/webhook/` | Callback LengoPay | ❌ |
| GET | `/payments/transactions/` | Mes transactions | ✅ |
| GET | `/store/orders/` | Mes commandes | ✅ |
| POST | `/store/orders/create/` | Créer commande | ✅ |
| POST | `/notifications/welcome/` | SMS bienvenue | ✅ |
| POST | `/notifications/custom/` | SMS groupé (admin) | ✅ |
| GET | `/support/tickets/` | Mes tickets | ✅ |
| POST | `/support/tickets/` | Créer ticket | ✅ |
| GET | `/support/tickets/<id>/` | Détail ticket | ✅ |
| PATCH | `/support/tickets/<id>/` | Répondre (admin) | ✅ |
| GET | `/reports/transactions/pdf/` | PDF transactions | ✅ |
| GET | `/reports/student/pdf/` | PDF bulletin | ✅ |
| GET | `/reports/stats/excel/` | Excel stats (admin) | ✅ |
| GET | `/search/?q=` | Recherche globale | ✅ |

---

## 15. Codes d'erreur

| Code | Signification |
|------|---------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Données invalides |
| 401 | Non authentifié (token manquant ou expiré) |
| 403 | Accès refusé (rôle insuffisant) |
| 404 | Ressource introuvable |
| 500 | Erreur interne Django |
| 502 | LengoPay indisponible |
| 503 | Nimba SMS indisponible |

---

## 16. Format des réponses

### Succès
```json
{
  "success": true,
  "message": "...",
  "data":    { ... }
}
```

### Erreur
```json
{
  "success": false,
  "message": "...",
  "errors":  { "field": ["message d'erreur"] }
}
```

---

## Notes techniques

**Stockage fichiers :**
- `USE_CLOUDINARY=False` → stockage local (perdu au redéploiement Render)
- `USE_CLOUDINARY=True`  → Cloudinary (persistant, recommandé en production)

**Tokens JWT :**
- Access token : valide 7 jours
- Refresh token : valide 30 jours, rotation automatique

**OTP :**
- Valide 5 minutes
- 5 tentatives maximum
- Code à 6 chiffres
- Géré par Nimba SMS `/v1/verifications`

**Plans disponibles après seed_data :**
- `Gratuit` → 0 GNF, accès limité
- `Premium Mensuel` → 25 000 GNF/mois
- `Premium Annuel` → 250 000 GNF/an
- `Boutique Vendeur` → 50 000 GNF/semestre


---

## Mise à jour v5 — Endpoints admin ajoutés

### Gestion utilisateurs (Admin)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/auth/users/` | Liste tous les utilisateurs |
| POST | `/auth/users/` | Créer un utilisateur |
| PATCH | `/auth/users/<id>/` | Modifier rôle / statut / profil |
| DELETE | `/auth/users/<id>/` | Supprimer un utilisateur |

#### Créer un utilisateur (admin)
```http
POST /api/v1/auth/users/
{
  "phone":        "+224XXXXXXXXX",
  "role":         "STUDENT",
  "password":     "Kharandi2026!",
  "first_name":   "Sékou",
  "last_name":    "Camara",
  "city":         "Conakry",
  "school_level": "Terminale",
  "is_active":    true
}
```

#### Modifier un utilisateur (admin)
```http
PATCH /api/v1/auth/users/<uuid>/
{
  "role":      "TUTOR",
  "is_active": false,
  "first_name": "Amadou"
}
```

#### Supprimer un utilisateur (admin)
```http
DELETE /api/v1/auth/users/<uuid>/
```
> Le superadmin (`is_superuser=True`) ne peut pas être supprimé.

---

### Gestion Plans (Admin)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/payments/plans/` | Liste plans actifs |
| POST | `/payments/plans/` | Créer un plan |
| PATCH | `/payments/plans/<id>/` | Modifier un plan |
| DELETE | `/payments/plans/<id>/` | Désactiver un plan |

#### Créer un plan (admin)
```http
POST /api/v1/payments/plans/
{
  "name":     "Premium Mensuel",
  "period":   "MENSUEL",
  "price":    25000,
  "currency": "GNF",
  "features": ["Accès illimité", "QCM illimités", "IA Tutor"],
  "is_active": true
}
```

> `DELETE` désactive le plan (`is_active=False`) au lieu de le supprimer physiquement,
> pour préserver les abonnements existants.

---

### Corrections v5

- `create_superadmin` force désormais `role=ADMIN` même si le compte existait déjà
- `TransactionSerializer` inclut maintenant `user_phone` pour l'affichage admin
- `TransactionListView` : l'admin voit toutes les transactions, les autres uniquement les leurs
