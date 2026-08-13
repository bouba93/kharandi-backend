from django.urls import path
from .views import (
    NewsListView, NewsDetailView,
    SchoolRankingListView, SchoolRankingDetailView,
    StudyAbroadListView, StudyAbroadDetailView,
    ScholarshipListView, ScholarshipDetailView,
    TutorAdListView, TutorAdDetailView,
    NotificationListView, NotificationMarkReadView,
    ReadingProgressView,
)

urlpatterns = [
    # ── Actualités ────────────────────────────────────────────────────────────
    path("news/",                          NewsListView.as_view(),            name="news-list"),
    path("news/<uuid:pk>/",                NewsDetailView.as_view(),          name="news-detail"),

    # ── Palmarès des écoles ───────────────────────────────────────────────────
    path("school-rankings/",               SchoolRankingListView.as_view(),   name="rankings-list"),
    path("school-rankings/<uuid:pk>/",     SchoolRankingDetailView.as_view(), name="rankings-detail"),

    # ── Étudier à l'étranger ──────────────────────────────────────────────────
    path("study-abroad/",                  StudyAbroadListView.as_view(),     name="study-list"),
    path("study-abroad/<uuid:pk>/",        StudyAbroadDetailView.as_view(),   name="study-detail"),

    # ── Bourses d'études ──────────────────────────────────────────────────────
    path("scholarships/",                  ScholarshipListView.as_view(),     name="scholarship-list"),
    path("scholarships/<uuid:pk>/",        ScholarshipDetailView.as_view(),   name="scholarship-detail"),

    # ── Répétiteurs ───────────────────────────────────────────────────────────
    path("tutor-ads/",                     TutorAdListView.as_view(),         name="tutor-list"),
    path("tutor-ads/<uuid:pk>/",           TutorAdDetailView.as_view(),       name="tutor-detail"),

    # ── Notifications ─────────────────────────────────────────────────────────
    path("notifications/",                 NotificationListView.as_view(),    name="notif-list"),
    path("notifications/read/",            NotificationMarkReadView.as_view(), name="notif-read-all"),
    path("notifications/<uuid:pk>/read/",  NotificationMarkReadView.as_view(), name="notif-read-one"),

    # ── Progression de lecture ────────────────────────────────────────────────
    path("reading-progress/<str:document_id>/", ReadingProgressView.as_view(), name="reading-progress"),
]
