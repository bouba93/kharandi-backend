from django.urls import path
from .views import GradeListView, StudentListView
urlpatterns = [
    path("",         GradeListView.as_view(),  name="grade-list"),
    path("students/",StudentListView.as_view(), name="grade-students"),
]
