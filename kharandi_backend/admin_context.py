from django.contrib.auth import get_user_model
from django.db.models import Sum

from learning.models import Document
from payments.models import Transaction, Subscription
from ecommerce.models import Order
from support.models import Ticket
from ecole.models import School, SchoolStudent, SchoolTeacher


User = get_user_model()


def admin_dashboard(request):
    if not request.path.startswith("/admin/"):
        return {}

    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    revenue = (
        Transaction.objects
        # `Transaction.Status.SUCCESS` vaut "SUCCESS" (majuscules) : le filtre
        # "success" ne correspondait à aucune ligne et le chiffre d'affaires
        # affiché dans l'admin restait donc toujours à 0.
        .filter(status=Transaction.Status.SUCCESS)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    recent_users = User.objects.order_by("-date_joined")[:5]

    recent_orders = (
        Order.objects
        .select_related("user")
        .order_by("-created_at")[:5]
    )

    recent_transactions = (
        Transaction.objects
        .select_related("user")
        .order_by("-created_at")[:5]
    )

    open_tickets = (
        Ticket.objects
        .filter(status__in=["open", "pending"])
        .order_by("-created_at")[:5]
    )

    return {
        "kharandi_dashboard": {
            "users": User.objects.count(),
            "documents": Document.objects.count(),
            "orders": Order.objects.count(),
            "subscriptions": Subscription.objects.count(),
            "tickets": Ticket.objects.count(),
            "transactions": Transaction.objects.count(),
            "revenue": revenue,

            "schools": School.objects.count(),
            "students": SchoolStudent.objects.count(),
            "teachers": SchoolTeacher.objects.count(),

            "recent_users": recent_users,
            "recent_orders": recent_orders,
            "recent_transactions": recent_transactions,
            "open_tickets": open_tickets,
        }
    }
