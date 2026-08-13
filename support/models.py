import uuid
from django.db import models

class Ticket(models.Model):
    class Status(models.TextChoices):
        OUVERT="OUVERT","Ouvert"; EN_COURS="EN_COURS","En cours"
        RESOLU="RESOLU","Résolu"; FERME="FERME","Fermé"
    class Category(models.TextChoices):
        PAIEMENT="PAIEMENT","Paiement"; TECHNIQUE="TECHNIQUE","Technique"
        CONTENU="CONTENU","Contenu"; ABONNEMENT="ABONNEMENT","Abonnement"; AUTRE="AUTRE","Autre"
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="tickets")
    title       = models.CharField(max_length=255)
    description = models.TextField()
    category    = models.CharField(max_length=15, choices=Category.choices, default=Category.AUTRE)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.OUVERT)
    priority    = models.PositiveSmallIntegerField(default=2)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["-created_at"]

class TicketReply(models.Model):
    ticket     = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author     = models.ForeignKey("users.User", on_delete=models.CASCADE)
    message    = models.TextField()
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["created_at"]
