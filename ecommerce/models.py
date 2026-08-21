import uuid
from django.db import models

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING="PENDING","En attente"; PAID="PAID","Payée"; CANCELLED="CANCELLED","Annulée"
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="orders")
    status     = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total      = models.DecimalField(max_digits=12, decimal_places=2)
    currency   = models.CharField(max_length=5, default="GNF")
    note       = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]

class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    document   = models.ForeignKey("learning.Document", on_delete=models.SET_NULL, null=True, blank=True)
    # Produit / service du catalogue payments.Plan (ex. « Kharandi Abacus »).
    # Permet de savoir de façon fiable CE QUI a été acheté sans dépendre du
    # libellé texte `name` : c'est cette clé qui sert à vérifier les droits
    # d'accès. Nullable : les lignes existantes (documents) ne sont pas touchées.
    plan       = models.ForeignKey("payments.Plan", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="order_items")
    name       = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity   = models.PositiveSmallIntegerField(default=1)
    @property
    def subtotal(self): return self.unit_price * self.quantity
