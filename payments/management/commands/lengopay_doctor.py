"""
Diagnostic complet de l'intégration LengoPay.

    docker compose exec api python manage.py lengopay_doctor
    docker compose exec api python manage.py lengopay_doctor --pay-id <PAY_ID>
    docker compose exec api python manage.py lengopay_doctor --reconcile

Vérifie, dans l'ordre :
  1. la configuration (identifiants, URLs, jeton de callback) ;
  2. la joignabilité de l'endpoint de vérification de statut ;
  3. le journal des callbacks reçus et les transactions en attente ;
  4. facultativement, le statut réel d'un pay_id précis.

Aucune donnée n'est supprimée. Sans --reconcile, la commande est en lecture
seule.
"""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnostique l'intégration LengoPay (configuration, callbacks, statuts)."

    def add_arguments(self, parser):
        parser.add_argument("--pay-id", dest="pay_id", default="",
                            help="Vérifie le statut réel d'un pay_id auprès de LengoPay.")
        parser.add_argument("--reference", dest="reference", default="",
                            help="Vérifie une transaction par sa référence KHR-…")
        parser.add_argument("--reconcile", action="store_true",
                            help="Lance la réconciliation des paiements en attente.")
        parser.add_argument("--hours", type=int, default=48,
                            help="Fenêtre d'analyse en heures (défaut : 48).")

    # ── Sections ─────────────────────────────────────────────────────────────
    def _section(self, titre):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"── {titre} " + "─" * max(0, 60 - len(titre))))

    def _ok(self, texte):
        self.stdout.write(self.style.SUCCESS(f"  OK    {texte}"))

    def _ko(self, texte):
        self.stdout.write(self.style.ERROR(f"  ERREUR {texte}"))

    def _warn(self, texte):
        self.stdout.write(self.style.WARNING(f"  ALERTE {texte}"))

    def _info(self, texte):
        self.stdout.write(f"        {texte}")

    # ── Exécution ────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        from ..._doctor_helpers import (
            verifier_configuration,
            verifier_endpoint_statut,
            verifier_planificateur,
            verifier_securite,
            resumer_callbacks,
            resumer_transactions,
        )

        self._section("1. Configuration")
        for niveau, message in verifier_configuration():
            getattr(self, f"_{niveau}")(message)

        self._section("2. Sécurité et configuration de production")
        for niveau, message in verifier_securite():
            getattr(self, f"_{niveau}")(message)

        self._section("3. Celery Beat (planificateur)")
        for niveau, message in verifier_planificateur():
            getattr(self, f"_{niveau}")(message)

        self._section("4. Endpoint de vérification de statut")
        for niveau, message in verifier_endpoint_statut():
            getattr(self, f"_{niveau}")(message)

        self._section("5. Journal des callbacks reçus")
        for niveau, message in resumer_callbacks(options["hours"]):
            getattr(self, f"_{niveau}")(message)

        self._section("6. Transactions")
        for niveau, message in resumer_transactions(options["hours"]):
            getattr(self, f"_{niveau}")(message)

        pay_id = options["pay_id"].strip()
        reference = options["reference"].strip()
        if reference and not pay_id:
            from ...models import Transaction
            tx = Transaction.objects.filter(reference=reference).first()
            if not tx:
                self._ko(f"Aucune transaction avec la référence {reference}.")
            elif not tx.gateway_ref:
                self._ko(f"{reference} n'a pas de gateway_ref (paiement jamais créé chez LengoPay).")
            else:
                pay_id = tx.gateway_ref

        if pay_id:
            self._section(f"7. Statut réel de {pay_id}")
            from ...lengopay import transaction_status
            from ...models import Transaction

            etat, montant = transaction_status(pay_id)
            if etat is None:
                self._ko("LengoPay n'a pas renvoyé de statut exploitable "
                         "(voir les journaux du conteneur api).")
            else:
                self._ok(f"Statut LengoPay : {etat} — montant : {montant}")
            tx = Transaction.objects.filter(gateway_ref=pay_id).first()
            if tx:
                self._info(f"Transaction locale : {tx.reference} — statut {tx.status} — "
                           f"montant {tx.amount} {tx.currency}")
                if etat and etat != "PENDING" and tx.status == "PENDING":
                    self._warn("Écart détecté : lancer --reconcile pour appliquer le statut réel.")
            else:
                self._warn("Aucune transaction locale avec ce gateway_ref.")

        if options["reconcile"]:
            self._section("8. Réconciliation")
            from ...cron import reconcile_pending_payments
            resultat = reconcile_pending_payments(max_age_hours=options["hours"])
            self._ok(f"Résultat : {resultat}")

        self.stdout.write("")
        self.stdout.write("Rappel : l'URL de callback enregistrée chez LengoPay doit être")
        self.stdout.write(f"  {settings.LENGOPAY_CALLBACK_URL}")
        self.stdout.write("")
