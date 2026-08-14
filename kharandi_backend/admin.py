from django.contrib import admin
from unfold.admin import ModelAdmin


# ─────────────────────────────────────────────────────────────
# Kharandi Admin — Configuration générale
# ─────────────────────────────────────────────────────────────

admin.site.site_header = "Kharandi Administration"
admin.site.site_title = "Kharandi Admin"
admin.site.index_title = "Tableau de bord Kharandi"


# ─────────────────────────────────────────────────────────────
# Branding / navigation Unfold
# ─────────────────────────────────────────────────────────────

UNFOLD = {
    "SITE_TITLE": "Kharandi Admin",
    "SITE_HEADER": "Kharandi",
    "SITE_SYMBOL": "school",

    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,

        "navigation": [
            {
                "title": "Kharandi",
                "separator": True,
                "items": [
                    {
                        "title": "Utilisateurs",
                        "icon": "people",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Profils",
                        "icon": "person",
                        "link": "/admin/users/profile/",
                    },
                ],
            },

            {
                "title": "Formation",
                "separator": True,
                "items": [
                    {
                        "title": "Matières",
                        "icon": "menu_book",
                        "link": "/admin/learning/subject/",
                    },
                    {
                        "title": "Documents",
                        "icon": "description",
                        "link": "/admin/learning/document/",
                    },
                    {
                        "title": "QCM",
                        "icon": "quiz",
                        "link": "/admin/learning/qcm/",
                    },
                ],
            },

            {
                "title": "Intelligence artificielle",
                "separator": True,
                "items": [
                    {
                        "title": "Base de connaissances",
                        "icon": "psychology",
                        "link": "/admin/ai_features/guineaknowledgeentry/",
                    },
                ],
            },

            {
                "title": "Paiements",
                "separator": True,
                "items": [
                    {
                        "title": "Plans",
                        "icon": "payments",
                        "link": "/admin/payments/plan/",
                    },
                    {
                        "title": "Abonnements",
                        "icon": "card_membership",
                        "link": "/admin/payments/subscription/",
                    },
                    {
                        "title": "Transactions",
                        "icon": "receipt_long",
                        "link": "/admin/payments/transaction/",
                    },
                    {
                        "title": "Callbacks",
                        "icon": "sync_alt",
                        "link": "/admin/payments/paymentcallback/",
                    },
                ],
            },

            {
                "title": "Marketplace",
                "separator": True,
                "items": [
                    {
                        "title": "Commandes",
                        "icon": "shopping_cart",
                        "link": "/admin/ecommerce/order/",
                    },
                ],
            },

            {
                "title": "Kharandi École",
                "separator": True,
                "items": [
                    {
                        "title": "Écoles",
                        "icon": "school",
                        "link": "/admin/ecole/school/",
                    },
                    {
                        "title": "Enseignants",
                        "icon": "co_present",
                        "link": "/admin/ecole/schoolteacher/",
                    },
                    {
                        "title": "Élèves",
                        "icon": "groups",
                        "link": "/admin/ecole/schoolstudent/",
                    },
                    {
                        "title": "Classes",
                        "icon": "class",
                        "link": "/admin/ecole/schoolclass/",
                    },
                    {
                        "title": "Notes",
                        "icon": "grading",
                        "link": "/admin/ecole/schoolgrade/",
                    },
                    {
                        "title": "Paiements",
                        "icon": "payments",
                        "link": "/admin/ecole/schoolpayment/",
                    },
                    {
                        "title": "Absences",
                        "icon": "event_busy",
                        "link": "/admin/ecole/schoolabsence/",
                    },
                ],
            },

            {
                "title": "Contenu",
                "separator": True,
                "items": [
                    {
                        "title": "Actualités",
                        "icon": "newspaper",
                        "link": "/admin/content/news/",
                    },
                    {
                        "title": "Bourses",
                        "icon": "school",
                        "link": "/admin/content/scholarship/",
                    },
                    {
                        "title": "Classements",
                        "icon": "leaderboard",
                        "link": "/admin/content/schoolranking/",
                    },
                    {
                        "title": "Étudier à l'étranger",
                        "icon": "flight",
                        "link": "/admin/content/studyabroad/",
                    },
                    {
                        "title": "Annonces répétiteurs",
                        "icon": "campaign",
                        "link": "/admin/content/tutorad/",
                    },
                    {
                        "title": "Notifications",
                        "icon": "notifications",
                        "link": "/admin/content/notification/",
                    },
                ],
            },

            {
                "title": "Support",
                "separator": True,
                "items": [
                    {
                        "title": "Tickets",
                        "icon": "support_agent",
                        "link": "/admin/support/ticket/",
                    },
                ],
            },
        ],
    },
}
