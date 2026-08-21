from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView, LoginVerifyView, OTPSendView, OTPVerifyView,
    MeView, AvatarUploadView, UserListView, UserDetailView,
    PointsAddView, DeviceResetView, DeviceListView, WalletView,
    # Nouvelles vues
    RegisterEleveView, RegisterParentView,
    RegisterRepetiteurView, RegisterVendeurView,
    RegisterOTPSendView,
    LoginWithPasswordView,
    PasswordResetRequestView, PasswordResetConfirmView,
    RegisterView, MyPointsView,
)
from .kyc_views import TutorKYCView
from .google_views import (
    GoogleCallbackView, GoogleCompleteView, GoogleExchangeView,
    GoogleLinkView, GoogleLoginStartView,
)

urlpatterns = [
    # ── Connexion ─────────────────────────────────────────────────────────────
    path("login/",                   LoginView.as_view(),               name="login"),
    path("login/verify/",            LoginVerifyView.as_view(),          name="login-verify"),
    path("login/password/",          LoginWithPasswordView.as_view(),    name="login-password"),

    # ── Connexion Google (pilotée exclusivement par Django) ───────────────────
    # Aucun endpoint existant n'est modifié : ces cinq routes sont additives.
    path("google/login/",            GoogleLoginStartView.as_view(),     name="google-login"),
    path("google/callback/",         GoogleCallbackView.as_view(),       name="google-callback"),
    path("google/exchange/",         GoogleExchangeView.as_view(),       name="google-exchange"),
    path("google/complete/",         GoogleCompleteView.as_view(),       name="google-complete"),
    path("google/link/",             GoogleLinkView.as_view(),           name="google-link"),

    # ── Inscription OTP (commun) ───────────────────────────────────────────────
    path("register/otp/send/",       RegisterOTPSendView.as_view(),      name="register-otp-send"),

    # ── Inscription générique (frontend Kharandi) ─────────────────────────────
    path("register/",                RegisterView.as_view(),             name="register"),

    # ── Inscription par rôle ───────────────────────────────────────────────────
    path("register/eleve/",          RegisterEleveView.as_view(),        name="register-eleve"),
    path("register/parent/",         RegisterParentView.as_view(),       name="register-parent"),
    path("register/repetiteur/",     RegisterRepetiteurView.as_view(),   name="register-repetiteur"),
    path("register/vendeur/",        RegisterVendeurView.as_view(),      name="register-vendeur"),

    # ── Mot de passe oublié ────────────────────────────────────────────────────
    path("password/reset/request/",  PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password/reset/confirm/",  PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    # ── OTP legacy ────────────────────────────────────────────────────────────
    path("otp/send/",                OTPSendView.as_view(),              name="otp-send"),
    path("otp/verify/",              OTPVerifyView.as_view(),            name="otp-verify"),
    path("token/refresh/",           TokenRefreshView.as_view(),         name="token-refresh"),

    # ── Profil ────────────────────────────────────────────────────────────────
    path("me/",                      MeView.as_view(),                   name="auth-me"),
    path("avatar/",                  AvatarUploadView.as_view(),         name="auth-avatar"),
    path("me/points/",               PointsAddView.as_view(),            name="points-add"),
    path("wallet/",                  WalletView.as_view(),               name="wallet"),

    # ── KYC répétiteur (dépôt + suivi de MON dossier) ─────────────────────────
    path("kyc/tutor/",               TutorKYCView.as_view(),             name="tutor-kyc"),

    # ── Appareils ─────────────────────────────────────────────────────────────
    path("devices/",                 DeviceListView.as_view(),           name="device-list"),
    path("devices/reset/",           DeviceResetView.as_view(),          name="device-reset"),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path("users/",                   UserListView.as_view(),             name="user-list"),
    path("users/<uuid:user_id>/",    UserDetailView.as_view(),           name="user-detail"),
]
