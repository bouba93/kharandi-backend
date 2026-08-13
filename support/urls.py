from django.urls import path
from .views import TicketListCreateView, TicketDetailView
urlpatterns = [
    path("tickets/",           TicketListCreateView.as_view(), name="ticket-list"),
    path("tickets/<uuid:pk>/", TicketDetailView.as_view(),     name="ticket-detail"),
]
