from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.utils import success_response, error_response
from learning.models import Document
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer

class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        s = OrderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data  = s.validated_data
        items = data["items"]
        if not items: return error_response("Le panier est vide.")
        document_ids = [item["document_id"] for item in items]
        documents = {d.id: d for d in Document.objects.filter(id__in=document_ids)}
        if len(documents) != len(set(document_ids)):
            return error_response("Un ou plusieurs documents sont introuvables.", status=404)

        total = sum(documents[i["document_id"]].price * i["quantity"] for i in items)
        if total <= 0:
            return error_response("Les documents gratuits ne nécessitent pas de commande.", status=400)
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user, total=total,
                currency=data.get("currency", "GNF"), note=data.get("note", "")
            )
            for item in items:
                doc = documents[item["document_id"]]
                OrderItem.objects.create(
                    order=order, document=doc, name=doc.title,
                    unit_price=doc.price, quantity=item["quantity"]
                )
        return success_response(data=OrderSerializer(order).data, message="Commande créée.", status=201)

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(data=OrderSerializer(
            Order.objects.filter(user=request.user).prefetch_related("items"), many=True).data)
