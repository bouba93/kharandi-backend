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
            {
                "name": "Gratuit",
                "period": "GRATUIT",
                "price": 0,
                "currency": "GNF",
                "features": [
                    "Accès aux documents gratuits",
                    "5 QCM par mois",
                ],
            },
            {
                "name": "Élève / Étudiant",
                "period": "ANNUEL",
                "price": 45000,
                "currency": "GNF",
                "features": [
                    "Accès illimité aux contenus",
                    "QCM illimités",
                    "IA Tutor",
                    "PDF",
                ],
            },
            {
                "name": "Palmarès National des Écoles",
                "period": "ANNUEL",
                "price": 250000,
                "currency": "GNF",
                "features": [
                    "Accès au Palmarès National des Écoles",
                    "Consultation des établissements",
                    "Informations détaillées",
                ],
            },
            {
                "name": "Forfait Standard Répétiteur",
                "period": "SEMESTRIEL",
                "price": 50000,
                "currency": "GNF",
                "features": [
                    "Profil répétiteur",
                    "Visibilité auprès des élèves",
                    "Gestion des cours",
                ],
            },
            {
                "name": "Forfait Standard Boutique",
                "period": "SEMESTRIEL",
                "price": 50000,
                "currency": "GNF",
                "features": [
                    "Boutique visible",
                    "Vente de produits scolaires",
                    "Gestion des stocks",
                ],
            },
        ]

        for plan_data in plans:
            obj, created = Plan.objects.update_or_create(
                name=plan_data["name"],
                defaults={
                    "period": plan_data["period"],
                    "price": plan_data["price"],
                    "currency": plan_data["currency"],
                    "features": plan_data["features"],
                    "is_active": True,
                },
            )

            self.stdout.write(
                f"  Plan '{obj.name}' — "
                f"{'créé' if created else 'mis à jour'}"
            )

        # Les anciens plans restent en base pour préserver
        # les références historiques, mais ne sont plus commercialisés.
        Plan.objects.filter(
            name__in=[
                "Premium Mensuel",
                "Premium Annuel",
                "Boutique Vendeur",
            ]
        ).update(is_active=False)

        self.stdout.write(
            self.style.WARNING(
                "  Anciens plans Premium/Boutique Vendeur désactivés."
            )
        )

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
