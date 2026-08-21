"""
users/kyc_storage.py — Stockage PRIVÉ des pièces d'identité KYC
───────────────────────────────────────────────────────────────
Pourquoi un stockage dédié
──────────────────────────
1. Nginx sert `/media/` en fichiers statiques publics
   (nginx/kharandi.conf : `location /media/ { alias /app/media/; }`).
   Un document KYC déposé dans MEDIA_ROOT serait donc téléchargeable par
   n'importe qui connaissant l'URL — inacceptable pour une pièce d'identité.
2. Quand `USE_CLOUDINARY=1`, le `DEFAULT_FILE_STORAGE` est Cloudinary, qui
   génère des URLs publiques. Les pièces KYC ne doivent JAMAIS y partir.

Solution retenue (minimale, sans nouveau volume Docker)
───────────────────────────────────────────────────────
Les fichiers sont écrits dans `<MEDIA_ROOT>/private/kyc/…` — donc dans le
volume `media_data` déjà persistant et déjà sauvegardé — et l'accès HTTP direct
à `/media/private/` est explicitement refusé par Nginx (voir nginx/kharandi.conf).
`base_url=None` : le champ FileField n'expose aucune URL publique ; la seule
façon de lire un document est la vue admin authentifiée
`users.admin.KYCDocumentView` (staff + permission `users.view_tutorkyc`).

Défense en profondeur : 4 couches indépendantes
  - nom de fichier non deviné (UUID) ;
  - Nginx refuse /media/private/ ;
  - aucune URL n'est jamais sérialisée dans l'API ;
  - téléchargement réservé au staff autorisé.
"""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.functional import cached_property

# Extensions et types acceptés : une pièce d'identité est une image ou un PDF.
EXTENSIONS_KYC_AUTORISEES = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
TYPES_MIME_KYC_AUTORISES = {
    "image/jpeg", "image/png", "image/webp", "application/pdf",
}
TAILLE_MAX_KYC = 5 * 1024 * 1024  # 5 Mo


class StockagePriveKYC(FileSystemStorage):
    """Système de fichiers local, hors de portée d'Internet, sans URL publique."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_url", None)
        # 0o600 / 0o700 : lisible seulement par l'utilisateur du conteneur.
        kwargs.setdefault("file_permissions_mode", 0o600)
        kwargs.setdefault("directory_permissions_mode", 0o700)
        super().__init__(*args, **kwargs)

    @cached_property
    def base_location(self):
        """Résolution TARDIVE de MEDIA_ROOT.

        Calculer le chemin ici (et non dans `__init__`) permet à
        `override_settings(MEDIA_ROOT=…)` d'être respecté dans les tests :
        Django efface ce cache au changement de réglage. Aucun test n'écrit
        donc dans le volume `media_data` réel.
        """
        return os.path.join(settings.MEDIA_ROOT, "private")

    def url(self, name):  # pragma: no cover - sécurité
        raise ValueError(
            "Les documents KYC n'ont pas d'URL publique. Utiliser la vue admin "
            "sécurisée (users.admin.KYCDocumentView)."
        )


def stockage_kyc():
    """Fabrique de stockage (callable).

    On passe une FONCTION à `FileField(storage=...)` plutôt qu'une instance :
    Django sérialise alors une simple référence dans la migration, et le chemin
    est résolu au moment de l'exécution avec le `MEDIA_ROOT` réel du conteneur.
    Une instance figée serait, elle, gelée dans le fichier de migration.
    """
    return StockagePriveKYC()


def chemin_document_kyc(instance, filename):
    """Nom de fichier imprévisible : aucune énumération possible.

    Résultat : `kyc/<uuid-utilisateur>/<uuid4><extension>`
    On ne conserve PAS le nom d'origine (il peut contenir le nom réel de la
    personne, des caractères de traversée de répertoire, etc.).
    """
    extension = os.path.splitext(filename)[1].lower()
    if extension not in EXTENSIONS_KYC_AUTORISEES:
        extension = ".bin"
    dossier = getattr(instance, "user_id", None) or "inconnu"
    return f"kyc/{dossier}/{uuid.uuid4().hex}{extension}"


# Signatures binaires (« magic bytes ») des seuls formats acceptés. Le type MIME
# annoncé par le navigateur est déclaratif : il se falsifie trivialement. On
# vérifie donc aussi les premiers octets du fichier réellement envoyé.
SIGNATURES_KYC = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"\xff\xd8\xff",        # JPEG
    b"%PDF",                # PDF
)


def _signature_acceptable(entete: bytes) -> bool:
    if any(entete.startswith(s) for s in SIGNATURES_KYC):
        return True
    # WEBP : "RIFF" + 4 octets de taille + "WEBP"
    return entete[:4] == b"RIFF" and entete[8:12] == b"WEBP"


def valider_document_kyc(fichier):
    """Validateur de champ : taille, extension, type MIME déclaré, signature."""
    if fichier is None:
        return
    taille = getattr(fichier, "size", 0) or 0
    if taille > TAILLE_MAX_KYC:
        raise ValidationError(
            "Fichier trop volumineux (%(taille).1f Mo). Maximum autorisé : 5 Mo.",
            params={"taille": taille / (1024 * 1024)},
        )
    nom = getattr(fichier, "name", "") or ""
    extension = os.path.splitext(nom)[1].lower()
    if extension not in EXTENSIONS_KYC_AUTORISEES:
        raise ValidationError(
            "Format non accepté. Formats autorisés : JPG, PNG, WEBP, PDF."
        )
    type_mime = getattr(getattr(fichier, "file", None), "content_type", None) or \
        getattr(fichier, "content_type", None)
    if type_mime and type_mime not in TYPES_MIME_KYC_AUTORISES:
        raise ValidationError(
            "Type de fichier non accepté (%(type)s). Envoyez une image ou un PDF.",
            params={"type": type_mime},
        )

    # Contrôle du contenu réel. Enveloppé dans un try/except : si le fichier
    # n'est pas relisible (champ déjà enregistré, stockage distant), on ne
    # bloque pas un enregistrement par ailleurs valide.
    try:
        position = fichier.tell() if hasattr(fichier, "tell") else None
        if hasattr(fichier, "seek"):
            fichier.seek(0)
        entete = fichier.read(12) or b""
        if hasattr(fichier, "seek"):
            fichier.seek(position or 0)
    except (OSError, ValueError, AttributeError):
        return
    if entete and not _signature_acceptable(entete):
        raise ValidationError(
            "Le contenu du fichier ne correspond pas à une image ou à un PDF "
            "valide. Envoyez la photo originale de votre pièce."
        )
