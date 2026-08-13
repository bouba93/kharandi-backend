#!/usr/bin/env python3
"""
gen_endpoints_doc.py
────────────────────
Génère ENDPOINTS.md : la liste complète et à jour des endpoints de l'API Kharandi,
directement depuis le routeur Django (donc jamais désynchronisée du code).

Usage :  python3 gen_endpoints_doc.py
"""
import os, django, inspect, datetime, collections

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kharandi_backend.settings")
django.setup()

from django.urls import get_resolver  # noqa: E402

# ── Nouveaux endpoints ajoutés lors de l'alignement avec le frontend ──────────
NEW = {
    "/api/v1/auth/register/",
    "/api/v1/users/me/points/",
    "/api/v1/users/me/",
    "/api/v1/users/me/avatar/",
    "/api/v1/users/me/wallet/",
    "/api/v1/content/scholarships/",
    "/api/v1/content/scholarships/<uuid:pk>/",
    "/api/v1/content/school-rankings/<uuid:pk>/",
    "/api/v1/content/study-abroad/<uuid:pk>/",
    "/healthz",
}

# ── Modules : titre lisible + ordre d'affichage ───────────────────────────────
MODULES = [
    ("_root",         "Racine et documentation"),
    ("auth",          "Authentification et comptes"),
    ("users",         "Portefeuille de points (libre-service)"),
    ("ai",            "Intelligence artificielle — Karamo"),
    ("learning",      "Bibliothèque pédagogique"),
    ("content",       "Contenu éditorial"),
    ("ecole",         "Espace École"),
    ("grades",        "Notes"),
    ("marketplace",   "Marketplace"),
    ("store",         "Boutique (commandes)"),
    ("payments",      "Paiements et abonnements"),
    ("notifications", "Notifications"),
    ("support",       "Support client"),
    ("reports",       "Rapports et exports"),
    ("search",        "Recherche globale"),
]

# ── Descriptions métier (prioritaires sur les docstrings) ────────────────────
DESC = {
    "/": "Statut de l'API et numéro de version.",
    "/healthz": "Sonde de santé : vérifie l'API et la connexion PostgreSQL.",
    "/api/schema/": "Schéma OpenAPI 3 brut (YAML).",
    "/api/docs/": "Documentation interactive Swagger UI.",

    # Auth
    "/api/v1/auth/login/": "Connexion : renvoie un JWT si appareil connu, sinon déclenche un OTP.",
    "/api/v1/auth/login/verify/": "Valide le code OTP de connexion et renvoie les jetons.",
    "/api/v1/auth/login/password/": "Connexion directe par numéro et mot de passe.",
    "/api/v1/auth/register/": "Inscription universelle (OTP + mot de passe + rôle).",
    "/api/v1/auth/register/otp/send/": "Envoie le code OTP d'inscription par SMS.",
    "/api/v1/auth/register/eleve/": "Inscription d'un élève (niveau, série).",
    "/api/v1/auth/register/parent/": "Inscription d'un parent, avec liaison à un enfant.",
    "/api/v1/auth/register/repetiteur/": "Inscription d'un répétiteur.",
    "/api/v1/auth/register/vendeur/": "Inscription d'un vendeur marketplace.",
    "/api/v1/auth/password/reset/request/": "Demande de réinitialisation du mot de passe (envoi OTP).",
    "/api/v1/auth/password/reset/confirm/": "Confirme la réinitialisation avec le code OTP.",
    "/api/v1/auth/otp/send/": "Envoi d'un OTP (voie historique).",
    "/api/v1/auth/otp/verify/": "Vérification d'un OTP (voie historique).",
    "/api/v1/auth/token/refresh/": "Renouvelle le jeton d'accès à partir du jeton de rafraîchissement.",
    "/api/v1/auth/me/": "Profil de l'utilisateur connecté (GET) et mise à jour (PATCH).",
    "/api/v1/auth/avatar/": "Envoi de la photo de profil (multipart).",
    "/api/v1/auth/me/points/": "Ajustement de points réservé aux administrateurs.",
    "/api/v1/auth/wallet/": "Solde du portefeuille et historique.",
    "/api/v1/auth/devices/": "Appareils de confiance : liste et révocation.",
    "/api/v1/auth/devices/reset/": "Réinitialise l'appareil de confiance (perte de téléphone).",
    "/api/v1/auth/users/": "Annuaire des utilisateurs (filtre `?role=`), création par un admin.",
    "/api/v1/auth/users/<uuid:user_id>/": "Modification ou suppression d'un utilisateur.",

    # Users
    "/api/v1/users/me/points/": "Portefeuille : solde et historique (GET), crédit ou débit (POST, `points` négatif = dépense).",
    "/api/v1/users/me/": "Alias de `/auth/me/`.",
    "/api/v1/users/me/avatar/": "Alias de `/auth/avatar/`.",
    "/api/v1/users/me/wallet/": "Alias de `/auth/wallet/`.",

    # IA
    "/api/v1/ai/status/": "Disponibilité du moteur IA et quota restant.",
    "/api/v1/ai/ask/": "Pose une question à Karamo (réponse complète).",
    "/api/v1/ai/ask/stream/": "Réponse de Karamo en flux continu (SSE).",
    "/api/v1/ai/ask-image/": "Analyse d'une image ou d'un énoncé photographié.",
    "/api/v1/ai/generate-qcm/": "Génère un QCM sur une matière et un niveau donnés.",
    "/api/v1/ai/qcm/<uuid:qcm_id>/submit/": "Soumet les réponses d'un QCM et renvoie le score.",

    # Learning
    "/api/v1/learning/documents/": "Documents pédagogiques : liste filtrable et création.",
    "/api/v1/learning/documents/upload/": "Téléversement d'un fichier (PDF, image).",
    "/api/v1/learning/documents/<uuid:pk>/": "Détail, modification ou suppression d'un document.",
    "/api/v1/learning/subjects/": "Liste des matières.",

    # Content
    "/api/v1/content/news/": "Actualités : liste publiée et publication.",
    "/api/v1/content/news/<uuid:pk>/": "Modification ou suppression d'une actualité.",
    "/api/v1/content/school-rankings/": "Palmarès des établissements.",
    "/api/v1/content/school-rankings/<uuid:pk>/": "Détail, modification ou retrait du palmarès.",
    "/api/v1/content/study-abroad/": "Programmes d'études à l'étranger.",
    "/api/v1/content/study-abroad/<uuid:pk>/": "Détail, modification ou suppression d'un programme.",
    "/api/v1/content/scholarships/": "Bourses d'études (filtres `?country=`, `?level=`, `?search=`).",
    "/api/v1/content/scholarships/<uuid:pk>/": "Détail, modification ou suppression d'une bourse.",
    "/api/v1/content/tutor-ads/": "Annonces de répétiteurs (filtres `?type=`, `?subject=`, `?location=`).",
    "/api/v1/content/tutor-ads/<uuid:pk>/": "Suppression d'une annonce (auteur ou admin).",
    "/api/v1/content/notifications/": "Notifications de l'utilisateur connecté.",
    "/api/v1/content/notifications/read/": "Marque toutes les notifications comme lues.",
    "/api/v1/content/notifications/<uuid:pk>/read/": "Marque une notification comme lue.",
    "/api/v1/content/reading-progress/<str:document_id>/": "Progression de lecture d'un document.",

    # École
    "/api/v1/ecole/schools/": "Établissements : liste et création.",
    "/api/v1/ecole/schools/<str:school_id>/": "Détail, modification ou suppression d'un établissement.",
    "/api/v1/ecole/schools/<str:school_id>/students/": "Élèves d'un établissement : liste et inscription.",
    "/api/v1/ecole/activate/": "Active un établissement à partir de sa clé de licence.",
    "/api/v1/ecole/login/": "Connexion de l'administration d'un établissement.",
    "/api/v1/ecole/teacher/login/": "Connexion d'un enseignant.",
    "/api/v1/ecole/subscriptions/pricing/": "Grille tarifaire des abonnements écoles.",
    "/api/v1/ecole/subscriptions/checkout-session/": "Crée une session de paiement d'abonnement.",
    "/api/v1/ecole/subscriptions/status/<str:school_id>/": "État de l'abonnement d'un établissement.",
    "/api/v1/ecole/schools/badges/issue/": "Émet un badge scolaire pour un élève.",
    "/api/v1/ecole/schools/badges/history/<str:school_id>/": "Historique des badges émis.",
    "/api/v1/ecole/schools/badges/<str:badge_id>/": "Révoque un badge.",
    "/api/v1/ecole/parent/<str:matricule>/": "Consultation parent par matricule de l'élève.",
    "/api/v1/ecole/parents/students/<str:student_id>/badges/": "Badges d'un élève, côté parent.",
    "/api/v1/ecole/parents/students/<str:student_id>/badges/<str:badge_id>/pdf/": "Badge au format PDF.",
    "/api/v1/ecole/students/<str:student_id>/": "Modification ou radiation d'un élève.",
    "/api/v1/ecole/grades/": "Notes scolaires : consultation et saisie.",
    "/api/v1/ecole/payments/": "Frais de scolarité : liste et enregistrement.",
    "/api/v1/ecole/payments/<str:payment_id>/": "Détail ou mise à jour d'un paiement scolaire.",
    "/api/v1/ecole/absences/": "Absences : liste et déclaration.",
    "/api/v1/ecole/teachers/": "Enseignants : liste, ajout et suppression.",
    "/api/v1/ecole/teachers/<str:teacher_id>/": "Détail ou suppression d'un enseignant.",
    "/api/v1/ecole/classes/": "Classes : liste et création.",

    # Grades
    "/api/v1/grades/": "Notes de l'utilisateur : consultation et saisie.",
    "/api/v1/grades/students/": "Élèves rattachés (vue parent ou enseignant).",

    # Marketplace
    "/api/v1/marketplace/products/": "Produits : catalogue filtrable et mise en vente.",
    "/api/v1/marketplace/products/mine/": "Produits du vendeur connecté.",
    "/api/v1/marketplace/products/<uuid:pk>/": "Modification ou retrait d'un produit.",
    "/api/v1/marketplace/promos/": "Codes promotionnels : liste et création.",
    "/api/v1/marketplace/promos/check/": "Vérifie la validité d'un code promo.",
    "/api/v1/marketplace/orders/": "Passe une commande marketplace.",
    "/api/v1/marketplace/orders/redeem/": "Règle une commande avec des points Kharandi.",
    "/api/v1/marketplace/seller/orders/": "Commandes reçues par le vendeur.",
    "/api/v1/marketplace/seller/orders/<uuid:pk>/": "Détail et changement de statut d'une commande.",

    # Store
    "/api/v1/store/orders/": "Historique des commandes de l'utilisateur.",
    "/api/v1/store/orders/create/": "Création d'une commande à partir du panier.",

    # Payments
    "/api/v1/payments/plans/": "Formules d'abonnement : liste et création.",
    "/api/v1/payments/plans/<uuid:pk>/": "Modification ou suppression d'une formule.",
    "/api/v1/payments/initiate/": "Initie un paiement LengoPay (Orange Money, MTN).",
    "/api/v1/payments/webhook/": "Callback LengoPay de confirmation de paiement.",
    "/api/v1/payments/transactions/": "Historique des transactions.",
    "/api/v1/payments/subscriptions/status/": "État de l'abonnement de l'utilisateur.",
    "/api/v1/payments/subscriptions/initiate/": "Souscription à une formule payante.",
    "/api/v1/payments/run-cron/": "Déclenche les tâches planifiées (protégé par `CRON_SECRET`).",

    # Notifications
    "/api/v1/notifications/welcome/": "Envoie le SMS de bienvenue.",
    "/api/v1/notifications/custom/": "Envoie une notification personnalisée (admin).",
    "/api/v1/notifications/stream/": "Flux temps réel des notifications (SSE).",

    # Support
    "/api/v1/support/tickets/": "Tickets d'assistance : liste et ouverture.",
    "/api/v1/support/tickets/<uuid:pk>/": "Détail et mise à jour d'un ticket.",

    # Reports
    "/api/v1/reports/transactions/pdf/": "Relevé des transactions au format PDF.",
    "/api/v1/reports/student/pdf/": "Bulletin de l'élève au format PDF.",
    "/api/v1/reports/stats/excel/": "Export des statistiques au format Excel.",

    # Search
    "/api/v1/search/": "Recherche transversale (documents, produits, actualités).",
}

PERM_LABEL = {
    "AllowAny":                     "Public",
    "IsAuthenticated":              "Connecté",
    "IsAdmin":                      "Admin Kharandi",
    "IsAdminUser":                  "Admin Kharandi",
    "IsAdminOrReadOnly":            "Lecture connecté · écriture admin",
    "IsPortalOrKharandiAdmin":      "Portail école ou admin Kharandi",
    "IsSchoolAdminOrKharandiAdmin": "Direction école ou admin Kharandi",
    "IsSchoolStaff":                "Personnel école",
    "WebhookPermission":            "Signature du prestataire",
}

# Vues déclarées `IsAuthenticated` mais qui restreignent les écritures à un
# administrateur à l'intérieur de la méthode (contrôle `IsAdmin` en ligne).
ADMIN_WRITE = {
    "/api/v1/content/news/",
    "/api/v1/content/news/<uuid:pk>/",
    "/api/v1/content/school-rankings/",
    "/api/v1/content/school-rankings/<uuid:pk>/",
    "/api/v1/content/study-abroad/",
    "/api/v1/content/study-abroad/<uuid:pk>/",
    "/api/v1/content/scholarships/",
    "/api/v1/content/scholarships/<uuid:pk>/",
    "/api/v1/payments/plans/",
    "/api/v1/payments/plans/<uuid:pk>/",
    "/api/v1/auth/users/",
    "/api/v1/auth/users/<uuid:user_id>/",
    "/api/v1/auth/me/points/",
    "/api/v1/notifications/custom/",
}


def collect():
    rows = []

    def walk(resolver, prefix=""):
        for entry in resolver.url_patterns:
            if hasattr(entry, "url_patterns"):
                walk(entry, prefix + str(entry.pattern))
                continue
            path = "/" + prefix + str(entry.pattern)
            if path.startswith("/admin/"):
                continue
            cb = entry.callback
            cls = getattr(cb, "cls", getattr(cb, "view_class", None))
            methods = [m.upper() for m in ("get", "post", "put", "patch", "delete")
                       if cls and hasattr(cls, m)]
            perms = [PERM_LABEL.get(c.__name__, c.__name__)
                     for c in getattr(cls, "permission_classes", [])] if cls else []
            if path in ADMIN_WRITE:
                perms = ["Lecture connecté · écriture admin"]
            doc = (inspect.getdoc(cls) or "").split("\n")[0].strip() if cls else ""
            rows.append({
                "path":    path,
                "methods": methods or ["GET"],
                "view":    cls.__name__ if cls else cb.__name__,
                "perms":   ", ".join(perms) or "Public",
                "desc":    DESC.get(path) or doc or "—",
            })

    walk(get_resolver())
    return rows


def module_of(path):
    if not path.startswith("/api/v1/"):
        return "_root"
    return path.split("/")[3]


def main():
    rows = collect()
    by_mod = collections.defaultdict(list)
    for r in rows:
        by_mod[module_of(r["path"])].append(r)

    total_routes = len(rows)
    total_ops = sum(len(r["methods"]) for r in rows)
    today = datetime.date.today().strftime("%d/%m/%Y")

    L = []
    add = L.append

    add("# API Kharandi — Liste complète des endpoints")
    add("")
    add(f"**Généré le {today}** depuis le routeur Django · `python3 gen_endpoints_doc.py`")
    add("")
    add(f"- **{total_routes} routes** exposées, soit **{total_ops} opérations HTTP**")
    add("- **URL de base** : `http://212.95.33.158/api/v1` (VPS YIGUI) — variable `VITE_API_URL` côté frontend")
    add("- **Documentation interactive** : `/api/docs/` · **Schéma OpenAPI** : `/api/schema/`")
    add("- Les endpoints marqués **NOUVEAU** ont été ajoutés pour combler les appels du frontend restés sans route.")
    add("")

    add("## Conventions")
    add("")
    add("**Authentification** — jeton JWT dans l'en-tête, plus l'identifiant d'appareil de confiance :")
    add("")
    add("```http")
    add("Authorization: Bearer <access_token>")
    add("X-Device-Token: <device_token>")
    add("```")
    add("")
    add("Le jeton d'accès expire ; le frontend le renouvelle automatiquement via `POST /auth/token/refresh/`.")
    add("")
    add("**Format de réponse** — uniforme sur toute l'API :")
    add("")
    add("```json")
    add('{ "success": true, "message": "Succès", "data": { } }')
    add("```")
    add("")
    add("```json")
    add('{ "success": false, "message": "Code OTP incorrect.", "errors": { } }')
    add("```")
    add("")
    add("**Codes de statut** — `200` succès · `201` créé · `400` requête invalide · "
        "`401` jeton absent ou expiré · `403` droits insuffisants · `404` introuvable · `500` erreur serveur.")
    add("")
    add("**Colonne Accès** — `Public` : aucun jeton requis · `Connecté` : jeton JWT valide · "
        "`Admin Kharandi` : rôle administrateur · `Lecture connecté · écriture admin` : "
        "consultation ouverte aux comptes connectés, création et suppression réservées aux administrateurs.")
    add("")
    add("**Pagination** — les listes acceptent `?page=` et `?page_size=` et renvoient "
        "`{ count, next, previous, results }` dans `data`.")
    add("")

    add("## Sommaire")
    add("")
    add("| Module | Préfixe | Routes |")
    add("|---|---|---|")
    for key, title in MODULES:
        if key not in by_mod:
            continue
        prefix = "—" if key == "_root" else f"`/api/v1/{key}/`"
        anchor = title.lower().replace(" ", "-").replace("—", "").replace("(", "").replace(")", "")
        anchor = "-".join(filter(None, anchor.split("-")))
        add(f"| [{title}](#{anchor}) | {prefix} | {len(by_mod[key])} |")
    add(f"| **Total** | | **{total_routes}** |")
    add("")

    for key, title in MODULES:
        if key not in by_mod:
            continue
        add(f"## {title}")
        add("")
        add("| Méthodes | Endpoint | Accès | Description |")
        add("|---|---|---|---|")
        for r in sorted(by_mod[key], key=lambda x: x["path"]):
            flag = " **NOUVEAU**" if r["path"] in NEW else ""
            methods = "`" + "` `".join(r["methods"]) + "`"
            path = r["path"].replace("/api/v1", "") if key != "_root" else r["path"]
            add(f"| {methods} | `{path}`{flag} | {r['perms']} | {r['desc']} |")
        add("")

    add("## Endpoints ajoutés pour le frontend")
    add("")
    add("Ces routes étaient appelées par le frontend Kharandi mais absentes du backend.")
    add("")
    add("| Endpoint | Appelé depuis | Anomalie corrigée |")
    add("|---|---|---|")
    add("| `POST /auth/register/` | `Login.tsx` | Seules les variantes par rôle existaient — l'inscription générique renvoyait 404 |")
    add("| `GET` `POST /users/me/points/` | `Exercises.tsx`, `Marketplace.tsx` | Le préfixe `/users/` n'existait pas ; `/auth/me/points/` était réservé aux admins et refusait les valeurs négatives |")
    add("| `GET` `POST /content/scholarships/` | `content.ts` | Aucun modèle Bourse — le frontend retombait toujours sur les données fictives |")
    add("| `GET` `PATCH` `DELETE /content/scholarships/<uuid>/` | `AdminDashboard.tsx` | Administration des bourses impossible |")
    add("| `GET` `PATCH` `DELETE /content/school-rankings/<uuid>/` | `AdminDashboard.tsx` | Seule la vue liste existait |")
    add("| `GET` `PATCH` `DELETE /content/study-abroad/<uuid>/` | `AdminDashboard.tsx` | Seule la vue liste existait |")
    add("| `GET /healthz` | Infrastructure | Aucune sonde de santé pour Docker et Nginx |")
    add("")
    add("Les routes `/users/me/`, `/users/me/avatar/` et `/users/me/wallet/` sont de simples alias "
        "de leurs équivalents `/auth/`, ajoutés par cohérence d'espace de noms.")
    add("")

    add("## Hors périmètre du backend Django")
    add("")
    add("| Endpoint | Servi par |")
    add("|---|---|")
    add("| `GET /api/results/search` | Serveur Express du frontend (`server.ts`) — recherche dans les résultats d'examens nationaux |")
    add("| `GET /api/results/cee2026` | Serveur Express du frontend — résultats CEE 2026 |")
    add("| `POST /api/chat` | Serveur Express du frontend — passerelle relayant vers `/api/v1/ai/ask/` |")
    add("")

    out = "ENDPOINTS.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"{out} généré — {total_routes} routes, {total_ops} opérations HTTP.")


if __name__ == "__main__":
    main()
