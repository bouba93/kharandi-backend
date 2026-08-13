from django.core.management.base import BaseCommand

from ai_features.guinea_data import seed_guinea_knowledge


class Command(BaseCommand):
    help = "Crée ou actualise les fiches de connaissances guinéennes de Karamo."

    def handle(self, *args, **options):
        created, updated = seed_guinea_knowledge()
        self.stdout.write(
            self.style.SUCCESS(
                f"Connaissances Karamo : {created} créée(s), {updated} actualisée(s)."
            )
        )
