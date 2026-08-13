from django.urls import path
from .views import OrderCreateView, OrderListView
urlpatterns = [
    path("orders/",        OrderListView.as_view(),  name="order-list"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),
]
