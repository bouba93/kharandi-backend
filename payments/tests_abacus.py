"""
payments/tests_abacus.py — Kharandi Abacus (achat unique 45 000 GNF)
────────────────────────────────────────────────────────────────────
Ce que ces tests garantissent, point par point, sur le cahier des charges :

  1. le produit existe côté backend (nom, slug, prix, devise, actif) ;
  2. le montant vient de la base, jamais de la requête du frontend ;
  3. le paiement Abacus n'active JAMAIS Premium ni aucun abonnement ;
  4. Abacus ne peut pas être acheté via l'endpoint d'abonnement ;
  5. les alias historiques du frontend continuent de fonctionner ;
  6. le droit d'accès n'est accordé qu'après confirmation LengoPay ;
  7. pas de double facturation du même accès.

Exécution :
    docker compose exec api python manage.py test payments.tests_abacus -v 2
"""
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from ecommerce.models import Order, OrderItem
from .models import Plan, Subscription, Transaction

User = get_user_model()

JETON = "jeton-de-test-tres-long-0123456789abcdef"
PAY_ID = "cGF5X2lkX2FiYWN1cw=="
SLUG = "kharandi-abacus"
PRIX = Decimal("45000")


class _Reponse:
    def __init__(self, code, donnees):
        self.status_code = code
        self._donnees = donnees
        self.text = str(donnees)

    def json(self):
        return self._donnees


def _reponse_creation():
    return _Reponse(200, {
        "status": "success", "pay_id": PAY_ID,
        "payment_url": "https://portal.lengopay.com/p/abacus",
    })


@override_settings(
    LENGOPAY_CALLBACK_TOKEN=JETON,
    LENGOPAY_REQUIRE_STATUS_CONFIRMATION=False,
    LENGOPAY_AMOUNT_TOLERANCE="1",
    RATE_LIMIT_ENABLED=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class KharandiAbacusTests(TestCase):
    def setUp(self):
        call_command("seed_plans", stdout=StringIO())
        self.user = User.objects.create_user(phone="+224622100100")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.abacus = Plan.objects.get(slug=SLUG)

    # ── 1. Le produit est défini côté backend ───────────────────────────────
    def test_le_produit_existe_avec_le_bon_prix_et_la_bonne_devise(self):
        self.assertEqual(self.abacus.name, "Kharandi Abacus")
        self.assertEqual(self.abacus.price, PRIX)
        self.assertEqual(self.abacus.currency, "GNF")
        self.assertTrue(self.abacus.is_active)
        self.assertEqual(self.abacus.period, Plan.Period.PONCTUEL)

    def test_le_slug_est_stable_et_unique(self):
        self.assertEqual(Plan.objects.filter(slug=SLUG).count(), 1)

    def test_amorcage_rejoue_ne_duplique_pas_le_produit(self):
        call_command("seed_plans", stdout=StringIO())
        self.assertEqual(Plan.objects.filter(name="Kharandi Abacus").count(), 1)

    # ── 2. Le montant est imposé par le backend ─────────────────────────────
    def test_le_frontend_ne_peut_pas_imposer_son_montant(self):
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            r = self.client.post(
                "/api/v1/payments/products/initiate/",
                {"product": SLUG, "amount": "1", "price": 1, "total": 1},
                format="json",
            )
        self.assertEqual(r.status_code, 201, r.data)
        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.amount, PRIX)
        self.assertEqual(tx.currency, "GNF")
        self.assertEqual(Order.objects.get(user=self.user).total, PRIX)

    def test_les_alias_frontend_resolvent_le_produit(self):
        from .views import _get_plan
        for alias in ["abacus", "abaque", "kharandi-abacus", "kharandi_abacus",
                      "Kharandi Abacus", str(self.abacus.id)]:
            self.assertEqual(_get_plan(alias), self.abacus, f"alias « {alias} »")

    def test_les_alias_historiques_ne_sont_pas_casses(self):
        from .views import _get_plan
        for alias, attendu in [("mensuel", "Premium Mensuel"),
                               ("annuel", "Premium Annuel"),
                               ("seller", "Boutique Vendeur"),
                               ("boutique", "Boutique Vendeur"),
                               ("gratuit", "Gratuit")]:
            self.assertEqual(_get_plan(alias).name, attendu)

    # ── 3. Aucun effet sur les abonnements ──────────────────────────────────
    def test_abacus_est_refuse_par_l_endpoint_d_abonnement(self):
        r = self.client.post(
            "/api/v1/payments/subscriptions/initiate/",
            {"plan_id": "abacus"}, format="json",
        )
        self.assertEqual(r.status_code, 400, r.data)
        self.assertFalse(Subscription.objects.filter(user=self.user).exists())

    def test_le_paiement_abacus_n_active_aucun_abonnement(self):
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/products/initiate/",
                             {"product": SLUG}, format="json")
        tx = Transaction.objects.get(user=self.user)
        self.assertIsNone(tx.subscription)

        self._confirmer_paiement()

        tx.refresh_from_db()
        self.assertEqual(tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(tx.order.status, Order.Status.PAID)
        # Aucun abonnement créé, donc aucun accès Premium accordé.
        self.assertFalse(Subscription.objects.filter(user=self.user).exists())

    def test_un_premium_en_cours_n_est_pas_ecrase_par_un_achat_abacus(self):
        """Le point le plus sensible : Subscription est un OneToOne."""
        premium = Plan.objects.get(name="Premium Mensuel")
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/subscriptions/initiate/",
                             {"plan_id": "mensuel"}, format="json")
        sub = Subscription.objects.get(user=self.user)
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status"])

        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            r = self.client.post("/api/v1/payments/products/initiate/",
                                 {"product": SLUG}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self._confirmer_paiement()

        sub.refresh_from_db()
        self.assertEqual(sub.plan, premium)
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)

    # ── 4. Droit d'accès ────────────────────────────────────────────────────
    def test_aucun_droit_avant_paiement(self):
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/products/initiate/",
                             {"product": SLUG}, format="json")
        r = self.client.get("/api/v1/payments/entitlements/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["data"]["products"], {})

    def test_droit_accorde_apres_confirmation_lengopay(self):
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/products/initiate/",
                             {"product": SLUG}, format="json")
        self._confirmer_paiement()

        r = self.client.get("/api/v1/payments/entitlements/")
        self.assertTrue(r.data["data"]["products"].get(SLUG))
        self.assertEqual(r.data["data"]["purchased"][0]["amount"], "45000.00")

    def test_pas_de_seconde_facturation_du_meme_acces(self):
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/products/initiate/",
                             {"product": SLUG}, format="json")
        self._confirmer_paiement()
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            r = self.client.post("/api/v1/payments/products/initiate/",
                                 {"product": SLUG}, format="json")
        self.assertEqual(r.status_code, 409, r.data)

    def test_un_abonnement_ne_passe_pas_par_l_endpoint_produit(self):
        r = self.client.post("/api/v1/payments/products/initiate/",
                             {"product": "mensuel"}, format="json")
        self.assertEqual(r.status_code, 400, r.data)
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_endpoint_produit_refuse_les_anonymes(self):
        anonyme = APIClient()
        r = anonyme.post("/api/v1/payments/products/initiate/",
                         {"product": SLUG}, format="json")
        self.assertIn(r.status_code, (401, 403))

    def test_produit_inconnu_renvoie_404(self):
        r = self.client.post("/api/v1/payments/products/initiate/",
                             {"product": "produit-qui-n-existe-pas"}, format="json")
        self.assertEqual(r.status_code, 404, r.data)

    def test_le_droit_est_lie_au_produit_pas_au_libelle(self):
        """La vérification passe par la clé étrangère `plan`, pas par le texte."""
        with patch("payments.lengopay.requests.post", return_value=_reponse_creation()):
            self.client.post("/api/v1/payments/products/initiate/",
                             {"product": SLUG}, format="json")
        self._confirmer_paiement()
        ligne = OrderItem.objects.get(order__user=self.user)
        self.assertEqual(ligne.plan, self.abacus)
        self.assertEqual(ligne.unit_price, PRIX)

    # ── Utilitaire : rejoue le callback LengoPay authentifié ────────────────
    def _confirmer_paiement(self):
        tx = Transaction.objects.filter(user=self.user, order__isnull=False).latest("created_at")
        charge = {
            "pay_id": tx.gateway_ref,
            "status": "SUCCESS",
            "amount": float(tx.amount),
            "message": "Transaction Successful",
            "Client": "622100100",
        }
        r = self.client.post(f"/api/v1/payments/webhook/{JETON}/", charge, format="json")
        self.assertEqual(r.status_code, 200, r.data)
