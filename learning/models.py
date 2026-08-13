import uuid
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    class Meta: verbose_name = "Matière"
    def __str__(self): return self.name

class Document(models.Model):
    class DocType(models.TextChoices):
        LIVRE      = "LIVRE",      "Livre"
        COURS      = "COURS",      "Cours"
        EXERCICE   = "EXERCICE",   "Exercice"
        CORRECTION = "CORRECTION", "Correction"
        VIDEO      = "VIDEO",      "Vidéo"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title           = models.CharField(max_length=255, db_index=True)
    description     = models.TextField(blank=True)
    doc_type        = models.CharField(max_length=15, choices=DocType.choices, default=DocType.COURS)
    subject         = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    level           = models.CharField(max_length=10, blank=True)
    file            = models.FileField(upload_to="documents/", blank=True, null=True)
    external_url    = models.URLField(blank=True)
    thumbnail       = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    is_free         = models.BooleanField(default=False)
    downloads       = models.PositiveIntegerField(default=0)
    # ✅ Contenu texte du cours (rédigé directement dans l'admin)
    content         = models.TextField(blank=True,
                        help_text="Contenu texte du cours (si pas de fichier PDF/vidéo)")
    # ✅ Nouveaux champs
    price           = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                        help_text="Prix du document en GNF (0 = gratuit)")
    has_certification = models.BooleanField(default=False,
                        help_text="Le document délivre-t-il une certification ?")
    search_vector   = SearchVectorField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [GinIndex(fields=["search_vector"])]
    def __str__(self): return self.title


class QCM(models.Model):
    class Difficulty(models.TextChoices):
        FACILE   = "FACILE",   "Facile"
        MOYEN    = "MOYEN",    "Moyen"
        DIFFICILE= "DIFFICILE","Difficile"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="qcms")
    subject    = models.CharField(max_length=100)
    level      = models.CharField(max_length=10)
    topic      = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MOYEN)
    questions  = models.JSONField(default=list)
    score      = models.FloatField(null=True, blank=True)
    completed  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ["-created_at"]
    def __str__(self): return f"QCM {self.subject}/{self.topic}"
