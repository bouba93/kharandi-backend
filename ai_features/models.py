from django.db import models


class GuineaKnowledgeEntry(models.Model):
    class Category(models.TextChoices):
        GEOGRAPHY = "GEOGRAPHY", "Géographie"
        HISTORY = "HISTORY", "Histoire"
        CULTURE = "CULTURE", "Cultures et langues"
        EDUCATION = "EDUCATION", "Éducation"
        ECONOMY = "ECONOMY", "Économie"
        ENVIRONMENT = "ENVIRONMENT", "Environnement"
        INSTITUTIONS = "INSTITUTIONS", "Institutions"

    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    keywords = models.JSONField(default=list, blank=True)
    source_title = models.CharField(max_length=255)
    source_url = models.URLField(max_length=500)
    source_published_on = models.DateField(null=True, blank=True)
    verified_on = models.DateField()
    priority = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "title"]
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["priority"]),
        ]
        verbose_name = "Connaissance sur la Guinée"
        verbose_name_plural = "Connaissances sur la Guinée"

    def __str__(self):
        return self.title
