"""
payments/tests.py — Tests de non-régression du callback LengoPay
───────────────────────────────────────────────────────────────
Ces tests reproduisent exactement la charge utile décrite dans la documentation
officielle LengoPay et couvrent les cas qui, en production, laissaient les
transactions bloquées en « PENDING ».

Exécution :
    docker compose exec api python manage.py test payments -v 2
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PaymentCallback, Plan, Subscription, Transaction

JETON = "jeton-de-test-tres-long-0123456789abcdef"
PAY_ID = "cGF5X2lkX2RlX3Rlc3Q="

# Charge utile telle que documentée par LengoPay (noter le « Client » majuscule).
CHARGE_SUCCES = {
    "pay_id": PAY_ID,
    "status": "SUCCESS",
    "amount": 50000,
    "message": "Transaction Successful",
    "Client": "624897845",
}

User = get_user_model()


def _api_muette(*args, **kwargs):
    """Simule une API de statut injoignable."""
    import requests
    raise requests.RequestException("API indisponible (simulation)")


class _Reponse:
    """Réponse HTTP minimale pour simuler l'API de statut."""

    def __init__(self, code, donnees):
        self.status_code = code
        self._donnees = donnees
        self.text = str(donnees)

    def json(self):
        return self._donnees


@override_settings(
    LENGOPAY_CALLBACK_TOKEN=JETON,
    LENGOPAY_REQUIRE_STATUS_CONFIRMATION=False,
    LENGOPAY_AMOUNT_TOLERANCE="1",
    RATE_LIMIT_ENABLED=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CallbackLengoPayTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(phone="620000001")
        self.plan = Plan.objects.create(
            name="Premium Mensuel", period=Plan.Period.MENSUEL,
            price=Decimal("50000.00"), currency="GNF",
        )
        self.sub = Subscription.objects.create(
            user=self.user, plan=self.plan, status=Subscription.Status.PENDING,
        )
        self.tx = Transaction.objects.create(
            user=self.user, subscription=self.sub, reference="KHR-TEST00000001",
            amount=Decimal("50000.00"), currency="GNF", gateway_ref=PAY_ID,
        )

    def _url(self, token=JETON, slash=True):
        base = "/api/v1/payments/webhook/"
        if token:
            base += token
            if slash:
                base += "/"
        elif not slash:
            base = base.rstrip("/")
        return base

    def _poster(self, charge=None, token=JETON, slash=True):
        return self.client.post(
            self._url(token, slash),
            data=charge if charge is not None else CHARGE_SUCCES,
            content_type="application/json",
        )

    # ── Cas nominal : c'est LE scénario qui échouait ──────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_callback_avec_jeton_active_labonnement_meme_si_api_muette(self, _):
        reponse = self._poster()

        self.assertEqual(reponse.status_code, 200)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertIsNotNone(self.sub.end_date)

        journal = PaymentCallback.objects.get(pay_id=PAY_ID)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.APPLIED)
        self.assertEqual(journal.auth_method, "url_token")

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_le_numero_du_payeur_est_enregistre(self, _):
        self._poster()
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.phone, "624897845")

    # ── Routage ──────────────────────────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_url_sans_slash_final_fonctionne_sans_redirection(self, _):
        reponse = self._poster(slash=False)
        self.assertEqual(reponse.status_code, 200)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)

    def test_get_sur_lurl_de_callback_repond_200(self):
        """Permet de tester la joignabilité depuis l'extérieur."""
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    # ── Sécurité ─────────────────────────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_callback_sans_jeton_ne_active_rien(self, _):
        reponse = self._poster(token="")

        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.json()["verified"])
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertEqual(self.sub.status, Subscription.Status.PENDING)
        self.assertEqual(
            PaymentCallback.objects.get(pay_id=PAY_ID).outcome,
            PaymentCallback.Outcome.UNVERIFIED,
        )

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_jeton_errone_ne_active_rien(self, _):
        self._poster(token="mauvais-jeton")
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_montant_incoherent_refuse_lactivation(self, _):
        charge = {**CHARGE_SUCCES, "amount": 100}
        self._poster(charge)

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertEqual(self.sub.status, Subscription.Status.PENDING)
        self.assertEqual(
            PaymentCallback.objects.get(pay_id=PAY_ID).outcome,
            PaymentCallback.Outcome.MISMATCH,
        )

    # ── L'API de statut fait foi quand elle répond ────────────────────────────
    def test_statut_de_lapi_prime_sur_le_statut_annonce(self):
        reponse_api = _Reponse(200, {
            "status": "FAILED", "pay_id": PAY_ID,
            "date": "2026-08-12 10:00:00", "amount": 50000,
        })
        with patch("payments.lengopay.requests.post", return_value=reponse_api):
            self._poster()  # annonce SUCCESS, l'API dit FAILED

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.FAILED)
        self.assertEqual(self.sub.status, Subscription.Status.PENDING)

    def test_api_confirme_sans_jeton_active_labonnement(self):
        """Rétrocompatibilité : l'ancienne URL sans jeton reste exploitable."""
        reponse_api = _Reponse(200, {
            "status": "SUCCESS", "pay_id": PAY_ID,
            "date": "2026-08-12 10:00:00", "amount": 50000,
        })
        with patch("payments.lengopay.requests.post", return_value=reponse_api):
            self._poster(token="")

        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)

    def test_statut_pending_ne_modifie_pas_la_transaction(self):
        reponse_api = _Reponse(200, {
            "status": "PENDING", "pay_id": PAY_ID,
            "date": "2026-08-12 10:00:00", "amount": 50000,
        })
        with patch("payments.lengopay.requests.post", return_value=reponse_api):
            reponse = self._poster()

        self.assertTrue(reponse.json()["pending"])
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)

    # ── Idempotence ──────────────────────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_callback_rejoue_est_idempotent(self, _):
        self._poster()
        self.sub.refresh_from_db()
        premiere_fin = self.sub.end_date

        self._poster()
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.end_date, premiere_fin)
        self.assertEqual(
            PaymentCallback.objects.filter(
                outcome=PaymentCallback.Outcome.DUPLICATE
            ).count(),
            1,
        )
        self.assertEqual(Transaction.objects.filter(status="SUCCESS").count(), 1)

    # ── Charges utiles dégradées ─────────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_pay_id_manquant_renvoie_400(self, _):
        reponse = self._poster({"status": "SUCCESS", "amount": 50000})
        self.assertEqual(reponse.status_code, 400)

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_statut_en_minuscules_est_accepte(self, _):
        self._poster({**CHARGE_SUCCES, "status": "success"})
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_montant_en_chaine_est_accepte(self, _):
        self._poster({**CHARGE_SUCCES, "amount": "50000"})
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)

    # ── Callback orphelin puis rejeu ──────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_callback_orphelin_est_conserve_puis_rejoue(self, _):
        self.tx.gateway_ref = ""
        self.tx.save(update_fields=["gateway_ref"])

        self._poster()
        journal = PaymentCallback.objects.get(pay_id=PAY_ID)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.ORPHAN)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)

        # L'initiation enregistre enfin le gateway_ref → rejeu.
        self.tx.gateway_ref = PAY_ID
        self.tx.save(update_fields=["gateway_ref"])

        from .cron import replay_orphan_callbacks
        resultat = replay_orphan_callbacks()

        self.assertEqual(resultat["applied"], 1)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)

    # ── Réconciliation ───────────────────────────────────────────────────────
    def test_reconciliation_rattrape_un_paiement_dont_le_callback_est_perdu(self):
        from datetime import timedelta

        from django.utils import timezone

        from .cron import reconcile_pending_payments

        Transaction.objects.filter(pk=self.tx.pk).update(
            created_at=timezone.now() - timedelta(hours=1)
        )
        reponse_api = _Reponse(200, {
            "status": "SUCCESS", "pay_id": PAY_ID,
            "date": "2026-08-12 10:00:00", "amount": 50000,
        })
        with patch("payments.lengopay.requests.post", return_value=reponse_api):
            resultat = reconcile_pending_payments()

        self.assertEqual(resultat["confirmed"], 1)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)


class ClientLengoPayTests(TestCase):
    """Conformité du client HTTP à la documentation officielle."""

    def test_normalisation_des_statuts(self):
        from .lengopay import normalize_status

        for valeur in ("SUCCESS", "success", "Successful", "PAID", "completed"):
            self.assertEqual(normalize_status(valeur), "SUCCESS", valeur)
        for valeur in ("FAILED", "failure", "CANCELLED", "expired"):
            self.assertEqual(normalize_status(valeur), "FAILED", valeur)
        for valeur in ("PENDING", "INITIATED", "processing"):
            self.assertEqual(normalize_status(valeur), "PENDING", valeur)
        for valeur in ("", None, "PEUT-ETRE"):
            self.assertIsNone(normalize_status(valeur), valeur)

    def test_extraction_du_numero_du_payeur(self):
        from .lengopay import extract_phone

        self.assertEqual(extract_phone({"Client": "624897845"}), "624897845")
        self.assertEqual(extract_phone({"client": "624897845"}), "624897845")
        self.assertEqual(extract_phone({"account": "624897845"}), "624897845")
        self.assertEqual(extract_phone({}), "")

    def test_corps_de_la_requete_de_creation(self):
        """Le corps envoyé doit correspondre à la documentation."""
        from .lengopay import create_payment

        capture = {}

        def _faux_post(url, json=None, headers=None, timeout=None):
            capture["url"] = url
            capture["json"] = json
            capture["headers"] = headers
            return _Reponse(200, {
                "status": "Success", "pay_id": PAY_ID,
                "payment_url": f"https://payment.lengopay.com/{PAY_ID}",
            })

        with override_settings(
            LENGOPAY_SITE_ID="VXQsfatrR3pVaSc8",
            LENGOPAY_LICENSE_KEY="cle-de-test",
        ):
            with patch("payments.lengopay.requests.post", _faux_post):
                resultat = create_payment(Decimal("50000.00"), "GNF", "KHR-ABC")

        self.assertTrue(resultat["success"])
        self.assertEqual(resultat["pay_id"], PAY_ID)
        self.assertEqual(capture["json"]["websiteid"], "VXQsfatrR3pVaSc8")
        self.assertEqual(capture["json"]["amount"], 50000)
        self.assertIsInstance(capture["json"]["amount"], int)
        self.assertEqual(capture["json"]["currency"], "GNF")
        self.assertEqual(capture["json"]["country"], "GN")
        self.assertIn("callback_url", capture["json"])
        self.assertEqual(capture["headers"]["Authorization"], "Basic cle-de-test")

    def test_corps_de_la_requete_de_statut(self):
        """POST /transaction/status avec {pay_id, websiteid}, et non un GET."""
        from .lengopay import transaction_status

        capture = {}

        def _faux_post(url, json=None, headers=None, timeout=None):
            capture["url"] = url
            capture["json"] = json
            return _Reponse(200, {
                "status": "SUCCESS", "pay_id": PAY_ID,
                "date": "2026-08-12 10:00:00", "amount": 50000,
            })

        with override_settings(LENGOPAY_SITE_ID="VXQsfatrR3pVaSc8"):
            with patch("payments.lengopay.requests.post", _faux_post):
                etat, montant = transaction_status(PAY_ID)

        self.assertEqual(etat, "SUCCESS")
        self.assertEqual(montant, Decimal("50000"))
        self.assertTrue(capture["url"].endswith("/transaction/status"))
        self.assertEqual(capture["json"], {
            "pay_id": PAY_ID, "websiteid": "VXQsfatrR3pVaSc8",
        })

    def test_ancien_gabarit_de_statut_est_corrige_automatiquement(self):
        """La configuration héritée .../payments/{pay_id} ne doit plus être utilisée."""
        from .lengopay import transaction_status

        capture = {}

        def _faux_post(url, json=None, headers=None, timeout=None):
            capture["url"] = url
            return _Reponse(200, {"status": "SUCCESS", "pay_id": PAY_ID, "amount": 1})

        with override_settings(
            LENGOPAY_STATUS_URL="https://portal.lengopay.com/api/v1/payments/{pay_id}",
            LENGOPAY_BASE_URL="https://portal.lengopay.com/api/v1",
        ):
            with patch("payments.lengopay.requests.post", _faux_post):
                transaction_status(PAY_ID)

        self.assertEqual(
            capture["url"], "https://portal.lengopay.com/api/v1/transaction/status"
        )

    def test_url_de_callback_contient_le_jeton(self):
        from django.conf import settings

        if settings.LENGOPAY_CALLBACK_TOKEN:
            self.assertIn(settings.LENGOPAY_CALLBACK_TOKEN, settings.LENGOPAY_CALLBACK_URL)
        self.assertIn("/api/v1/payments/webhook/", settings.LENGOPAY_CALLBACK_URL)


# ══════════════════════════════════════════════════════════════════════════════
#  MODE STRICT — LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True
#  C'est la configuration de production. Un callback annonçant SUCCESS ne suffit
#  plus : LengoPay doit le confirmer par un appel serveur-à-serveur.
# ══════════════════════════════════════════════════════════════════════════════

@override_settings(
    LENGOPAY_CALLBACK_TOKEN=JETON,
    LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True,
    LENGOPAY_AMOUNT_TOLERANCE="1",
    RATE_LIMIT_ENABLED=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ModeStrictTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(phone="620000002")
        self.plan = Plan.objects.create(
            name="Premium Mensuel", period=Plan.Period.MENSUEL,
            price=Decimal("50000.00"), currency="GNF",
        )
        self.sub = Subscription.objects.create(
            user=self.user, plan=self.plan, status=Subscription.Status.PENDING,
        )
        self.tx = Transaction.objects.create(
            user=self.user, subscription=self.sub, reference="KHR-STRICT000001",
            amount=Decimal("50000.00"), currency="GNF", gateway_ref=PAY_ID,
        )

    def _poster(self, charge=None):
        return self.client.post(
            f"/api/v1/payments/webhook/{JETON}/",
            data=charge if charge is not None else CHARGE_SUCCES,
            content_type="application/json",
        )

    def _vieillir(self, heures=1):
        from datetime import timedelta
        from django.utils import timezone
        Transaction.objects.filter(pk=self.tx.pk).update(
            created_at=timezone.now() - timedelta(hours=heures)
        )

    @staticmethod
    def _reponse(statut, montant=50000):
        return _Reponse(200, {
            "status": statut, "pay_id": PAY_ID,
            "date": "2026-08-13 10:00:00", "amount": montant,
        })

    # ── Le cœur du mode strict ───────────────────────────────────────────────
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_callback_success_non_confirme_reste_en_attente(self, _):
        """
        API muette + mode strict : le callback est journalisé en UNVERIFIED et
        l'abonnement n'est PAS activé. Aucun accès n'est accordé sur la seule
        parole d'un callback non confirmé.
        """
        reponse = self._poster()
        self.assertEqual(reponse.status_code, 200)

        journal = PaymentCallback.objects.get(pay_id=PAY_ID)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.UNVERIFIED)

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertEqual(self.sub.status, Subscription.Status.PENDING)

    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_un_callback_non_confirme_est_rattrape_par_la_reconciliation(self, _):
        """
        Test le plus important du mode strict : rien n'est perdu.
        L'API redevient joignable → la réconciliation applique le paiement.
        """
        self._poster()
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)

        from .cron import reconcile_pending_payments
        self._vieillir()
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            resultat = reconcile_pending_payments()

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertGreaterEqual(
            resultat["confirmed"] + resultat["orphans_applied"], 1
        )

    def test_callback_confirme_par_lapi_active_labonnement(self):
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            self._poster()

        journal = PaymentCallback.objects.get(pay_id=PAY_ID)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.APPLIED)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertIsNotNone(self.sub.end_date)

    # ── FAILED ne crédite jamais rien ────────────────────────────────────────
    def test_callback_failed_ne_credite_rien(self):
        charge = dict(CHARGE_SUCCES, status="FAILED", message="Transaction Failed")
        with patch("payments.lengopay.requests.post", return_value=self._reponse("FAILED")):
            self._poster(charge)

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.FAILED)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertIsNone(self.sub.end_date)

    def _mettre_en_echec(self):
        with patch("payments.lengopay.requests.post", return_value=self._reponse("FAILED")):
            self._poster(dict(CHARGE_SUCCES, status="FAILED"))
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.FAILED)

    @override_settings(LENGOPAY_REQUIRE_STATUS_CONFIRMATION=False)
    @patch("payments.lengopay.requests.post", side_effect=_api_muette)
    def test_un_success_non_confirme_ne_peut_pas_rouvrir_un_echec(self, _):
        """
        Un échec est un état terminal. Quiconque connaîtrait le jeton pourrait
        sinon « ressusciter » un paiement refusé en renvoyant un faux SUCCESS.
        """
        with patch("payments.lengopay.requests.post", return_value=self._reponse("FAILED")):
            self._poster(dict(CHARGE_SUCCES, status="FAILED"))

        self._poster()  # API muette : le jeton seul ne suffit pas ici.

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.FAILED)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertTrue(
            PaymentCallback.objects.filter(
                pay_id=PAY_ID, outcome=PaymentCallback.Outcome.UNVERIFIED
            ).exists()
        )

    def test_seule_lapi_lengopay_peut_rouvrir_un_echec(self):
        """
        Cas inverse : si LengoPay confirme elle-même l'encaissement, refuser
        reviendrait à garder l'argent du client sans lui donner son abonnement.
        La transition est donc autorisée — et journalisée.
        """
        self._mettre_en_echec()

        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            self._poster()

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.sub.status, Subscription.Status.ACTIVE)

    # ── Idempotence : double callback ────────────────────────────────────────
    def test_double_callback_nactive_quune_seule_fois(self):
        """
        LengoPay peut renvoyer le même callback plusieurs fois (retentative).
        Un seul paiement validé, un seul abonnement, une seule date de fin.
        """
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            self._poster()
            self.sub.refresh_from_db()
            fin_initiale = self.sub.end_date

            self._poster()
            self._poster()

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.end_date, fin_initiale,
                         "L'abonnement a été prolongé une seconde fois.")
        self.assertEqual(
            Transaction.objects.filter(gateway_ref=PAY_ID,
                                       status=Transaction.Status.SUCCESS).count(), 1)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)

        doublons = PaymentCallback.objects.filter(
            pay_id=PAY_ID, outcome=PaymentCallback.Outcome.DUPLICATE).count()
        self.assertEqual(doublons, 2)
        self.assertEqual(
            PaymentCallback.objects.filter(
                pay_id=PAY_ID, outcome=PaymentCallback.Outcome.APPLIED).count(), 1)

    # ── Montant ──────────────────────────────────────────────────────────────
    def test_montant_inferieur_a_lattendu_est_refuse(self):
        """100 000 attendus, 10 000 annoncés → refus, aucune activation."""
        self.tx.amount = Decimal("100000.00")
        self.tx.save(update_fields=["amount"])

        charge = dict(CHARGE_SUCCES, amount=10000)
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS", 10000)):
            self._poster(charge)

        journal = PaymentCallback.objects.get(pay_id=PAY_ID)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.MISMATCH)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)

    def test_la_reconciliation_refuse_aussi_un_montant_incoherent(self):
        """
        Le contrôle de montant ne doit pas être contournable en laissant
        simplement le callback se perdre.
        """
        self.tx.amount = Decimal("100000.00")
        self.tx.save(update_fields=["amount"])
        self._vieillir()

        from .cron import reconcile_pending_payments
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS", 10000)):
            resultat = reconcile_pending_payments()

        self.assertEqual(resultat["refused"], 1)
        self.assertEqual(resultat["confirmed"], 0)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)

    # ── Faux pay_id ──────────────────────────────────────────────────────────
    def test_faux_pay_id_naffecte_aucune_transaction(self):
        """
        Un attaquant qui devine le jeton mais invente un pay_id ne doit rien
        pouvoir activer, même si l'API répond SUCCESS pour ce pay_id inconnu.
        """
        faux = "cGF5X2lkX2ludmVudGU="
        charge = dict(CHARGE_SUCCES, pay_id=faux)
        with patch("payments.lengopay.requests.post",
                   return_value=_Reponse(200, {"status": "SUCCESS", "pay_id": faux,
                                               "amount": 50000})):
            self._poster(charge)

        journal = PaymentCallback.objects.get(pay_id=faux)
        self.assertIsNone(journal.transaction)
        self.assertEqual(journal.outcome, PaymentCallback.Outcome.ORPHAN)

        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)
        self.assertEqual(
            Transaction.objects.filter(status=Transaction.Status.SUCCESS).count(), 0)

    def test_le_rejeu_dun_faux_pay_id_reste_sans_effet(self):
        faux = "cGF5X2lkX2ludmVudGU="
        with patch("payments.lengopay.requests.post",
                   return_value=_Reponse(200, {"status": "SUCCESS", "pay_id": faux,
                                               "amount": 50000})):
            self._poster(dict(CHARGE_SUCCES, pay_id=faux))

            from .cron import replay_orphan_callbacks
            resultat = replay_orphan_callbacks()

        self.assertEqual(resultat["applied"], 0)
        self.assertEqual(
            Transaction.objects.filter(status=Transaction.Status.SUCCESS).count(), 0)

    # ── PENDING ──────────────────────────────────────────────────────────────
    def test_pending_reste_en_attente_puis_devient_reconciliable(self):
        with patch("payments.lengopay.requests.post", return_value=self._reponse("PENDING")):
            self._poster(dict(CHARGE_SUCCES, status="PENDING"))

        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.PENDING)
        self.sub.refresh_from_db()
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)

        self._vieillir()
        from .cron import reconcile_pending_payments
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            resultat = reconcile_pending_payments()

        self.assertEqual(resultat["confirmed"], 1)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.SUCCESS)

    def test_la_reconciliation_marque_en_echec_un_paiement_failed(self):
        self._vieillir()
        from .cron import reconcile_pending_payments
        with patch("payments.lengopay.requests.post", return_value=self._reponse("FAILED")):
            resultat = reconcile_pending_payments()

        self.assertEqual(resultat["failed"], 1)
        self.tx.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.FAILED)
        self.assertNotEqual(self.sub.status, Subscription.Status.ACTIVE)

    def test_une_transaction_trop_recente_nest_pas_interrogee(self):
        """
        Marge de 2 minutes : inutile d'interroger LengoPay pendant que le client
        est encore sur la page de paiement.
        """
        from .cron import reconcile_pending_payments
        with patch("payments.lengopay.requests.post", side_effect=AssertionError(
                "L'API ne doit pas être appelée pour une transaction récente.")):
            resultat = reconcile_pending_payments()
        self.assertEqual(resultat["checked"], 0)

    # ── Idempotence de la réconciliation elle-même ───────────────────────────
    def test_deux_reconciliations_successives_nactivent_quune_fois(self):
        self._vieillir()
        from .cron import reconcile_pending_payments
        with patch("payments.lengopay.requests.post", return_value=self._reponse("SUCCESS")):
            reconcile_pending_payments()
            self.sub.refresh_from_db()
            fin = self.sub.end_date
            reconcile_pending_payments()

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.end_date, fin)


# ══════════════════════════════════════════════════════════════════════════════
#  CELERY BEAT — la planification doit être réellement exécutable
#  Une faute de frappe dans un nom de tâche ne provoquerait aucune erreur au
#  démarrage : Beat émettrait dans le vide et la réconciliation ne tournerait
#  jamais. Ces tests rendent cette panne silencieuse impossible.
# ══════════════════════════════════════════════════════════════════════════════

class PlanificationBeatTests(TestCase):

    def setUp(self):
        from kharandi_backend.celery import app
        self.app = app
        self.app.loader.import_default_modules()

    def test_toutes_les_taches_planifiees_existent(self):
        from django.conf import settings

        enregistrees = set(self.app.tasks.keys())
        for nom, conf in settings.CELERY_BEAT_SCHEDULE.items():
            self.assertIn(
                conf["task"], enregistrees,
                f"L'entrée « {nom} » planifie « {conf['task']} », qui n'est "
                "enregistrée nulle part : Beat émettrait dans le vide.",
            )

    def test_la_reconciliation_des_paiements_est_planifiee(self):
        from django.conf import settings

        taches = {c["task"] for c in settings.CELERY_BEAT_SCHEDULE.values()}
        self.assertIn("payments.reconcile_lengopay", taches)
        self.assertIn("payments.replay_orphan_callbacks", taches)
        self.assertIn("payments.expire_subscriptions", taches)
        self.assertIn("core.cleanup_expired_otps", taches)

    def test_la_reconciliation_est_assez_frequente(self):
        """Au-delà de 10 minutes, un client payant attendrait trop longtemps."""
        from django.conf import settings

        entree = settings.CELERY_BEAT_SCHEDULE["reconciliation-lengopay"]
        self.assertLessEqual(entree["schedule"], 600)

    def test_le_mode_strict_impose_une_reconciliation_planifiee(self):
        """
        Contrôle système kharandi.E018 : le mode strict sans réconciliation
        bloquerait définitivement les paiements en cas de panne de l'API.
        """
        from django.core.checks import Error
        from core.checks import verifier_configuration_production

        with override_settings(
            DEBUG=False,
            LENGOPAY_REQUIRE_STATUS_CONFIRMATION=True,
            CELERY_BEAT_SCHEDULE={},
        ):
            problemes = verifier_configuration_production(None)

        ids = [p.id for p in problemes if isinstance(p, Error)]
        self.assertIn("kharandi.E018", ids)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class VerrouTachesTests(TestCase):
    """Deux exécutions simultanées d'une tâche ne doivent pas se superposer."""

    def test_le_verrou_empeche_une_execution_concurrente(self):
        from .tasks import verrou

        with verrou("essai") as premier:
            self.assertTrue(premier)
            with verrou("essai") as second:
                self.assertFalse(second)

        # Le verrou est libéré à la sortie.
        with verrou("essai") as apres:
            self.assertTrue(apres)

    def test_la_tache_ignore_le_passage_si_le_verrou_est_pris(self):
        from django.core.cache import cache

        from .tasks import reconcile_lengopay

        cache.set("lock:reconcile_lengopay", "1", timeout=60)
        try:
            self.assertEqual(reconcile_lengopay(), {"skipped": True})
        finally:
            cache.delete("lock:reconcile_lengopay")

    def test_un_cache_indisponible_ne_bloque_pas_la_tache(self):
        """
        Redis en panne ne doit pas empêcher la réconciliation : mieux vaut un
        risque de doublon (neutralisé par select_for_update) qu'un filet de
        sécurité à l'arrêt.
        """
        from .tasks import verrou

        with patch("payments.tasks.cache.add", side_effect=Exception("cache muet")):
            with verrou("essai-panne") as obtenu:
                self.assertTrue(obtenu)
