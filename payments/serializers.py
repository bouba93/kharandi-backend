from rest_framework import serializers
from .models import Plan, Subscription, Transaction

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Plan
        fields = ["id", "name", "period", "price", "currency", "features", "is_active"]
        read_only_fields = ["id"]

class SubscriptionSerializer(serializers.ModelSerializer):
    plan      = PlanSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    class Meta:
        model  = Subscription
        fields = ["id", "plan", "status", "is_active", "start_date", "end_date"]
    def get_is_active(self, obj): return obj.is_active()

class TransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    class Meta:
        model  = Transaction
        fields = [
            "id", "reference", "gateway_ref", "amount",
            "currency", "provider", "status",
            "user_phone", "created_at",
        ]

class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
