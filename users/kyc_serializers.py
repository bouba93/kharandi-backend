"""
users/kyc_serializers.py — Sérialiseurs du KYC répétiteur
─────────────────────────────────────────────────────────
Règle de sécurité appliquée ici : AUCUN sérialiseur n'expose l'URL ni le
contenu d'un document KYC. Le répétiteur reçoit uniquement l'état de son
dossier (déposé / en attente / approuvé / refusé + motif). Les fichiers ne se
consultent que depuis l'admin authentifié.
"""
from rest_framework import serializers

from .models import TutorKYC


class TutorKYCSubmitSerializer(serializers.ModelSerializer):
    """Dépôt / mise à jour d'un dossier (écriture seule).

    Les champs de décision (`status`, `reviewed_by`, `reviewed_at`,
    `rejection_reason`, `admin_notes`) sont volontairement ABSENTS : un
    répétiteur ne peut en aucun cas s'auto-approuver via l'API.
    """

    class Meta:
        model = TutorKYC
        fields = [
            "full_name", "document_type", "document_number", "birth_date",
            "address", "diploma", "experience_years",
            "document_front", "document_back", "selfie", "diploma_file",
        ]

    def validate_full_name(self, valeur):
        valeur = (valeur or "").strip()
        if len(valeur) < 3:
            raise serializers.ValidationError("Nom complet invalide.")
        return valeur


class TutorKYCStatusSerializer(serializers.ModelSerializer):
    """Lecture par le répétiteur : état du dossier, jamais les fichiers."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    documents_recus = serializers.SerializerMethodField()

    class Meta:
        model = TutorKYC
        fields = [
            "status", "status_label", "submitted_at", "reviewed_at",
            "rejection_reason", "documents_recus",
        ]
        read_only_fields = fields

    def get_documents_recus(self, obj):
        """Booléens uniquement : aucune URL, aucun nom de fichier."""
        return {
            "recto": bool(obj.document_front),
            "verso": bool(obj.document_back),
            "selfie": bool(obj.selfie),
            "diplome": bool(obj.diploma_file),
        }
