from django.urls import path
from .views import (ProductListView, SellerProductListView, ProductDetailView,
                    PromoCodeListView, PromoCodeCheckView,
                    MarketplaceOrderView, SellerOrderListView,
                    RedeemWithPointsView)
urlpatterns = [
    path("products/",                ProductListView.as_view(),      name="product-list"),
    path("products/mine/",           SellerProductListView.as_view(), name="product-mine"),
    path("products/<uuid:pk>/",      ProductDetailView.as_view(),    name="product-detail"),
    path("promos/",                  PromoCodeListView.as_view(),    name="promo-list"),
    path("promos/check/",            PromoCodeCheckView.as_view(),   name="promo-check"),
    path("orders/",                  MarketplaceOrderView.as_view(), name="market-order"),
    path("orders/redeem/",           RedeemWithPointsView.as_view(), name="market-redeem"),
    path("seller/orders/",           SellerOrderListView.as_view(),  name="seller-orders"),
    path("seller/orders/<uuid:pk>/", SellerOrderListView.as_view(),  name="seller-order-detail"),
]
