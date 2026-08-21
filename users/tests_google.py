"""
users/tests_google.py — Connexion Google pilotée par Django
═══════════════════════════════════════════════════════════

Ces tests couvrent les 15 cas exigés par le cahier des charges, plus la
non-régression du reste de l'authentification.

Le dialogue réseau avec Google est simulé aux deux seules frontières sortantes
(`echanger_code` et `verifier_id_token`) : tout le reste — state, nonce, PKCE,
tickets, liaison de comptes, création d'utilisateur, JWT — est exécuté pour de
vrai contre la base de test.
"""
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from users.google_oauth import GoogleOAuthError, code_challenge
from users.models import (
    GoogleAccount, GoogleAuthTicket, GoogleOAuthState, OTPRecord, Profile, User,
)

IDENTITE_GOOGLE = {
    "sub": "1234567890google",
    "email": "mariama@example.com",
    "email_verified": True,
    "given_name": "Mariama",
    "family_name": "Diallo",
}

REGLAGES_GOOGLE = dict(
    GOOGLE_CLIENT_ID="client-id-de-test.apps.googleusercontent.com",
    GOOGLE_CLIENT_SECRET="secret-de-test",
    GOOGLE_OAUTH_REDIRECT_URI="https://api.kharandi.gn/api/v1/auth/google/callback/",
    GOOGLE_POST_LOGIN_WEB_URL="https://kharandi.gn/auth/google/retour",
    GOOGLE_POST_LOGIN_MOBILE_URL="kharandi://auth/google",
)


@override_settings(**REGLAGES_GOOGLE)
class BaseGoogleTests(TestCase):
    """Outils communs : démarrage du flux, callback simulé, OTP vérifié."""

    def _demarrer(self, platform="web"):
        reponse = self.client.get(reverse("google-login"), {"platform": platform})
        self.assertEqual(reponse.status_code, 302)
        return GoogleOAuthState.objects.latest("created_at")

    def _callback(self, etat, identite=None, erreur=None, state=None):
        """Rejoue le callback Google avec une identité vérifiée simulée."""
        identite = identite or dict(IDENTITE_GOOGLE)
        with patch("users.google_oauth.echanger_code",
                   return_value={"id_token": "jeton-simule"}) as echange, \
             patch("users.google_oauth.verifier_id_token",
                   side_effect=erreur if erreur else None,
                   return_value=identite) as verif:
            reponse = self.client.get(reverse("google-callback"), {
                "code": "code-google", "state": state or (etat.state if etat else ""),
            })
        self.echange = echange
        self.verif = verif
        return reponse

    def _params_retour(self, reponse):
        self.assertEqual(reponse.status_code, 302)
        return parse_qs(urlparse(reponse["Location"]).query), reponse["Location"]

    def _otp_pret(self, phone):
        """Crée un OTP en attente sur ce numéro (mécanisme existant, inchangé)."""
        from users.views import _normalize_phone
        return OTPRecord.objects.create(
            phone=_normalize_phone(phone), verificationid="verif-1",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def _completer(self, code_ticket, phone, role="STUDENT", otp_valide=True, **extra):
        self._otp_pret(phone)
        with patch("notifications.tasks.verify_otp_sms", return_value=otp_valide):
            return self.client.post(reverse("google-complete"), {
                "code": code_ticket, "phone": phone, "code_otp": "123456",
                "role": role, **extra,
            }, content_type="application/json")

    def _code_ticket_via_callback(self, platform="web", identite=None):
        etat = self._demarrer(platform)
        reponse = self._callback(etat, identite=identite)
        params, _ = self._params_retour(reponse)
        return params, reponse


# ═══════════════════ 1. Démarrage du flux OAuth ═══════════════════════════════
class DemarrageOAuthTests(BaseGoogleTests):

    def test_demarrage_redirige_vers_google_avec_state_nonce_et_pkce(self):
        """Cas 1 — le flux part de Django, avec state, nonce et PKCE S256."""
        reponse = self.client.get(reverse("google-login"))
        self.assertEqual(reponse.status_code, 302)
        url = urlparse(reponse["Location"])
        self.assertEqual(url.netloc, "accounts.google.com")
        params = parse_qs(url.query)

        etat = GoogleOAuthState.objects.get()
        self.assertEqual(params["state"], [etat.state])
        self.assertEqual(params["nonce"], [etat.nonce])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["code_challenge"], [code_challenge(etat.code_verifier)])
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["redirect_uri"],
                         [REGLAGES_GOOGLE["GOOGLE_OAUTH_REDIRECT_URI"]])
        # Le secret client ne quitte jamais le serveur.
        self.assertNotIn("client_secret", params)
        self.assertNotIn("secret-de-test", reponse["Location"])

    def test_le_verifier_pkce_ne_quitte_jamais_le_serveur(self):
        reponse = self.client.get(reverse("google-login"))
        etat = GoogleOAuthState.objects.get()
        self.assertNotIn(etat.code_verifier, reponse["Location"])

    @override_settings(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="")
    def test_sans_configuration_google_l_endpoint_est_indisponible(self):
        """Sans identifiants, Google est simplement inactif : 503, jamais 500."""
        reponse = self.client.get(reverse("google-login"))
        self.assertEqual(reponse.status_code, 503)
        self.assertFalse(GoogleOAuthState.objects.exists())

    def test_la_cible_mobile_est_un_deep_link_sans_secret(self):
        etat = self._demarrer("mobile")
        self.assertEqual(etat.platform, "mobile")
        params, url = self._params_retour(self._callback(etat))
        self.assertTrue(url.startswith("kharandi://auth/google"))
        self.assertNotIn("secret", url)
        self.assertNotIn("access", url)


# ═══════════════════ 2 à 5. Callback et rejets de sécurité ════════════════════
class CallbackTests(BaseGoogleTests):

    def test_callback_valide_verifie_l_identite_et_ne_cree_rien(self):
        """Cas 2 — callback valide : identité vérifiée, aucun compte créé."""
        params, _ = self._code_ticket_via_callback()
        self.assertEqual(params["status"], ["signup_required"])
        self.assertEqual(GoogleAuthTicket.objects.count(), 1)
        ticket = GoogleAuthTicket.objects.get()
        self.assertEqual(ticket.kind, GoogleAuthTicket.Kind.SIGNUP)
        self.assertIsNone(ticket.user)
        # Aucun utilisateur créé sans téléphone vérifié.
        self.assertEqual(User.objects.count(), 0)
        # Le code en clair n'est pas stocké : seul son SHA-256 l'est.
        self.assertNotEqual(ticket.code_hash, params["code"][0])
        self.assertEqual(len(ticket.code_hash), 64)

    def test_state_invalide_est_refuse(self):
        """Cas 3 — un state inconnu interrompt le flux."""
        self._demarrer()
        reponse = self._callback(None, state="state-forge")
        params, _ = self._params_retour(reponse)
        self.assertEqual(params["status"], ["error"])
        self.assertEqual(params["reason"], ["invalid_state"])
        self.assertFalse(GoogleAuthTicket.objects.exists())
        self.assertEqual(User.objects.count(), 0)

    def test_state_est_a_usage_unique(self):
        etat = self._demarrer()
        self._callback(etat)
        etat.refresh_from_db()
        self.assertIsNotNone(etat.used_at)
        params, _ = self._params_retour(self._callback(etat))
        self.assertEqual(params["reason"], ["invalid_state"])

    def test_state_expire_est_refuse(self):
        etat = self._demarrer()
        GoogleOAuthState.objects.filter(pk=etat.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        params, _ = self._params_retour(self._callback(etat))
        self.assertEqual(params["reason"], ["invalid_state"])

    def test_identite_google_invalide_est_refusee(self):
        """Cas 4 — signature, audience ou émetteur invalide : rien n'est créé."""
        etat = self._demarrer()
        reponse = self._callback(etat, erreur=GoogleOAuthError("invalid_identity"))
        params, _ = self._params_retour(reponse)
        self.assertEqual(params["status"], ["error"])
        self.assertEqual(params["reason"], ["invalid_identity"])
        self.assertFalse(GoogleAuthTicket.objects.exists())
        self.assertEqual(User.objects.count(), 0)

    def test_email_non_verifie_est_refuse(self):
        """Cas 5 — un email Google non vérifié n'authentifie personne."""
        etat = self._demarrer()
        reponse = self._callback(etat, erreur=GoogleOAuthError("email_not_verified"))
        params, _ = self._params_retour(reponse)
        self.assertEqual(params["reason"], ["email_not_verified"])
        self.assertFalse(GoogleAuthTicket.objects.exists())
        self.assertEqual(User.objects.count(), 0)

    def test_refus_utilisateur_chez_google_est_gere(self):
        etat = self._demarrer()
        reponse = self.client.get(reverse("google-callback"),
                                  {"error": "access_denied", "state": etat.state})
        params, _ = self._params_retour(reponse)
        self.assertEqual(params["reason"], ["access_denied"])

    def test_la_redirection_de_retour_est_toujours_une_cible_de_liste_blanche(self):
        """Aucune redirection ouverte : la cible ne vient jamais de la requête."""
        etat = self._demarrer()
        # Aucun appel réseau : l'échange est simulé en échec, seule la cible de
        # redirection est observée.
        with patch("users.google_oauth.echanger_code",
                   side_effect=GoogleOAuthError("token_exchange_failed")):
            reponse = self.client.get(reverse("google-callback"), {
                "code": "c", "state": etat.state,
                "next": "https://pirate.example.com/vol",
                "redirect_uri": "https://pirate.example.com/vol",
            })
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(reponse["Location"].startswith(
            REGLAGES_GOOGLE["GOOGLE_POST_LOGIN_WEB_URL"]))
        self.assertNotIn("pirate.example.com", reponse["Location"])


# ═══════════════════ 6. Nouvel utilisateur ════════════════════════════════════
class NouvelUtilisateurTests(BaseGoogleTests):

    def test_nouvel_utilisateur_cree_apres_otp_et_choix_du_role(self):
        """Cas 6 — création selon les règles actuelles : phone + OTP + rôle."""
        params, _ = self._code_ticket_via_callback()
        code = params["code"][0]

        # Étape intermédiaire : le frontend apprend qu'il faut compléter.
        echange = self.client.post(reverse("google-exchange"), {"code": code},
                                   content_type="application/json")
        self.assertEqual(echange.status_code, 200)
        self.assertEqual(echange.json()["data"]["status"], "signup_required")
        self.assertEqual(echange.json()["data"]["google"]["email"],
                         IDENTITE_GOOGLE["email"])

        reponse = self._completer(code, "620000001", role="STUDENT",
                                  niveau="Terminale", serie="SM")
        self.assertEqual(reponse.status_code, 201)
        donnees = reponse.json()["data"]

        user = User.objects.get(phone="+224620000001")
        self.assertEqual(user.role, "STUDENT")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.niveau, "Terminale")
        self.assertEqual(user.profile.serie, "SM")
        self.assertEqual(user.profile.first_name, "Mariama")
        self.assertFalse(user.profile.onboarding_completed)
        # Google est enregistré comme méthode d'authentification, rien de plus.
        compte = GoogleAccount.objects.get(user=user)
        self.assertEqual(compte.google_sub, IDENTITE_GOOGLE["sub"])
        self.assertTrue(compte.email_verified)
        self.assertTrue(donnees["is_new"])
        # Sans mot de passe choisi, aucun secret inconnu mais utilisable.
        self.assertFalse(user.has_usable_password())

    def test_le_ticket_d_inscription_est_a_usage_unique(self):
        params, _ = self._code_ticket_via_callback()
        code = params["code"][0]
        self.assertEqual(self._completer(code, "620000002").status_code, 201)
        seconde = self._completer(code, "620000003")
        self.assertEqual(seconde.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_otp_incorrect_empeche_toute_creation(self):
        params, _ = self._code_ticket_via_callback()
        reponse = self._completer(params["code"][0], "620000004", otp_valide=False)
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(GoogleAccount.objects.exists())

    def test_sans_otp_actif_aucune_creation(self):
        params, _ = self._code_ticket_via_callback()
        with patch("notifications.tasks.verify_otp_sms", return_value=True):
            reponse = self.client.post(reverse("google-complete"), {
                "code": params["code"][0], "phone": "620000005",
                "code_otp": "123456", "role": "STUDENT",
            }, content_type="application/json")
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_google_ne_peut_jamais_attribuer_un_role_privilegie(self):
        """Cas 6 (suite) — ADMIN est refusé, aucun rôle n'est déduit de Google."""
        params, _ = self._code_ticket_via_callback()
        for role in ("ADMIN", "admin", "SUPERUSER", "inconnu"):
            reponse = self._completer(params["code"][0], "620000006", role=role)
            self.assertEqual(reponse.status_code, 400, role)
        self.assertEqual(User.objects.count(), 0)

    def test_le_workflow_repetiteur_reste_en_attente_de_validation(self):
        """Le choix élève/répétiteur et la validation manuelle sont conservés."""
        params, _ = self._code_ticket_via_callback()
        reponse = self._completer(params["code"][0], "620000007", role="TUTOR",
                                  nom="Alpha Camara", matieres=["Maths"],
                                  niveaux=["Terminale"], zone="Ratoma")
        self.assertEqual(reponse.status_code, 201)
        user = User.objects.get(phone="+224620000007")
        self.assertEqual(user.role, "TUTOR")
        self.assertEqual(user.profile.tutor_status, "PENDING")
        self.assertEqual(reponse.json()["data"]["validation_status"], "pending")


# ═══════════════════ 7 à 9. Comptes existants, liaison, doublons ══════════════
class ComptesExistantsTests(BaseGoogleTests):

    def setUp(self):
        self.user = User.objects.create_user(phone="+224620111222", role="TUTOR")
        self.user.set_password("motdepasse")
        self.user.save(update_fields=["password"])
        self.profil = Profile.objects.get_or_create(user=self.user)[0]
        self.profil.display_name = "Fatoumata"
        self.profil.tutor_status = "APPROVED"
        self.profil.points = 350
        self.profil.save()

    def test_utilisateur_existant_est_lie_sans_doublon(self):
        """Cas 7 & 9 — même personne : liaison, pas de second compte."""
        params, _ = self._code_ticket_via_callback()
        reponse = self._completer(params["code"][0], "620111222", role="STUDENT")
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.json()["data"]["linked"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(GoogleAccount.objects.count(), 1)
        self.assertEqual(GoogleAccount.objects.get().user, self.user)

    def test_la_liaison_ne_modifie_ni_role_ni_profil_ni_donnees(self):
        """Cas 11, 12 & 14 — rôle, Profile et données restent intacts."""
        params, _ = self._code_ticket_via_callback()
        self._completer(params["code"][0], "620111222", role="STUDENT")
        self.user.refresh_from_db()
        self.profil.refresh_from_db()
        # Le rôle demandé (STUDENT) est IGNORÉ : le compte existe déjà.
        self.assertEqual(self.user.role, "TUTOR")
        self.assertEqual(self.profil.display_name, "Fatoumata")
        self.assertEqual(self.profil.tutor_status, "APPROVED")
        self.assertEqual(self.profil.points, 350)
        self.assertTrue(self.user.check_password("motdepasse"))

    def test_l_abonnement_et_les_commandes_survivent_a_la_liaison(self):
        """Cas 13 & 14 — abonnement, commandes et transactions inchangés."""
        from ecommerce.models import Order
        from payments.models import Plan, Subscription

        plan = Plan.objects.create(name="Premium", period=Plan.Period.MENSUEL,
                                   price=50000)
        abonnement = Subscription.objects.create(
            user=self.user, plan=plan, status=Subscription.Status.ACTIVE,
            start_date=timezone.now(), end_date=timezone.now() + timedelta(days=30),
        )
        commande = Order.objects.create(user=self.user, total=45000,
                                        status=Order.Status.PAID)

        params, _ = self._code_ticket_via_callback()
        self._completer(params["code"][0], "620111222")

        abonnement.refresh_from_db()
        commande.refresh_from_db()
        self.assertEqual(abonnement.status, Subscription.Status.ACTIVE)
        self.assertEqual(abonnement.plan_id, plan.id)
        self.assertTrue(abonnement.is_active())
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(commande.total, 45000)
        self.assertEqual(commande.status, Order.Status.PAID)

    def test_compte_google_deja_lie_connecte_directement(self):
        """Cas 8 — identité Google déjà liée : connexion immédiate."""
        GoogleAccount.objects.create(
            user=self.user, google_sub=IDENTITE_GOOGLE["sub"],
            email=IDENTITE_GOOGLE["email"], email_verified=True,
        )
        params, _ = self._code_ticket_via_callback()
        self.assertEqual(params["status"], ["authenticated"])

        reponse = self.client.post(reverse("google-exchange"),
                                   {"code": params["code"][0]},
                                   content_type="application/json")
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()["data"]
        self.assertEqual(donnees["user"]["phone"], "+224620111222")
        self.assertEqual(donnees["user"]["role"], "TUTOR")
        self.assertFalse(donnees["is_new"])
        self.assertEqual(User.objects.count(), 1)
        GoogleAccount.objects.get().refresh_from_db()
        self.assertIsNotNone(GoogleAccount.objects.get().last_used_at)

    def test_le_ticket_de_connexion_est_a_usage_unique(self):
        GoogleAccount.objects.create(user=self.user,
                                     google_sub=IDENTITE_GOOGLE["sub"],
                                     email_verified=True)
        params, _ = self._code_ticket_via_callback()
        code = params["code"][0]
        self.assertEqual(self.client.post(reverse("google-exchange"), {"code": code},
                                          content_type="application/json").status_code, 200)
        rejoue = self.client.post(reverse("google-exchange"), {"code": code},
                                  content_type="application/json")
        self.assertEqual(rejoue.status_code, 400)

    def test_une_identite_google_ne_peut_pas_etre_liee_a_deux_comptes(self):
        """Cas 9 — prévention des doublons et des associations frauduleuses."""
        GoogleAccount.objects.create(user=self.user,
                                     google_sub=IDENTITE_GOOGLE["sub"],
                                     email_verified=True)
        autre = User.objects.create_user(phone="+224620999888", role="STUDENT")
        Profile.objects.get_or_create(user=autre)

        ticket = GoogleAuthTicket.objects.create(
            code_hash=__import__("hashlib").sha256(b"code-brut").hexdigest(),
            kind=GoogleAuthTicket.Kind.SIGNUP,
            google_sub=IDENTITE_GOOGLE["sub"], email=IDENTITE_GOOGLE["email"],
            email_verified=True,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        reponse = self._completer("code-brut", "620999888")
        self.assertEqual(reponse.status_code, 409)
        self.assertEqual(reponse.json()["errors"]["code"], "google_already_linked")
        self.assertEqual(GoogleAccount.objects.count(), 1)
        self.assertEqual(GoogleAccount.objects.get().user, self.user)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.used_at)

    def test_un_compte_kharandi_ne_peut_pas_etre_lie_a_deux_comptes_google(self):
        GoogleAccount.objects.create(user=self.user, google_sub="autre-sub-google",
                                     email_verified=True)
        params, _ = self._code_ticket_via_callback()
        reponse = self._completer(params["code"][0], "620111222")
        self.assertEqual(reponse.status_code, 409)
        self.assertEqual(reponse.json()["errors"]["code"], "user_already_linked")

    def test_liaison_par_un_utilisateur_deja_authentifie(self):
        """Chemin le plus sûr : JWT Kharandi valide + flux Google complet."""
        params, _ = self._code_ticket_via_callback()
        from users.views import _get_tokens
        acces = _get_tokens(self.user)["access"]
        reponse = self.client.post(
            reverse("google-link"), {"code": params["code"][0]},
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {acces}")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(GoogleAccount.objects.get().user, self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "TUTOR")

    def test_la_liaison_exige_une_authentification(self):
        params, _ = self._code_ticket_via_callback()
        reponse = self.client.post(reverse("google-link"),
                                   {"code": params["code"][0]},
                                   content_type="application/json")
        self.assertEqual(reponse.status_code, 401)
        self.assertFalse(GoogleAccount.objects.exists())


# ═══════════════════ 10. Utilisateur désactivé ════════════════════════════════
class UtilisateurDesactiveTests(BaseGoogleTests):

    def setUp(self):
        self.user = User.objects.create_user(phone="+224620555444", role="STUDENT")
        Profile.objects.get_or_create(user=self.user)
        GoogleAccount.objects.create(user=self.user,
                                     google_sub=IDENTITE_GOOGLE["sub"],
                                     email_verified=True)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

    def test_un_compte_desactive_ne_peut_pas_se_connecter_par_google(self):
        """Cas 10 — Google ne contourne pas la désactivation d'un compte."""
        params, _ = self._code_ticket_via_callback()
        self.assertEqual(params["status"], ["error"])
        self.assertEqual(params["reason"], ["account_disabled"])
        self.assertFalse(GoogleAuthTicket.objects.exists())

    def test_un_ticket_ne_reanime_pas_un_compte_desactive(self):
        ticket_code = "code-direct"
        GoogleAuthTicket.objects.create(
            code_hash=__import__("hashlib").sha256(ticket_code.encode()).hexdigest(),
            kind=GoogleAuthTicket.Kind.LOGIN, user=self.user,
            google_sub=IDENTITE_GOOGLE["sub"], email_verified=True,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        reponse = self.client.post(reverse("google-exchange"), {"code": ticket_code},
                                   content_type="application/json")
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(reponse.json()["errors"]["code"], "account_disabled")

    def test_un_compte_desactive_ne_peut_pas_etre_lie_par_otp(self):
        GoogleAccount.objects.all().delete()
        params, _ = self._code_ticket_via_callback()
        reponse = self._completer(params["code"][0], "620555444")
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(GoogleAccount.objects.exists())


# ═══════════════════ 15. Même authentification que le login actuel ════════════
class MemeAuthentificationTests(BaseGoogleTests):

    def setUp(self):
        self.user = User.objects.create_user(phone="+224621777666", role="STUDENT")
        self.user.set_password("motdepasse")
        self.user.save(update_fields=["password"])
        Profile.objects.get_or_create(user=self.user)
        GoogleAccount.objects.create(user=self.user,
                                     google_sub=IDENTITE_GOOGLE["sub"],
                                     email_verified=True)

    def test_google_renvoie_exactement_le_meme_contrat_que_le_login(self):
        """Cas 15 — aucun second système de jetons, même contrat de réponse."""
        classique = self.client.post(reverse("login"), {
            "phone": "621777666", "password": "motdepasse",
        }, content_type="application/json")
        self.assertEqual(classique.status_code, 200)

        params, _ = self._code_ticket_via_callback()
        par_google = self.client.post(reverse("google-exchange"),
                                      {"code": params["code"][0]},
                                      content_type="application/json")
        self.assertEqual(par_google.status_code, 200)

        attendu = {"user", "tokens", "device_token"}
        self.assertTrue(attendu.issubset(classique.json()["data"].keys()))
        self.assertTrue(attendu.issubset(par_google.json()["data"].keys()))
        self.assertEqual(set(classique.json()["data"]["tokens"]),
                         set(par_google.json()["data"]["tokens"]))
        self.assertEqual(classique.json()["data"]["user"],
                         par_google.json()["data"]["user"])

    def test_le_jeton_google_est_un_jwt_kharandi_valide_sur_les_endpoints_existants(self):
        params, _ = self._code_ticket_via_callback()
        donnees = self.client.post(reverse("google-exchange"),
                                   {"code": params["code"][0]},
                                   content_type="application/json").json()["data"]
        reponse = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"Bearer {donnees['tokens']['access']}")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["data"]["phone"], "+224621777666")

        # Le refresh passe par l'endpoint simplejwt existant, inchangé.
        rafraichi = self.client.post(reverse("token-refresh"),
                                     {"refresh": donnees["tokens"]["refresh"]},
                                     content_type="application/json")
        self.assertEqual(rafraichi.status_code, 200)
        self.assertIn("access", rafraichi.json())

    def test_aucune_reponse_google_n_expose_de_secret_ni_de_jeton_google(self):
        params, _ = self._code_ticket_via_callback()
        corps = self.client.post(reverse("google-exchange"),
                                 {"code": params["code"][0]},
                                 content_type="application/json").content.decode()
        for interdit in ("secret-de-test", "client_secret", "id_token",
                         "google_sub", IDENTITE_GOOGLE["sub"]):
            self.assertNotIn(interdit, corps)


# ═══════════════════ Non-régression de l'authentification existante ═══════════
class NonRegressionAuthTests(BaseGoogleTests):

    def test_la_connexion_par_mot_de_passe_reste_identique(self):
        user = User.objects.create_user(phone="+224622333444", role="STUDENT")
        user.set_password("motdepasse")
        user.save(update_fields=["password"])
        Profile.objects.get_or_create(user=user)
        reponse = self.client.post(reverse("login"), {
            "phone": "622333444", "password": "motdepasse",
        }, content_type="application/json")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("device_token", reponse.json()["data"])

    def test_l_inscription_eleve_classique_reste_identique(self):
        OTPRecord.objects.create(phone="+224623111000", verificationid="v",
                                 expires_at=timezone.now() + timedelta(minutes=5))
        with patch("notifications.tasks.verify_otp_sms", return_value=True):
            reponse = self.client.post(reverse("register-eleve"), {
                "phone": "623111000", "code": "123456", "password": "motdepasse",
                "niveau": "Terminale", "serie": "SM",
            }, content_type="application/json")
        self.assertEqual(reponse.status_code, 201)
        user = User.objects.get(phone="+224623111000")
        self.assertFalse(GoogleAccount.objects.filter(user=user).exists())
        self.assertTrue(user.has_usable_password())

    def test_les_endpoints_google_n_ont_pas_deplace_les_routes_existantes(self):
        self.assertEqual(reverse("login"), "/api/v1/auth/login/")
        self.assertEqual(reverse("auth-me"), "/api/v1/auth/me/")
        self.assertEqual(reverse("google-login"), "/api/v1/auth/google/login/")
        self.assertEqual(reverse("google-callback"), "/api/v1/auth/google/callback/")


# ═══════════════════ Admin : visibilité sans exposition ══════════════════════
class AdminGoogleTests(TestCase):

    def test_l_admin_voit_la_liaison_sans_pouvoir_la_creer_ni_la_modifier(self):
        """Cahier des charges — l'admin voit utilisateur, fournisseur, email, date."""
        from django.contrib import admin as django_admin

        from users.admin import GoogleAccountAdmin

        instance = django_admin.site._registry[GoogleAccount]
        self.assertIsInstance(instance, GoogleAccountAdmin)
        self.assertFalse(instance.has_add_permission(None))
        self.assertFalse(instance.has_change_permission(None))
        for colonne in ("telephone_kharandi", "fournisseur", "email", "linked_at"):
            self.assertIn(colonne, instance.list_display)
        # Aucun jeton ni secret n'est stocké, donc rien de tel n'est affichable.
        champs = {c.name for c in GoogleAccount._meta.get_fields()}
        for interdit in ("access_token", "refresh_token", "client_secret", "id_token"):
            self.assertNotIn(interdit, champs)
