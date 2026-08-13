from rest_framework import serializers
from .models import Order, OrderItem

class CartItemSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    quantity    = serializers.IntegerField(min_value=1, default=1)

class OrderCreateSerializer(serializers.Serializer):
    items    = CartItemSerializer(many=True)
    currency = serializers.CharField(max_length=5, default="GNF")
    note     = serializers.CharField(required=False, allow_blank=True)

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    class Meta:
        model  = OrderItem
        fields = ["id","name","unit_price","quantity","subtotal"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model  = Order
        fields = ["id","status","total","currency","note","items","created_at"]
