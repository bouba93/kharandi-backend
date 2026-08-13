from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Crée les données initiales (Plans + Matières)"

    def handle(self, *args, **kwargs):
        self._seed_plans()
        self._seed_subjects()
        self._seed_guinea_knowledge()
        self.stdout.write(self.style.SUCCESS("✅ Données initiales créées."))

    def _seed_plans(self):
        from payments.models import Plan
        plans = [
            {"name": "Gratuit",         "period": "GRATUIT", "price": 0,      "currency": "GNF", "features": ["Accès aux documents gratuits", "5 QCM par mois"]},
            {"name": "Premium Mensuel", "period": "MENSUEL",  "price": 25000,  "currency": "GNF", "features": ["Accès illimité", "QCM illimités", "IA Tutor", "PDF"]},
            {"name": "Premium Annuel",  "period": "ANNUEL",   "price": 250000, "currency": "GNF", "features": ["Accès illimité", "QCM illimités", "IA Tutor", "PDF", "2 mois offerts"]},
            {"name": "Boutique Vendeur","period": "SEMESTRIEL","price": 50000, "currency": "GNF", "features": ["Boutique visible", "Vente produits scolaires", "Gestion stocks"]},
        ]
        for p in plans:
            obj, created = Plan.objects.get_or_create(name=p["name"], defaults=p)
            self.stdout.write(f"  Plan '{obj.name}' — {'créé' if created else 'existant'}")

    def _seed_subjects(self):
        from learning.models import Subject
        subjects = [
            {"name": "Mathématiques",   "icon": "calculator"},
            {"name": "Physique-Chimie", "icon": "flask"},
            {"name": "SVT",             "icon": "leaf"},
            {"name": "Français",        "icon": "book-open"},
            {"name": "Histoire-Géo",    "icon": "globe"},
            {"name": "Philosophie",     "icon": "lightbulb"},
            {"name": "Anglais",         "icon": "languages"},
            {"name": "Informatique",    "icon": "monitor"},
            {"name": "Économie",        "icon": "trending-up"},
            {"name": "Arabe",           "icon": "pen-line"},
        ]
        for s in subjects:
            obj, created = Subject.objects.get_or_create(name=s["name"], defaults=s)
            self.stdout.write(f"  Matière '{obj.name}' — {'créée' if created else 'existante'}")

    def _seed_guinea_knowledge(self):
        from ai_features.guinea_data import seed_guinea_knowledge

        created, updated = seed_guinea_knowledge()
        self.stdout.write(
            f"  Karamo Guinée — {created} fiche(s) créée(s), {updated} actualisée(s)"
        )
