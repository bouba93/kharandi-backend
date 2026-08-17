import hashlib
import hmac
import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ecole.models import School, SchoolStudent
from ecommerce.models import Order
from learning.models import Document, QCM
from payments.models import Plan, Subscription, Transaction
from users.models import Profile, User
from users.views import _create_user_with_profile
from notifications.tasks import send_otp_sms
from core.redis_utils import karamo_get_remaining
from ai_features.guinea_data import seed_guinea_knowledge
from ai_features.knowledge import get_guinea_context, should_search_guinea
from ai_features.models import GuineaKnowledgeEntry


def make_user(phone="+224600000001", role=User.Role.STUDENT, password="SafePass123"):
    user = User.objects.create_user(phone=phone, role=role)
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_user_cannot_promote_self_to_admin(self):
        response = self.client.patch(
            "/api/v1/auth/me/", {"role": "ADMIN", "city": "Conakry"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)
        self.assertEqual(self.user.profile.city, "Conakry")

    def test_user_cannot_credit_own_wallet(self):
        response = self.client.post(
            "/api/v1/auth/me/points/", {"points": 1000000}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 0)

    def test_password_login_uses_hashed_user_password(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/password/",
            {"phone": self.user.phone, "password": "SafePass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("tokens", response.data["data"])

    @override_settings(DEBUG=False, NIMBA_ACCOUNT_SID="", NIMBA_AUTH_TOKEN="")
    def test_otp_is_not_reported_as_sent_without_sms_provider_in_production(self):
        result = send_otp_sms("+224600000099")
        self.assertFalse(result["success"])
        self.assertEqual(result["local_code"], "")


class RegistrationTests(TestCase):
    def test_student_profile_fields_are_persisted_without_duplicate_profile(self):
        user = _create_user_with_profile(
            "+224600000010", "SafePass123", User.Role.STUDENT,
            {"niveau": "Terminale", "serie": "SM"},
        )
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(user.profile.niveau, "Terminale")
        self.assertEqual(user.profile.serie, "SM")

    def test_vendor_role_and_profile_are_supported(self):
        user = _create_user_with_profile(
            "+224600000011", "SafePass123", User.Role.VENDOR,
            {"shop_name": "Kharandi Shop", "shop_status": "ACTIVE"},
        )
        self.assertEqual(user.role, User.Role.VENDOR)
        self.assertEqual(user.profile.shop_name, "Kharandi Shop")


class SchoolSecurityTests(TestCase):
    def setUp(self):
        self.admin = make_user("+224600000020", User.Role.ADMIN)
        self.school = School.objects.create(
            name="École Test", email="school@example.com", code="CODE-SECRET"
        )

    def test_school_directory_is_not_public(self):
        response = APIClient().get("/api/v1/ecole/schools/")
        self.assertIn(response.status_code, (401, 403))

    def test_activation_code_is_not_exposed_and_cannot_reset_password(self):
        client = APIClient()
        response = client.post(
            "/api/v1/ecole/activate/",
            {"code": self.school.code, "email": self.school.email, "password": "SchoolPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("code", response.data["data"])

        second = client.post(
            "/api/v1/ecole/activate/",
            {"code": self.school.code, "email": self.school.email, "password": "HackedPass123"},
            format="json",
        )
        self.assertEqual(second.status_code, 400)

    def test_school_token_is_scoped_to_its_school(self):
        self.school.set_password("SchoolPass123")
        self.school.is_activated = True
        self.school.save()
        other = School.objects.create(
            name="Autre école", email="other@example.com", code="OTHER"
        )
        login = APIClient().post(
            "/api/v1/ecole/login/",
            {"email": self.school.email, "password": "SchoolPass123"},
            format="json",
        )
        token = login.data["data"]["access_token"]
        client = APIClient()
        client.credentials(HTTP_X_SCHOOL_TOKEN=token)
        own = client.get(f"/api/v1/ecole/schools/{self.school.id}/students/")
        forbidden = client.get(f"/api/v1/ecole/schools/{other.id}/students/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(forbidden.status_code, 403)

    def test_parent_can_only_read_own_child(self):
        parent = make_user("+224600000030", User.Role.PARENT)
        child = SchoolStudent.objects.create(
            school=self.school, name="Enfant", matricule="KHA-001",
            parent_phone=parent.phone,
        )
        stranger = make_user("+224600000031", User.Role.PARENT)
        ok = auth_client(parent).get(f"/api/v1/ecole/parent/{child.matricule}/")
        denied = auth_client(stranger).get(f"/api/v1/ecole/parent/{child.matricule}/")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(denied.status_code, 403)


@override_settings(LENGOPAY_WEBHOOK_SECRET="webhook-test-secret")
class PaymentSecurityTests(TestCase):
    def setUp(self):
        self.user = make_user("+224600000040")
        self.client = auth_client(self.user)
        self.plan = Plan.objects.create(
            name="Premium Mensuel", period=Plan.Period.MENSUEL,
            price=25000, currency="GNF",
        )

    def test_subscription_rejects_client_supplied_direct_amount(self):
        response = self.client.post(
            "/api/v1/payments/subscriptions/initiate/", {"amount": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("payments.views._call_lengopay")
    def test_order_and_payment_amount_are_calculated_server_side(self, gateway):
        gateway.return_value = {
            "success": True, "pay_id": "PAY-ORDER", "payment_url": "https://pay.test"
        }
        document = Document.objects.create(title="Livre", price=15000)
        order_response = self.client.post(
            "/api/v1/store/orders/create/",
            {"items": [{"document_id": str(document.id), "quantity": 2,
                         "unit_price": 1, "name": "Prix falsifié"}]},
            format="json",
        )
        self.assertEqual(order_response.status_code, 201)
        order = Order.objects.get(id=order_response.data["data"]["id"])
        self.assertEqual(order.total, 30000)

        payment_response = self.client.post(
            "/api/v1/payments/initiate/",
            {"order_id": str(order.id), "amount": 1}, format="json",
        )
        self.assertEqual(payment_response.status_code, 201)
        tx = Transaction.objects.get(id=payment_response.data["data"]["transaction_id"])
        self.assertEqual(tx.amount, order.total)

    @patch("notifications.tasks.send_payment_confirmation_sms")
    def test_webhook_requires_valid_signature(self, _sms):
        """
        Un callback non authentifié ne doit RIEN activer.

        Le code de réponse est volontairement 200 et non 403 : LengoPay
        réessaie sur code d'erreur, ce qui provoquerait une avalanche de
        retentatives sans jamais rien résoudre. On accuse donc réception
        (`verified: false`), on journalise, et l'abonnement reste inactif.
        """
        subscription = Subscription.objects.create(
            user=self.user, plan=self.plan, status=Subscription.Status.PENDING
        )
        Transaction.objects.create(
            user=self.user, subscription=subscription, reference="KHR-TEST",
            gateway_ref="PAY-123", amount=self.plan.price,
        )
        body = json.dumps({"pay_id": "PAY-123", "status": "SUCCESS"})

        # API LengoPay injoignable : aucune confirmation possible.
        import requests
        with patch("payments.lengopay.requests.post",
                   side_effect=requests.RequestException("API indisponible")):
            unsigned = APIClient().post(
                "/api/v1/payments/webhook/", data=body,
                content_type="application/json",
            )

        self.assertEqual(unsigned.status_code, 200)
        self.assertIs(unsigned.data.get("verified"), False)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.PENDING)

        # Signature HMAC valide ET statut confirmé par l'API → activation.
        signature = hmac.new(
            b"webhook-test-secret", body.encode(), hashlib.sha256
        ).hexdigest()

        class _ReponseApi:
            status_code = 200
            text = ""

            @staticmethod
            def json():
                return {"status": "SUCCESS", "pay_id": "PAY-123",
                        "amount": int(self.plan.price)}

        with patch("payments.lengopay.requests.post", return_value=_ReponseApi()):
            signed = APIClient().post(
                "/api/v1/payments/webhook/", data=body,
                content_type="application/json",
                HTTP_X_LENGOPAY_SIGNATURE=signature,
            )

        self.assertEqual(signed.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)


class RewardLogicTests(TestCase):
    def test_perfect_qcm_awards_fifty_points(self):
        user = make_user("+224600000050")
        questions = [
            {"id": i, "question": f"Q{i}", "options": ["A", "B"], "correct_index": 0}
            for i in range(1, 11)
        ]
        qcm = QCM.objects.create(
            user=user, subject="Maths", level="TERM", topic="Algèbre",
            questions=questions,
        )
        request = auth_client(user).post(
            f"/api/v1/ai/qcm/{qcm.id}/submit/",
            {"answers": {str(i): 0 for i in range(1, 11)}}, format="json",
        )
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data["data"]["points_earned"], 50)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.points_in_gnf, 5000)


# Le quota est épinglé à 5 pour cette classe : les assertions ci-dessous portent
# sur la MÉCANIQUE de débit et de remboursement, pas sur la valeur commerciale du
# quota (pilotée par KARAMO_FREE_DAILY_LIMIT dans l'environnement). Sans cet
# épinglage, changer le quota en production casserait ces tests à tort.
@override_settings(KARAMO_FREE_DAILY_LIMIT=5)
class KaramoSafetyTests(TestCase):
    def setUp(self):
        self.user = make_user("+224600000060")
        self.client = auth_client(self.user)

    def _questions(self):
        return [
            {
                "id": index,
                "question": f"Question {index} ?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "Parce que A est correcte.",
            }
            for index in range(1, 11)
        ]

    def test_malformed_history_is_normalised_not_rejected(self):
        """Un historique mal formé est du contexte : il est ignoré, pas refusé.

        Avant correctif, `history` non conforme renvoyait un HTTP 400 et Karamo
        devenait inutilisable dès que le client changeait de format.
        """
        with patch("ai_features.views._call_openrouter", return_value="Bonjour !"):
            response = self.client.post(
                "/api/v1/ai/ask/",
                {"message": "Bonjour", "history": "pas-une-liste"},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)

    def test_invalid_request_does_not_consume_quota(self):
        """Une requête réellement invalide (message absent) ne débite rien."""
        response = self.client.post("/api/v1/ai/ask/", {"history": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(karamo_get_remaining(self.user), 5)

    def test_provider_failure_refunds_chat_quota(self):
        with patch("ai_features.views._call_openrouter", side_effect=RuntimeError("down")):
            response = self.client.post(
                "/api/v1/ai/ask/", {"message": "Explique Pythagore"}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(karamo_get_remaining(self.user), 5)
        self.assertNotIn("down", str(response.data))

    def test_empty_stream_refunds_chat_quota(self):
        class EmptyStream:
            status_code = 200

            def iter_lines(self):
                return iter([b"data: [DONE]"])

        with patch("ai_features.views._call_openrouter", return_value=EmptyStream()):
            response = self.client.post(
                "/api/v1/ai/ask/stream/",
                {"message": "Explique les fonctions"},
                format="json",
            )
            body = b"".join(response.streaming_content).decode("utf-8")
        self.assertEqual(response.status_code, 200)
        # Le flux se termine désormais par un marqueur `event: end` : on lit le
        # premier évènement `data:`, qui porte l'erreur.
        premier = next(
            bloc for bloc in body.split("\n\n") if bloc.startswith("data: ")
        )
        event = json.loads(premier.removeprefix("data: ").strip())
        self.assertEqual(event["type"], "error")
        self.assertIn("aucune réponse", event["message"])
        self.assertEqual(karamo_get_remaining(self.user), 5)

    def test_generated_qcm_hides_solutions_and_costs_two_messages(self):
        generated = json.dumps({"questions": self._questions()})
        with patch("ai_features.views._call_openrouter", return_value=generated):
            response = self.client.post(
                "/api/v1/ai/generate-qcm/",
                {
                    "subject": "Mathématiques",
                    "level": "Terminale",
                    "topic": "Dérivées",
                    "difficulty": "moyen",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        first = response.data["data"]["questions"][0]
        self.assertNotIn("correct_index", first)
        self.assertNotIn("explanation", first)
        self.assertEqual(karamo_get_remaining(self.user), 3)
        qcm = QCM.objects.get(id=response.data["data"]["qcm_id"])
        self.assertIn("correct_index", qcm.questions[0])

    def test_invalid_generated_qcm_refunds_two_messages(self):
        with patch(
            "ai_features.views._call_openrouter",
            return_value=json.dumps({"questions": []}),
        ):
            response = self.client.post(
                "/api/v1/ai/generate-qcm/",
                {"subject": "Maths", "level": "Terminale", "topic": "Algèbre"},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(karamo_get_remaining(self.user), 5)

    def test_invalid_image_is_rejected_before_quota(self):
        image = SimpleUploadedFile("devoir.png", b"pas une image", "image/png")
        response = self.client.post(
            "/api/v1/ai/ask-image/", {"image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(karamo_get_remaining(self.user), 5)

    def test_incomplete_qcm_cannot_be_submitted_for_points(self):
        qcm = QCM.objects.create(
            user=self.user,
            subject="Maths",
            level="Terminale",
            topic="Algèbre",
            questions=self._questions(),
        )
        response = self.client.post(
            f"/api/v1/ai/qcm/{qcm.id}/submit/",
            {"answers": {"1": 0}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        qcm.refresh_from_db()
        self.assertFalse(qcm.completed)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 0)

    @override_settings(OPENROUTER_API_KEY="configured-test-key")
    def test_status_lists_capabilities_without_paid_probe(self):
        with patch("ai_features.views._call_openrouter") as call:
            response = self.client.get("/api/v1/ai/status/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("analyse_image", response.data["data"]["capabilities"])
        call.assert_not_called()


class GuineaKnowledgeTests(TestCase):
    def setUp(self):
        self.user = make_user("+224600000070")
        self.client = auth_client(self.user)

    def test_seed_is_idempotent_and_preserves_deactivated_entries(self):
        created, updated = seed_guinea_knowledge()
        self.assertEqual(created, 9)
        self.assertEqual(updated, 0)
        entry = GuineaKnowledgeEntry.objects.get(slug="mont-nimba")
        entry.is_active = False
        entry.save(update_fields=["is_active"])

        created, updated = seed_guinea_knowledge()
        self.assertEqual(created, 0)
        self.assertEqual(updated, 9)
        entry.refresh_from_db()
        self.assertFalse(entry.is_active)

    def test_retrieval_returns_relevant_sourced_guinea_facts(self):
        seed_guinea_knowledge()
        context = get_guinea_context(
            "Quelles sont les quatre régions naturelles de la Guinée ?"
        )
        self.assertIn("Les quatre régions naturelles", context)
        self.assertIn("Source :", context)
        self.assertIn("https://", context)

    def test_guinea_bissau_does_not_trigger_republic_of_guinea_knowledge(self):
        self.assertFalse(should_search_guinea("Quelle est la capitale de la Guinée Bissau ?"))
        self.assertTrue(should_search_guinea("Compare la Guinée et la Guinée-Bissau"))

    def test_chat_injects_guinea_knowledge_into_model_context(self):
        seed_guinea_knowledge()
        with patch("ai_features.views._call_openrouter", return_value="Conakry") as call:
            response = self.client.post(
                "/api/v1/ai/ask/",
                {"message": "Quelle est la capitale de la Guinée ?"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["guinea_knowledge"])
        messages = call.call_args.args[0]
        self.assertIn("[CONNAISSANCES GUINÉE", messages[-1]["content"])
        self.assertIn("Conakry", messages[-1]["content"])

    def test_current_guinea_question_uses_web_and_local_knowledge(self):
        seed_guinea_knowledge()
        with (
            patch("ai_features.views._web_search", return_value="Source officielle") as search,
            patch("ai_features.views._call_openrouter", return_value="Réponse vérifiée"),
        ):
            response = self.client.post(
                "/api/v1/ai/ask/",
                {"message": "Qui est le président actuel de la Guinée ?"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["web_search"])
        self.assertTrue(response.data["data"]["guinea_knowledge"])
        search.assert_called_once()

    def test_dedicated_seed_command_loads_knowledge(self):
        call_command("seed_guinea_knowledge", verbosity=0)
        self.assertEqual(GuineaKnowledgeEntry.objects.count(), 9)
