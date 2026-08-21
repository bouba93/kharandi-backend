"""
Crée les plans d'abonnement attendus par le frontend.

Pourquoi cette commande existe
──────────────────────────────
La table `payments_plan` est vide sur une base neuve : aucune migration ni
aucun script ne l'alimente. Or `SubscriptionInitiateView` résout le plan par
UUID ou par alias (« mensuel », « annuel », « seller », « gratuit ») et renvoie
un 404 « Plan introuvable » si la ligne n'existe pas. Sans amorçage, aucun
abonnement n'est possible en production.

Sécurité des données
────────────────────
STRICTEMENT NON DESTRUCTIVE :
  - `get_or_create` sur le nom : un plan déjà présent n'est jamais recréé ;
  - les tarifs d'un plan existant ne sont modifiés que si `--maj-tarifs` est
    passé explicitement — sans cette option, un plan existant est laissé
    intact, y compris son prix ;
  - aucune suppression, aucun `delete()`, aucun plan désactivé.

Un abonnement (`Subscription`) référence son plan avec `on_delete=PROTECT` :
supprimer un plan utilisé est de toute façon impossible.

Usage
─────
    python manage.py seed_plans                # crée ce qui manque
    python manage.py seed_plans --simulation   # affiche sans rien écrire
    python manage.py seed_plans --maj-tarifs   # aligne aussi les prix existants
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from payments.models import Plan

# Les noms doivent correspondre exactement à la table `name_map` de
# payments/views.py::_get_plan, sinon les alias du frontend ne résolvent rien.
PLANS = [
    {
        "name": "Gratuit",
        "slug": "gratuit",
        "period": Plan.Period.GRATUIT,
        "price": Decimal("0"),
        "features": [
            "Accès aux documents publics",
            "3 questions à Karamo par jour",
        ],
    },
    {
        "name": "Premium Mensuel",
        "slug": "premium-mensuel",
        "period": Plan.Period.MENSUEL,
        "price": Decimal("25000"),
        "features": [
            "Karamo illimité",
            "Génération de QCM",
            "Tous les documents",
            "Bulletins PDF",
        ],
    },
    {
        "name": "Premium Annuel",
        "slug": "premium-annuel",
        "period": Plan.Period.ANNUEL,
        "price": Decimal("250000"),
        "features": [
            "Tous les avantages du Premium Mensuel",
            "Deux mois offerts",
        ],
    },
    {
        "name": "Boutique Vendeur",
        "slug": "boutique-vendeur",
        "period": Plan.Period.MENSUEL,
        "price": Decimal("50000"),
        "features": [
            "Publication de produits sur la place de marché",
            "Suivi des commandes",
            "Codes promotionnels",
        ],
    },
    # ── Produit à paiement unique ────────────────────────────────────────────
    # Kharandi Abacus : service payé UNE fois, 45 000 GNF. Période PONCTUEL →
    # il ne passe pas par Subscription (voir payments/views.py::
    # ProductOrderInitiateView) et ne peut donc jamais activer Premium.
    {
        "name": "Kharandi Abacus",
        "slug": "kharandi-abacus",
        "period": Plan.Period.PONCTUEL,
        "price": Decimal("45000"),
        "features": [
            "Programme de calcul mental Kharandi Abacus",
            "Accès à vie après paiement unique",
        ],
    },
]


class Command(BaseCommand):
    help = "Crée les plans d'abonnement manquants (aucune suppression)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--simulation",
            action="store_true",
            help="Affiche ce qui serait fait sans écrire en base.",
        )
        parser.add_argument(
            "--maj-tarifs",
            action="store_true",
            help="Aligne aussi le prix, la période et les avantages des plans "
                 "déjà présents. Sans cette option, ils ne sont pas touchés.",
        )
        parser.add_argument(
            "--devise",
            default="GNF",
            help="Devise à appliquer aux plans créés (défaut : GNF).",
        )

    def handle(self, *args, **options):
        simulation = options["simulation"]
        maj_tarifs = options["maj_tarifs"]
        devise = options["devise"]

        crees, inchanges, mis_a_jour = [], [], []

        with transaction.atomic():
            for modele in PLANS:
                existant = Plan.objects.filter(name__iexact=modele["name"]).first()

                if existant is None:
                    if not simulation:
                        Plan.objects.create(
                            name=modele["name"],
                            slug=modele.get("slug") or None,
                            period=modele["period"],
                            price=modele["price"],
                            currency=devise,
                            features=modele["features"],
                            is_active=True,
                        )
                    crees.append(modele["name"])
                    continue

                # Le slug est un identifiant technique manquant sur les lignes
                # créées avant son introduction : on le renseigne s'il est vide,
                # sans jamais écraser un slug déjà défini, et même sans
                # --maj-tarifs (ce n'est ni un prix ni une donnée commerciale).
                if modele.get("slug") and not existant.slug:
                    if not simulation:
                        existant.slug = modele["slug"]
                        existant.save(update_fields=["slug"])
                    mis_a_jour.append(f"{existant.name} (slug)")

                if not maj_tarifs:
                    inchanges.append(
                        f"{existant.name} ({existant.price} {existant.currency}, "
                        f"actif={existant.is_active})"
                    )
                    continue

                champs = []
                if existant.price != modele["price"]:
                    existant.price = modele["price"]
                    champs.append("price")
                if existant.period != modele["period"]:
                    existant.period = modele["period"]
                    champs.append("period")
                if existant.features != modele["features"]:
                    existant.features = modele["features"]
                    champs.append("features")
                if not existant.is_active:
                    existant.is_active = True
                    champs.append("is_active")

                if champs:
                    if not simulation:
                        existant.save(update_fields=champs)
                    mis_a_jour.append(f"{existant.name} ({', '.join(champs)})")
                else:
                    inchanges.append(existant.name)

            if simulation:
                transaction.set_rollback(True)

        prefixe = "[SIMULATION] " if simulation else ""
        for nom in crees:
            self.stdout.write(self.style.SUCCESS(f"{prefixe}créé      : {nom}"))
        for nom in mis_a_jour:
            self.stdout.write(self.style.WARNING(f"{prefixe}mis à jour : {nom}"))
        for nom in inchanges:
            self.stdout.write(f"{prefixe}inchangé  : {nom}")

        self.stdout.write("")
        self.stdout.write(
            f"{prefixe}{len(crees)} créé(s), {len(mis_a_jour)} mis à jour, "
            f"{len(inchanges)} inchangé(s). Total en base : "
            f"{Plan.objects.count() if not simulation else 'inchangé'}"
        )
        if not maj_tarifs and inchanges:
            self.stdout.write(
                "Les plans existants n'ont pas été modifiés. Utilisez "
                "--maj-tarifs pour aligner leurs tarifs."
            )
