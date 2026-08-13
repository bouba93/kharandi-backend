from django.urls import path
from .views import (
    # Existant
    ActivateSchoolView, SchoolLoginView, TeacherLoginView,
    ParentLookupView, StudentListView, StudentDetailView,
    GradeView, PaymentView, AbsenceView,
    TeacherListView, ClassListView,
    SchoolListView, SchoolDetailView,
    # Nouveaux
    SubscriptionPricingView, SubscriptionCheckoutView, SubscriptionStatusView,
    BadgeIssueView, BadgeHistoryView, BadgeDetailView,
    ParentStudentBadgesView, ParentBadgePDFView,
)

urlpatterns = [
    # ── Écoles ───────────────────────────────────────────────────────────────
    path("schools/",                          SchoolListView.as_view()),
    path("schools/<str:school_id>/",          SchoolDetailView.as_view()),
    path("schools/<str:school_id>/students/", StudentListView.as_view()),

    # ── Auth école ────────────────────────────────────────────────────────────
    path("activate/",                         ActivateSchoolView.as_view()),
    path("login/",                            SchoolLoginView.as_view()),
    path("teacher/login/",                    TeacherLoginView.as_view()),

    # ── Abonnements ───────────────────────────────────────────────────────────
    path("subscriptions/pricing/",            SubscriptionPricingView.as_view()),
    path("subscriptions/checkout-session/",   SubscriptionCheckoutView.as_view()),
    path("subscriptions/status/<str:school_id>/", SubscriptionStatusView.as_view()),

    # ── Badges ────────────────────────────────────────────────────────────────
    path("schools/badges/issue/",             BadgeIssueView.as_view()),
    path("schools/badges/history/<str:school_id>/", BadgeHistoryView.as_view()),
    path("schools/badges/<str:badge_id>/",    BadgeDetailView.as_view()),

    # ── Parents ───────────────────────────────────────────────────────────────
    path("parent/<str:matricule>/",           ParentLookupView.as_view()),
    path("parents/students/<str:student_id>/badges/",
         ParentStudentBadgesView.as_view()),
    path("parents/students/<str:student_id>/badges/<str:badge_id>/pdf/",
         ParentBadgePDFView.as_view()),

    # ── Élèves ────────────────────────────────────────────────────────────────
    path("students/<str:student_id>/",        StudentDetailView.as_view()),

    # ── Notes, paiements, absences ────────────────────────────────────────────
    path("grades/",                           GradeView.as_view()),
    path("payments/",                         PaymentView.as_view()),
    path("payments/<str:payment_id>/",        PaymentView.as_view()),
    path("absences/",                         AbsenceView.as_view()),

    # ── Enseignants & Classes ─────────────────────────────────────────────────
    path("teachers/",                         TeacherListView.as_view()),
    path("teachers/<str:teacher_id>/",        TeacherListView.as_view()),
    path("classes/",                          ClassListView.as_view()),
]
