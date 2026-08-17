"""Diagnostic Karamo — affiche la configuration RÉELLEMENT chargée.

Usage :
    docker compose exec api python manage.py karamo_doctor

Sert à trancher la question « le conteneur exécute-t-il bien le code attendu ? »
sans ouvrir un shell Python : la commande imprime les valeurs effectives, leur
origine (variable d'environnement ou valeur par défaut du code) et l'empreinte
SHA-256 des fichiers source chargés.
"""
import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import NoReverseMatch, reverse

FICHIERS_SUIVIS = [
    "ai_features/serializers.py",
    "ai_features/views.py",
    "core/middleware.py",
    "core/redis_utils.py",
    "core/utils.py",
    "kharandi_backend/settings.py",
]

ROUTES_SUIVIES = ["ai-ask", "ai-ask-stream", "ai-status"]


class Command(BaseCommand):
    help = "Affiche la configuration Karamo effective (quota, rate limit, routes)."

    def _ligne(self, cle, valeur, origine=""):
        suffixe = f"   [{origine}]" if origine else ""
        self.stdout.write(f"  {cle:<30} {valeur}{suffixe}")

    @staticmethod
    def _origine(nom_env):
        if os.environ.get(nom_env) is not None:
            return "variable d'environnement"
        return "valeur par défaut du code"

    def handle(self, *args, **options):
        from core.redis_utils import limite_gratuite_karamo

        self.stdout.write("\n== Quota et limitation de débit ==")
        self._ligne(
            "KARAMO_FREE_DAILY_LIMIT",
            limite_gratuite_karamo(),
            self._origine("KARAMO_FREE_DAILY_LIMIT"),
        )
        for nom in ("RATE_LIMIT_PER_MIN", "RATE_LIMIT_AI_MIN", "RATE_LIMIT_ENABLED"):
            self._ligne(nom, getattr(settings, nom, "?"), self._origine(nom))

        self.stdout.write("\n== Routes Karamo ==")
        for nom in ROUTES_SUIVIES:
            try:
                self._ligne(nom, reverse(nom))
            except NoReverseMatch:
                self._ligne(nom, "INTROUVABLE")

        self.stdout.write("\n== Environnement ==")
        self._ligne("DEBUG", settings.DEBUG)
        self._ligne("ALLOWED_HOSTS", ", ".join(settings.ALLOWED_HOSTS))
        self._ligne(
            "OPENROUTER_API_KEY",
            "définie" if getattr(settings, "OPENROUTER_API_KEY", "").strip() else "ABSENTE",
        )
        self._ligne(
            "TAVILY_API_KEY",
            "définie" if getattr(settings, "TAVILY_API_KEY", "").strip() else "absente",
        )
        self._ligne(
            "ErreursJsonMiddleware",
            "actif" if "core.middleware.ErreursJsonMiddleware" in settings.MIDDLEWARE else "INACTIF",
        )

        self.stdout.write("\n== Empreinte des fichiers chargés ==")
        self.stdout.write(
            "  (comparez ces empreintes avec celles de votre dépôt local :\n"
            "   une différence prouve que l'image Docker est périmée)\n"
        )
        racine = Path(settings.BASE_DIR)
        for relatif in FICHIERS_SUIVIS:
            chemin = racine / relatif
            if not chemin.exists():
                self._ligne(relatif, "FICHIER ABSENT")
                continue
            empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()[:16]
            self._ligne(relatif, empreinte)

        self.stdout.write(
            self.style.SUCCESS("\nDiagnostic Karamo terminé.\n")
        )
