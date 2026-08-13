"""
payments/admin.py — Journal des callbacks LengoPay
──────────────────────────────────────────────────
Plan, Subscription et Transaction sont déjà enregistrés dans core/admin.py :
on ne les redéclare pas ici (Django lèverait AlreadyRegistered).

Le journal des callbacks est volontairement en LECTURE SEULE : c'est une pièce
de diagnostic et de preuve, elle ne doit pas être modifiable depuis l'admin.
"""
from django.contrib import admin

from .models import PaymentCallback


@admin.register(PaymentCallback)
class PaymentCallbackAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "pay_id", "outcome", "announced_status",
        "applied_status", "auth_method", "source_ip", "replayed",
    )
    list_filter = ("outcome", "replayed", "auth_method")
    search_fields = ("pay_id", "detail", "source_ip")
    date_hierarchy = "created_at"
    raw_id_fields = ("transaction",)

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
