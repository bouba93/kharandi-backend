"""
users/kyc_views.py — Dépôt et suivi du dossier KYC répétiteur
─────────────────────────────────────────────────────────────
Endpoints ajoutés (aucun endpoint existant n'est modifié) :

    GET  /api/v1/auth/kyc/tutor/   → état de MON dossier
    POST /api/v1/auth/kyc/tutor/   → déposer / corriger MON dossier (multipart)

Contrat de sécurité
───────────────────
  - `IsAuthenticated` : jamais public ;
  - réservé au rôle TUTOR (un élève n'a pas de KYC répétiteur) ;
  - un utilisateur ne voit et ne modifie QUE son propre dossier
    (aucun paramètre d'identifiant n'est accepté → pas d'IDOR possible) ;
  - un dossier APPROVED est verrouillé : seul un admin peut le rouvrir ;
  - la réponse ne contient jamais d'URL de document.
"""
import logging

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.utils import API_EXCEPTIONS, error_response, success_response
from .kyc_serializers import TutorKYCStatusSerializer, TutorKYCSubmitSerializer
from .models import TutorKYC

logger = logging.getLogger(__name__)


class TutorKYCView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        dossier = TutorKYC.objects.filter(user=request.user).first()
        if not dossier:
            return success_response(
                data={"status": None, "documents_recus": {}},
                message="Aucun dossier KYC déposé.",
            )
        return success_response(data=TutorKYCStatusSerializer(dossier).data)

    def post(self, request):
        try:
            if request.user.role != "TUTOR":
                return error_response(
                    "Le KYC est réservé aux comptes répétiteur.", status=403
                )

            dossier = TutorKYC.objects.filter(user=request.user).first()
            if dossier and dossier.status == TutorKYC.Status.APPROVED:
                return error_response(
                    "Votre dossier est déjà validé. Contactez le support pour "
                    "toute modification.",
                    status=409,
                )

            s = TutorKYCSubmitSerializer(dossier, data=request.data,
                                         partial=bool(dossier))
            s.is_valid(raise_exception=True)

            nouveau = dossier is None
            dossier = s.save(user=request.user)

            # Une correction après refus repasse le dossier en attente.
            if dossier.status != TutorKYC.Status.PENDING:
                dossier.status = TutorKYC.Status.PENDING
                dossier.rejection_reason = ""
                dossier.reviewed_at = None
                dossier.reviewed_by = None
                dossier.save(update_fields=["status", "rejection_reason",
                                            "reviewed_at", "reviewed_by",
                                            "updated_at"])
            dossier._synchroniser_profil()

            logger.info("KYC répétiteur %s : dossier %s (statut PENDING).",
                        request.user.phone, "déposé" if nouveau else "mis à jour")
            return success_response(
                data=TutorKYCStatusSerializer(dossier).data,
                message="Dossier reçu. Il sera examiné par l'équipe Kharandi.",
                status=201 if nouveau else 200,
            )
        except API_EXCEPTIONS:
            raise
