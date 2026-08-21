from django.urls import path
from .views import (
    PlanListView, PlanDetailView,
    SubscriptionStatusView, SubscriptionInitiateView,
    PaymentInitiateView, PaymentWebhookView, CallbackLogView,
    TransactionListView, RunCronView,
    ProductOrderInitiateView, EntitlementListView,
)

urlpatterns = [
    path("plans/",                    PlanListView.as_view(),             name="plan-list"),
    path("plans/<uuid:pk>/",          PlanDetailView.as_view(),           name="plan-detail"),
    path("initiate/",                 PaymentInitiateView.as_view(),      name="payment-initiate"),

    # ── Produits à paiement unique (Kharandi Abacus…) ────────────────────────
    # Le montant vient toujours de payments_plan.price : le frontend envoie un
    # identifiant de produit, jamais un prix.
    path("products/initiate/",        ProductOrderInitiateView.as_view(), name="product-initiate"),
    path("entitlements/",             EntitlementListView.as_view(),      name="entitlement-list"),

    # ── Callback LengoPay ────────────────────────────────────────────────────
    # LengoPay ne signant pas ses notifications, l'URL porte un jeton secret
    # (LENGOPAY_CALLBACK_TOKEN) qui authentifie l'émetteur.
    #
    # Les variantes SANS slash final sont indispensables : sur un POST, Django
    # ne peut pas appliquer APPEND_SLASH sans provoquer une redirection 301 qui
    # ferait perdre le corps de la requête, donc la notification de paiement.
    path("webhook/",                  PaymentWebhookView.as_view(),       name="payment-webhook"),
    path("webhook",                   PaymentWebhookView.as_view(),       name="payment-webhook-noslash"),
    path("webhook/<str:token>/",      PaymentWebhookView.as_view(),       name="payment-webhook-token"),
    path("webhook/<str:token>",       PaymentWebhookView.as_view(),       name="payment-webhook-token-noslash"),

    # Journal des callbacks reçus — réservé aux administrateurs (diagnostic).
    path("callbacks/",                CallbackLogView.as_view(),          name="payment-callbacks"),

    path("transactions/",             TransactionListView.as_view(),      name="transaction-list"),
    path("subscriptions/status/",     SubscriptionStatusView.as_view(),   name="subscription-status"),
    path("subscriptions/initiate/",   SubscriptionInitiateView.as_view(), name="subscription-initiate"),
    path("run-cron/",                 RunCronView.as_view(),              name="run-cron"),
]
