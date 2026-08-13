import uuid
from django.db import models

class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE   = "active",   "Actif"
        INACTIVE = "inactive", "Inactif"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller      = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="products")
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=12, decimal_places=2)
    stock       = models.PositiveIntegerField(default=10)
    category    = models.CharField(max_length=100, blank=True)
    image_url   = models.URLField(blank=True)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    variants    = models.JSONField(default=list, blank=True)
    is_boosted  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-is_boosted", "-created_at"]
    def __str__(self): return self.title

class PromoCode(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller    = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="promos")
    code      = models.CharField(max_length=20, unique=True)
    discount  = models.PositiveIntegerField(default=10, help_text="Pourcentage de réduction")
    is_active = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.code} (-{self.discount}%)"

class Order(models.Model):
    """Commandes marketplace (produits vendeur)."""
    class Status(models.TextChoices):
        PENDING   = "pending",   "En attente"
        COMPLETED = "completed", "Terminée"
        SHIPPED   = "shipped",   "Expédiée"
        DELIVERED = "delivered", "Livrée"
        CANCELLED = "cancelled", "Annulée"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer         = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="marketplace_orders")
    product       = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_title = models.CharField(max_length=255)
    price         = models.DecimalField(max_digits=12, decimal_places=2)
    status        = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    promo_code    = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return f"Order {self.product_title} — {self.buyer.phone}"
