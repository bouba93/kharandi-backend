"""
learning/signals.py — Mise à jour du vecteur de recherche lors de la sauvegarde
"""
from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document


@receiver(post_save, sender=Document)
def update_search_vector(sender, instance, **kwargs):
    """Met à jour le SearchVector PostgreSQL après chaque sauvegarde d'un Document."""
    Document.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector("title", weight="A", config="french") +
            SearchVector("description", weight="B", config="french")
        )
    )
