from django.contrib.auth import get_user_model
from django.db.models import Sum

from learning.models import Document
from payments.models import Transaction, Subscription
from ecommerce.models import Order
from support.models import Ticket

User = get_user_model()


def dashboard_stats():
    return {
        "users": User.objects.count(),
        "documents": Document.objects.count(),
        "orders": Order.objects.count(),
        "subscriptions": Subscription.objects.count(),
        "tickets": Ticket.objects.count(),
        "transactions": Transaction.objects.count(),
        "revenue": Transaction.objects.filter(
            status="success"
        ).aggregate(total=Sum("amount"))["total"] or 0,
    }
