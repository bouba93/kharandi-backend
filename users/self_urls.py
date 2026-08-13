"""
users/self_urls.py
──────────────────
Espace de noms « /api/v1/users/ » attendu par le frontend Kharandi.

Le frontend appelle POST /api/v1/users/me/points/ (Exercises.tsx, Marketplace.tsx)
pour créditer/débiter le portefeuille de points de l'utilisateur connecté.
"""
from django.urls import path
from .views import MyPointsView, MeView, AvatarUploadView, WalletView

urlpatterns = [
    path("me/points/", MyPointsView.as_view(),      name="users-me-points"),
    path("me/",        MeView.as_view(),            name="users-me"),
    path("me/avatar/", AvatarUploadView.as_view(),  name="users-me-avatar"),
    path("me/wallet/", WalletView.as_view(),        name="users-me-wallet"),
]
