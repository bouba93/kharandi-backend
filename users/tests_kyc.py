"""
users/tests_kyc.py — KYC répétiteurs (dépôt API + validation Django Admin)
─────────────────────────────────────────────────────────────────────────
Ce que ces tests garantissent :

  Parcours   dépôt → PENDING → décision admin → APPROVED / REJECTED ;
  Réutilisation  `Profile.tutor_status` existant est mis à jour (aucun champ
                 concurrent) ;
  Sécurité   pas d'accès anonyme, pas d'auto-approbation via l'API, aucune URL
             de document exposée, fichiers hors du répertoire public,
             validation du type et de la taille, nom de fichier assaini ;
  Intégrité  un dossier APPROVED n'est pas écrasable par le répétiteur.

Exécution :
    docker compose exec api python manage.py test users.tests_kyc -v 2
"""
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .kyc_storage import valider_document_kyc
from .models import Profile, TutorKYC

User = get_user_model()

URL = "/api/v1/auth/kyc/tutor/"

# En-tête PNG minimale : le validateur contrôle aussi le type MIME réel.
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
       b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")


def _fichier(nom="cni.png", contenu=PNG, type_mime="image/png"):
    return SimpleUploadedFile(nom, contenu, content_type=type_mime)


def _dossier_valide(**extra):
    donnees = {
        "full_name": "Mamadou Diallo",
        "document_type": "CNI",
        "document_number": "GN-123456",
        "address": "Ratoma, Conakry",
        "diploma": "Licence Mathématiques",
        "experience_years": 3,
        "document_front": _fichier(),
    }
    donnees.update(extra)
    return donnees


# MEDIA_ROOT temporaire : les tests n'écrivent JAMAIS dans le volume réel.
_MEDIA_TEST = tempfile.mkdtemp(prefix="kharandi-kyc-tests-")


@override_settings(
    MEDIA_ROOT=_MEDIA_TEST,
    RATE_LIMIT_ENABLED=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class DepotKYCTests(TestCase):
    def setUp(self):
        self.repetiteur = User.objects.create_user(phone="+224622333444", role="TUTOR")
        self.eleve = User.objects.create_user(phone="+224622555666", role="STUDENT")
        self.client = APIClient()
        self.client.force_authenticate(user=self.repetiteur)

    # ── Parcours nominal ────────────────────────────────────────────────────
    def test_depot_cree_un_dossier_en_attente(self):
        r = self.client.post(URL, _dossier_valide(), format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        dossier = TutorKYC.objects.get(user=self.repetiteur)
        self.assertEqual(dossier.status, TutorKYC.Status.PENDING)
        self.assertIsNotNone(dossier.submitted_at)
        self.assertIsNone(dossier.reviewed_at)
        self.assertIsNone(dossier.reviewed_by)

    def test_le_statut_est_reporte_sur_le_profil_existant(self):
        """Réutilisation de `Profile.tutor_status` (pas de champ concurrent)."""
        self.client.post(URL, _dossier_valide(), format="multipart")
        profil = Profile.objects.get(user=self.repetiteur)
        self.assertEqual(profil.tutor_status, "PENDING")

    def test_le_repetiteur_peut_consulter_son_etat(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["data"]["status"], "PENDING")
        self.assertTrue(r.data["data"]["documents_recus"]["recto"])

    def test_sans_dossier_l_etat_est_vide_et_non_404(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["data"]["status"])

    def test_correction_apres_refus_repasse_en_attente(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        dossier = TutorKYC.objects.get(user=self.repetiteur)
        dossier.reject("Photo illisible")
        self.assertEqual(dossier.status, TutorKYC.Status.REJECTED)

        r = self.client.post(URL, {"document_front": _fichier("cni2.png")},
                             format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        dossier.refresh_from_db()
        self.assertEqual(dossier.status, TutorKYC.Status.PENDING)
        self.assertEqual(dossier.rejection_reason, "")
        self.assertIsNone(dossier.reviewed_at)

    def test_un_dossier_approuve_n_est_pas_ecrasable(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        dossier = TutorKYC.objects.get(user=self.repetiteur)
        dossier.approve()
        chemin_initial = dossier.document_front.name

        r = self.client.post(URL, {"document_front": _fichier("autre.png")},
                             format="multipart")
        self.assertEqual(r.status_code, 409, r.data)
        dossier.refresh_from_db()
        self.assertEqual(dossier.document_front.name, chemin_initial)
        self.assertEqual(dossier.status, TutorKYC.Status.APPROVED)

    def test_un_seul_dossier_par_repetiteur(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        self.client.post(URL, _dossier_valide(), format="multipart")
        self.assertEqual(TutorKYC.objects.filter(user=self.repetiteur).count(), 1)

    # ── Sécurité ────────────────────────────────────────────────────────────
    def test_acces_anonyme_refuse(self):
        anonyme = APIClient()
        self.assertIn(anonyme.get(URL).status_code, (401, 403))
        self.assertIn(
            anonyme.post(URL, _dossier_valide(), format="multipart").status_code,
            (401, 403),
        )

    def test_un_eleve_ne_peut_pas_deposer_de_kyc_repetiteur(self):
        self.client.force_authenticate(user=self.eleve)
        r = self.client.post(URL, _dossier_valide(), format="multipart")
        self.assertEqual(r.status_code, 403, r.data)
        self.assertFalse(TutorKYC.objects.exists())

    def test_impossible_de_s_auto_approuver_via_l_api(self):
        r = self.client.post(
            URL,
            _dossier_valide(status="APPROVED", reviewed_by=self.repetiteur.id,
                            rejection_reason="", admin_notes="ok"),
            format="multipart",
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(
            TutorKYC.objects.get(user=self.repetiteur).status,
            TutorKYC.Status.PENDING,
        )

    def test_aucune_url_de_document_dans_la_reponse_api(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        corps = self.client.get(URL).content.decode()
        for interdit in ["/media/", "http://", "https://", ".png", "kyc/"]:
            self.assertNotIn(interdit, corps, f"fuite possible : « {interdit} »")

    def test_un_repetiteur_ne_voit_pas_le_dossier_d_un_autre(self):
        autre = User.objects.create_user(phone="+224622777888", role="TUTOR")
        TutorKYC.objects.create(user=autre, full_name="Autre Personne",
                                document_front=_fichier("x.png"))
        r = self.client.get(URL)
        self.assertIsNone(r.data["data"]["status"])

    def test_les_fichiers_sont_stockes_hors_du_repertoire_public(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        dossier = TutorKYC.objects.get(user=self.repetiteur)
        chemin = Path(dossier.document_front.path).resolve()
        prive = (Path(settings.MEDIA_ROOT) / "private").resolve()
        self.assertTrue(str(chemin).startswith(str(prive)), chemin)
        # Le nom de fichier est réécrit en UUID : aucun nom fourni par le client.
        self.assertNotIn("cni", dossier.document_front.name)
        self.assertIn(str(self.repetiteur.id), dossier.document_front.name)

    def test_le_stockage_prive_refuse_de_fabriquer_une_url(self):
        self.client.post(URL, _dossier_valide(), format="multipart")
        dossier = TutorKYC.objects.get(user=self.repetiteur)
        with self.assertRaises(Exception):
            dossier.document_front.url  # noqa: B018

    # ── Validation des fichiers ─────────────────────────────────────────────
    def test_extension_interdite_refusee(self):
        r = self.client.post(
            URL,
            _dossier_valide(document_front=_fichier("virus.exe", b"MZ...",
                                                    "application/octet-stream")),
            format="multipart",
        )
        self.assertEqual(r.status_code, 400, r.data)
        self.assertFalse(TutorKYC.objects.exists())

    def test_fichier_trop_volumineux_refuse(self):
        gros = _fichier("gros.png", PNG + b"\x00" * (6 * 1024 * 1024))
        r = self.client.post(URL, _dossier_valide(document_front=gros),
                             format="multipart")
        self.assertEqual(r.status_code, 400, r.data)

    def test_extension_maquillee_refusee(self):
        """.png annoncé mais contenu non-image → refus (contrôle MIME réel)."""
        with self.assertRaises(ValidationError):
            valider_document_kyc(_fichier("faux.png", b"#!/bin/sh\nrm -rf /",
                                          "image/png"))

    def test_le_pdf_est_accepte(self):
        pdf = _fichier("diplome.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF",
                       "application/pdf")
        r = self.client.post(URL, _dossier_valide(diploma_file=pdf),
                             format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(TutorKYC.objects.get(user=self.repetiteur).diploma_file)


@override_settings(
    MEDIA_ROOT=_MEDIA_TEST,
    RATE_LIMIT_ENABLED=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ValidationAdminKYCTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone="+224620000001", password="MotDePasseAdmin123"
        )
        self.repetiteur = User.objects.create_user(phone="+224622333444", role="TUTOR")
        self.dossier = TutorKYC.objects.create(
            user=self.repetiteur, full_name="Mamadou Diallo",
            document_front=_fichier(),
        )
        self.client.force_login(self.admin)

    # ── Décision ────────────────────────────────────────────────────────────
    def test_approbation_renseigne_le_validateur_et_la_date(self):
        self.dossier.approve(par_admin=self.admin)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.status, TutorKYC.Status.APPROVED)
        self.assertEqual(self.dossier.reviewed_by, self.admin)
        self.assertIsNotNone(self.dossier.reviewed_at)
        self.assertEqual(
            Profile.objects.get(user=self.repetiteur).tutor_status, "APPROVED"
        )

    def test_refus_enregistre_le_motif(self):
        self.dossier.reject("Document expiré", par_admin=self.admin)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.status, TutorKYC.Status.REJECTED)
        self.assertEqual(self.dossier.rejection_reason, "Document expiré")
        self.assertEqual(
            Profile.objects.get(user=self.repetiteur).tutor_status, "REJECTED"
        )

    def test_un_dossier_approuve_ne_peut_pas_etre_refuse_par_le_modele(self):
        self.dossier.approve(par_admin=self.admin)
        self.dossier.reject("Erreur", par_admin=self.admin)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.status, TutorKYC.Status.APPROVED)

    # ── Pages d'administration ──────────────────────────────────────────────
    def test_liste_admin_accessible(self):
        r = self.client.get("/admin/users/tutorkyc/")
        self.assertEqual(r.status_code, 200)

    def test_filtre_par_statut_accessible(self):
        r = self.client.get("/admin/users/tutorkyc/?status__exact=PENDING")
        self.assertEqual(r.status_code, 200)

    def test_recherche_admin_accessible(self):
        r = self.client.get("/admin/users/tutorkyc/?q=Diallo")
        self.assertEqual(r.status_code, 200)

    def test_fiche_admin_accessible(self):
        r = self.client.get(f"/admin/users/tutorkyc/{self.dossier.pk}/change/")
        self.assertEqual(r.status_code, 200)

    def test_ajout_manuel_interdit_dans_l_admin(self):
        r = self.client.get("/admin/users/tutorkyc/add/")
        self.assertIn(r.status_code, (403, 302))

    def test_actions_groupees_disponibles(self):
        from django.contrib import admin
        from .models import TutorKYC as M
        actions = admin.site._registry[M].get_actions(
            type("R", (), {"user": self.admin, "GET": {}})()
        )
        self.assertIn("approuver_dossiers", actions)
        self.assertIn("refuser_dossiers", actions)

    def test_action_groupee_approuve_et_trace_le_validateur(self):
        r = self.client.post(
            "/admin/users/tutorkyc/",
            {"action": "approuver_dossiers",
             "_selected_action": [str(self.dossier.pk)]},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.status, TutorKYC.Status.APPROVED)
        self.assertEqual(self.dossier.reviewed_by, self.admin)

    # ── Consultation des pièces ─────────────────────────────────────────────
    def test_le_telechargement_admin_sert_le_document(self):
        r = self.client.get(
            f"/admin/users/tutorkyc/{self.dossier.pk}/document/document_front/"
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("no-store", r.headers.get("Cache-Control", ""))

    def test_le_telechargement_est_refuse_a_un_non_staff(self):
        self.client.logout()
        self.client.force_login(self.repetiteur)
        r = self.client.get(
            f"/admin/users/tutorkyc/{self.dossier.pk}/document/document_front/"
        )
        self.assertIn(r.status_code, (302, 403))

    def test_le_telechargement_est_refuse_a_un_anonyme(self):
        self.client.logout()
        r = self.client.get(
            f"/admin/users/tutorkyc/{self.dossier.pk}/document/document_front/"
        )
        self.assertIn(r.status_code, (302, 403))

    def test_champ_inconnu_refuse_au_telechargement(self):
        r = self.client.get(
            f"/admin/users/tutorkyc/{self.dossier.pk}/document/admin_notes/"
        )
        self.assertIn(r.status_code, (400, 404))
