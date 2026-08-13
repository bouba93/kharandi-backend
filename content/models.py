import uuid
from django.db import models

class News(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=255)
    excerpt     = models.TextField(blank=True)
    content     = models.TextField(blank=True)
    category    = models.CharField(max_length=100, blank=True)
    color       = models.CharField(max_length=100, blank=True, default="bg-primary/10 text-primary")
    date        = models.CharField(max_length=50, blank=True)
    is_published= models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return self.title

class SchoolRanking(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rank     = models.PositiveIntegerField()
    name     = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    school_type = models.CharField(max_length=100, blank=True)
    score    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    year     = models.PositiveIntegerField(default=2024)
    class Meta: ordering = ["rank"]
    def __str__(self): return f"#{self.rank} {self.name}"

class StudyAbroad(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    university   = models.CharField(max_length=255)
    program_name = models.CharField(max_length=255)
    country      = models.CharField(max_length=100)
    city         = models.CharField(max_length=100, blank=True)
    level        = models.CharField(max_length=50, blank=True)
    link         = models.URLField(blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["country", "university"]
    def __str__(self): return f"{self.university} — {self.program_name}"

class Scholarship(models.Model):
    """Bourses d'etudes (coopération bilatérale, organismes, universités).
    Consommé par GET /api/v1/content/scholarships/ (frontend Kharandi)."""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    university   = models.CharField(max_length=255)
    program_name = models.CharField(max_length=255)
    excerpt      = models.TextField(blank=True)
    country      = models.CharField(max_length=100, blank=True)
    city         = models.CharField(max_length=100, blank=True)
    level        = models.CharField(max_length=100, blank=True)
    link         = models.URLField(blank=True)
    deadline     = models.CharField(max_length=50, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["country", "university"]
        verbose_name = "Bourse d'étude"
        verbose_name_plural = "Bourses d'études"

    def __str__(self): return f"{self.university} — {self.program_name}"


class TutorAd(models.Model):
    class AdType(models.TextChoices):
        OFFER   = "offer",   "Offre de cours"
        REQUEST = "request", "Demande de répétiteur"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="tutor_ads")
    ad_type     = models.CharField(max_length=10, choices=AdType.choices, default=AdType.OFFER)
    subject     = models.CharField(max_length=100)
    level       = models.CharField(max_length=50, blank=True)
    location    = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    phone       = models.CharField(max_length=20, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    is_boosted  = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-is_boosted", "-created_at"]
    def __str__(self): return f"{self.ad_type} — {self.subject}"

class Notification(models.Model):
    class NType(models.TextChoices):
        INFO    = "info",    "Information"
        SUCCESS = "success", "Succès"
        WARNING = "warning", "Avertissement"
        PROMO   = "promo",   "Promotion"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notifs")
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    notif_type = models.CharField(max_length=10, choices=NType.choices, default=NType.INFO)
    link       = models.CharField(max_length=255, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return f"[{self.notif_type}] {self.title} → {self.user.phone}"

class ReadingProgress(models.Model):
    user        = models.ForeignKey("users.User", on_delete=models.CASCADE)
    document_id = models.CharField(max_length=100, db_index=True)
    progress    = models.PositiveIntegerField(default=0)
    is_read     = models.BooleanField(default=False)
    updated_at  = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [("user", "document_id")]
    def __str__(self): return f"{self.user.phone} — doc:{self.document_id} {self.progress}%"
