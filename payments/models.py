import uuid
from django.db import models
from django.utils import timezone

class Plan(models.Model):
    class Period(models.TextChoices):
        MENSUEL    = "MENSUEL",    "Mensuel"
        ANNUEL     = "ANNUEL",     "Annuel"
        GRATUIT    = "GRATUIT",    "Gratuit"
        SEMESTRIEL = "SEMESTRIEL", "Semestriel"

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name     = models.CharField(max_length=100)
    period   = models.CharField(max_length=12, choices=Period.choices)
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default="GNF")
    features = models.JSONField(default=list)
    is_active= models.BooleanField(default=True)
    def __str__(self): return f"{self.name} — {self.price} {self.currency}"

class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = "ACTIVE",    "Actif"
        EXPIRED   = "EXPIRED",   "Expiré"
        PENDING   = "PENDING",   "En attente"
        CANCELLED = "CANCELLED", "Annulé"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="subscription")
    plan       = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True)
    status     = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date   = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        if self.status != self.Status.ACTIVE: return False
        if not self.plan or self.plan.period == Plan.Period.GRATUIT: return False
        if self.end_date and timezone.now() > self.end_date: return False
        return True

class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING  = "PENDING",  "En attente"
        SUCCESS  = "SUCCESS",  "Réussie"
        FAILED   = "FAILED",   "Échouée"
        REFUNDED = "REFUNDED", "Remboursée"
    class Provider(models.TextChoices):
        LENGOPAY = "LENGOPAY", "LengoPay"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="transactions")
    subscription    = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    order           = models.ForeignKey("ecommerce.Order", on_delete=models.SET_NULL, null=True, blank=True)
    reference       = models.CharField(max_length=100, unique=True, db_index=True)
    gateway_ref     = models.CharField(max_length=200, blank=True)
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    currency        = models.CharField(max_length=5, default="GNF")
    provider        = models.CharField(max_length=15, choices=Provider.choices, default=Provider.LENGOPAY)
    status          = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    phone           = models.CharField(max_length=20, blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway_ref"], name="tx_gateway_ref_idx"),
            models.Index(fields=["status", "created_at"], name="tx_status_created_idx"),
        ]
    def __str__(self): return f"TX:{self.reference} [{self.status}]"


class PaymentCallback(models.Model):
    """
    Journal brut de CHAQUE notification LengoPay reçue.

    Sans cette trace, un « souci de callback » est indiagnosticable : on ne sait
    pas si LengoPay a appelé, ce qu'il a envoyé, ni pourquoi la transaction n'a
    pas été appliquée. Sert aussi de file de rattrapage : un callback arrivé
    avant l'enregistrement du `gateway_ref` (course possible sur les paiements
    Mobile Money instantanés) est conservé puis rejoué par le cron.
    """

    class Outcome(models.TextChoices):
        APPLIED     = "APPLIED",     "Appliqué"
        DUPLICATE   = "DUPLICATE",   "Doublon (déjà traité)"
        PENDING     = "PENDING",     "Statut encore en attente"
        ORPHAN      = "ORPHAN",      "Transaction introuvable"
        UNVERIFIED  = "UNVERIFIED",  "Non authentifié"
        MISMATCH    = "MISMATCH",    "Montant ou statut incohérent"
        INVALID     = "INVALID",     "Charge utile invalide"
        ERROR       = "ERROR",       "Erreur interne"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pay_id      = models.CharField(max_length=200, blank=True, db_index=True)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="callbacks",
    )
    announced_status = models.CharField(max_length=32, blank=True)
    applied_status   = models.CharField(max_length=32, blank=True)
    outcome     = models.CharField(max_length=12, choices=Outcome.choices, db_index=True)
    auth_method = models.CharField(max_length=24, blank=True)
    source_ip   = models.CharField(max_length=64, blank=True)
    payload     = models.JSONField(null=True, blank=True)
    detail      = models.TextField(blank=True)
    replayed    = models.BooleanField(default=False, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Callback LengoPay"
        verbose_name_plural = "Callbacks LengoPay"

    def __str__(self):
        return f"CB:{self.pay_id or '?'} [{self.outcome}]"
