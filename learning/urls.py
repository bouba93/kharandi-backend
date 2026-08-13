from django.urls import path
from .views import DocumentListCreateView, DocumentDetailView, SubjectListView, DocumentUploadView

urlpatterns = [
    path("documents/",           DocumentListCreateView.as_view(), name="document-list"),
    path("documents/upload/",    DocumentUploadView.as_view(),     name="document-upload"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(),     name="document-detail"),
    path("subjects/",            SubjectListView.as_view(),         name="subject-list"),
]
