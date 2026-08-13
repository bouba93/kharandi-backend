from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import serializers
from django.db import transaction
from core.utils import success_response, error_response
from .models import Product, PromoCode, Order


class ProductSerializer(serializers.ModelSerializer):
    seller_name = serializers.SerializerMethodField()
    class Meta:
        model  = Product
        fields = ["id","title","description","price","stock","category",
                  "image_url","status","variants","is_boosted","seller_name","created_at"]
        read_only_fields = ["id","seller_name","created_at"]
    def get_seller_name(self, obj):
        p = getattr(obj.seller, "profile", None)
        return f"{p.first_name} {p.last_name}".strip() if p else obj.seller.phone

class PromoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PromoCode
        fields = ["id","code","discount","is_active"]
        read_only_fields = ["id"]

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Order
        fields = ["id","product","product_title","price","status","created_at"]
        read_only_fields = ["id","product_title","created_at"]


# ─── Products ────────────────────────────────────────────────────────────────
class ProductListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Product.objects.filter(status="active").select_related("seller__profile")
        if q := request.query_params.get("q"):
            qs = qs.filter(title__icontains=q)
        if cat := request.query_params.get("category"):
            qs = qs.filter(category=cat)
        return success_response(data=ProductSerializer(qs, many=True).data)
    def post(self, request):
        s = ProductSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(seller=request.user)
        return success_response(data=s.data, status=201, message="Produit ajouté.")

class SellerProductListView(APIView):
    """Produits du vendeur connecté."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(
            data=ProductSerializer(
                Product.objects.filter(seller=request.user).select_related("seller__profile"),
                many=True).data)

class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk, user):
        try: return Product.objects.get(id=pk, seller=user)
        except Product.DoesNotExist: return None
    def patch(self, request, pk):
        p = self._get(pk, request.user)
        if not p: return error_response("Produit introuvable.", status=404)
        s = ProductSerializer(p, data=request.data, partial=True)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data)
    def delete(self, request, pk):
        p = self._get(pk, request.user)
        if not p: return error_response("Produit introuvable.", status=404)
        p.status = "inactive"; p.save(update_fields=["status"])
        return success_response(message="Produit désactivé.")


# ─── Promo Codes ─────────────────────────────────────────────────────────────
class PromoCodeListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(
            data=PromoSerializer(PromoCode.objects.filter(seller=request.user), many=True).data)
    def post(self, request):
        s = PromoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(seller=request.user)
        return success_response(data=s.data, status=201)

class PromoCodeCheckView(APIView):
    """POST /marketplace/promos/check/ { code: "KHARANDI10" }"""
    permission_classes = [IsAuthenticated]
    def post(self, request):
        code = request.data.get("code", "").upper().strip()
        if not code: return error_response("Code vide.", status=400)
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
            return success_response(
                data={"id": str(promo.id), "code": promo.code, "discount": promo.discount,
                      "seller_id": str(promo.seller_id)},
                message=f"Code valide — {promo.discount}% de réduction.")
        except PromoCode.DoesNotExist:
            return error_response("Code promo invalide ou expiré.", status=404)


# ─── Orders ──────────────────────────────────────────────────────────────────
class MarketplaceOrderView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        product_id = request.data.get("product_id")
        try:
            product = Product.objects.get(id=product_id, status="active")
        except Product.DoesNotExist:
            return error_response("Produit introuvable.", status=404)
        order = Order.objects.create(
            buyer=request.user, product=product,
            product_title=product.title, price=product.price)
        return success_response(
            data=OrderSerializer(order).data,
            message="Commande créée.", status=201)

class SellerOrderListView(APIView):
    """Commandes reçues par le vendeur."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        orders = Order.objects.filter(product__seller=request.user).select_related("buyer")
        data = [{
            "id": str(o.id), "product_title": o.product_title,
            "price": float(o.price), "status": o.status,
            "buyer_phone": o.buyer.phone,
            "created_at": o.created_at.isoformat(),
        } for o in orders]
        return success_response(data=data)
    def patch(self, request, pk):
        try:
            order = Order.objects.get(id=pk, product__seller=request.user)
        except Order.DoesNotExist:
            return error_response("Commande introuvable.", status=404)
        new_status = request.data.get("status")
        if new_status: order.status = new_status; order.save(update_fields=["status"])
        return success_response(message="Statut mis à jour.")


# ─── POST /marketplace/orders/redeem/ ────────────────────────────────────────
from rest_framework.views import APIView as _APIView
from rest_framework.permissions import IsAuthenticated as _IsAuthenticated
from core.utils import success_response as _ok, error_response as _err
import logging as _logging
_logger = _logging.getLogger(__name__)

class RedeemWithPointsView(_APIView):
    """
    Échanger des points contre un produit marketplace.

    Body : { product_id: UUID, quantity: int (défaut 1) }

    Règle : coût en points = ceil(prix_produit / 100)
    Exemple : produit à 5000 GNF = 50 points
    """
    permission_classes = [_IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id", "")
        quantity   = int(request.data.get("quantity", 1))

        if not product_id:
            return _err("product_id requis.", status=400)
        if quantity < 1:
            return _err("La quantité doit être ≥ 1.", status=400)

        import math
        from users.models import PointTransaction, Profile
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    id=product_id, status="active"
                )
                profile, _ = Profile.objects.select_for_update().get_or_create(
                    user=request.user
                )
                unit_cost_pts = math.ceil(float(product.price) / 100)
                total_pts = unit_cost_pts * quantity

                if product.stock < quantity:
                    return _err(
                        f"Stock insuffisant. Disponible : {product.stock}", status=400
                    )
                if (profile.points or 0) < total_pts:
                    return _err(
                        f"Points insuffisants. Requis : {total_pts} pts — Solde : {profile.points or 0} pts",
                        status=400, code="insufficient_points",
                    )

                profile.points -= total_pts
                profile.save(update_fields=["points"])
                order = Order.objects.create(
                    buyer=request.user, product=product,
                    product_title=product.title, price=0,
                    status=Order.Status.PENDING,
                )
                product.stock -= quantity
                product.save(update_fields=["stock"])
                PointTransaction.objects.create(
                    user=request.user, type=PointTransaction.Type.DEBIT,
                    source=PointTransaction.Source.MARKETPLACE,
                    points=total_pts, balance_after=profile.points,
                    description=f"Achat : {product.title} × {quantity}",
                    reference=str(order.id),
                )
        except Product.DoesNotExist:
            return _err("Produit introuvable ou indisponible.", status=404)

        _logger.info(
            "Échange points — user=%s produit=%s pts=%d solde=%d",
            request.user.phone, product.title, total_pts, profile.points
        )

        return _ok(
            data={
                "order_id":      str(order.id),
                "product":       product.title,
                "points_spent":  total_pts,
                "points_balance": profile.points,
                "points_in_gnf": profile.points * 100,
            },
            message=f"Échange réussi ! -{total_pts} points pour {product.title}.",
            status=201,
        )
