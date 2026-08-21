import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .kyc_storage import (
    chemin_document_kyc, stockage_kyc, valider_document_kyc,
)

class UserManager(BaseUserManager):
    def create_user(self, phone, **extra_fields):
        if not phone: raise ValueError("Le téléphone est obligatoire.")
        user = self.model(phone=phone, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff",    True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role",         "ADMIN")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Élève"
        TUTOR   = "TUTOR",   "Tuteur"
        PARENT  = "PARENT",  "Parent"
        VENDOR  = "VENDOR",  "Vendeur"
        ADMIN   = "ADMIN",   "Administrateur"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone       = models.CharField(max_length=20, unique=True, db_index=True)
    role        = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD  = "phone"
    REQUIRED_FIELDS = []

    class Meta: verbose_name = "Utilisateur"
    def __str__(self): return self.phone


class Profile(models.Model):
    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name           = models.CharField(max_length=100, blank=True)
    last_name            = models.CharField(max_length=100, blank=True)
    avatar               = models.ImageField(upload_to="avatars/", blank=True, null=True)
    school_level         = models.CharField(max_length=50,  blank=True)
    birth_date           = models.DateField(null=True, blank=True)
    city                 = models.CharField(max_length=100, blank=True)
    bio                  = models.TextField(blank=True)
    niveau               = models.CharField(max_length=50, blank=True)
    serie                = models.CharField(max_length=30, blank=True)
    parent               = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="children_profiles",
    )
    display_name          = models.CharField(max_length=150, blank=True)
    tutor_status          = models.CharField(max_length=20, blank=True)
    tutor_subjects        = models.JSONField(default=list, blank=True)
    tutor_levels          = models.JSONField(default=list, blank=True)
    tutor_zone            = models.CharField(max_length=150, blank=True)
    shop_name             = models.CharField(max_length=150, blank=True)
    shop_description      = models.TextField(blank=True)
    delivery_zone         = models.CharField(max_length=150, blank=True)
    shop_status           = models.CharField(max_length=20, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    points               = models.PositiveIntegerField(default=0,
                           help_text="Points Kharandi Makiti — 1 point = 100 GNF")
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    def __str__(self): return f"Profil de {self.user.phone}"

    @property
    def points_in_gnf(self):
        """1 point = 100 GNF."""
        return (self.points or 0) * 100


class OTPRecord(models.Model):
    phone          = models.CharField(max_length=20, db_index=True)
    verificationid = models.CharField(max_length=100, blank=True)
    sent_at        = models.DateTimeField(auto_now_add=True)
    verified       = models.BooleanField(default=False)
    expires_at     = models.DateTimeField()

    class Meta:
        verbose_name = "OTP"
        ordering     = ["-sent_at"]
    def __str__(self): return f"OTP({self.phone})"


class UserDevice(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    device_token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    user_agent   = models.TextField(blank=True)
    last_ip      = models.GenericIPAddressField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    last_used    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_used"]

    def __str__(self):
        return f"{self.user.phone} — {str(self.device_token)[:8]}..."


class PointTransaction(models.Model):
    """
    Historique wallet — toutes les transactions de points Kharandi Makiti.
    CREDIT → points gagnés (exercice, bonus)
    DEBIT  → points dépensés (achat marketplace)
    1 point = 100 GNF
    """
    class Type(models.TextChoices):
        CREDIT = "CREDIT", "Crédit"
        DEBIT  = "DEBIT",  "Débit"

    class Source(models.TextChoices):
        EXERCISE    = "EXERCISE",    "Exercice QCM"
        MARKETPLACE = "MARKETPLACE", "Achat Marketplace"
        ADMIN       = "ADMIN",       "Ajustement Admin"
        BONUS       = "BONUS",       "Bonus"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="point_transactions")
    type          = models.CharField(max_length=6,  choices=Type.choices)
    source        = models.CharField(max_length=15, choices=Source.choices, default=Source.EXERCISE)
    points        = models.PositiveIntegerField()
    balance_after = models.PositiveIntegerField(default=0)
    description   = models.CharField(max_length=255)
    reference     = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["-created_at"]
        verbose_name = "Transaction de points"

    def __str__(self):
        sign = "+" if self.type == self.Type.CREDIT else "-"
        return f"{self.user.phone} {sign}{self.points}pts — {self.description}"


# ─── KYC des répétiteurs (vérification d'identité) ───────────────────────────
class TutorKYC(models.Model):
    """Dossier de vérification d'identité d'un répétiteur.

    Choix d'architecture
    ────────────────────
    Le statut de validation d'un répétiteur EXISTE DÉJÀ dans le projet :
    `Profile.tutor_status`, mis à « PENDING » par
    `users.views.RegisterRepetiteurView` et exposé au frontend par
    `ProfileSerializer`. On ne crée donc AUCUN champ concurrent : ce modèle
    porte uniquement les pièces justificatives et la traçabilité de l'examen,
    et c'est lui qui MET À JOUR `Profile.tutor_status` lors de la décision
    (méthodes `approve()` / `reject()`). `Profile.tutor_status` reste la seule
    source de vérité lue par l'API et le frontend.

    Un seul dossier par utilisateur (OneToOne) : un répétiteur qui corrige son
    dossier refusé remplace ses fichiers, il ne crée pas un second dossier.
    """

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "En attente"
        APPROVED = "APPROVED", "Approuvé"
        REJECTED = "REJECTED", "Refusé"

    class DocumentType(models.TextChoices):
        CNI       = "CNI",       "Carte nationale d'identité"
        PASSEPORT = "PASSEPORT", "Passeport"
        PERMIS    = "PERMIS",    "Permis de conduire"
        CARTE_ETU = "CARTE_ETU", "Carte d'étudiant"

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="tutor_kyc",
        verbose_name="Répétiteur",
    )

    full_name     = models.CharField("Nom complet (tel qu'écrit sur la pièce)", max_length=150)
    document_type = models.CharField("Type de pièce", max_length=12,
                                     choices=DocumentType.choices,
                                     default=DocumentType.CNI)
    document_number = models.CharField("Numéro de la pièce", max_length=50, blank=True)
    birth_date    = models.DateField("Date de naissance", null=True, blank=True)
    address       = models.CharField("Adresse / quartier", max_length=255, blank=True)
    diploma       = models.CharField("Diplôme le plus élevé", max_length=150, blank=True)
    experience_years = models.PositiveSmallIntegerField("Années d'expérience", default=0)

    # Fichiers : stockage PRIVÉ (voir users/kyc_storage.py). Jamais servis par
    # Nginx, jamais exposés dans l'API.
    document_front = models.FileField(
        "Pièce d'identité (recto)",
        upload_to=chemin_document_kyc, storage=stockage_kyc,
        validators=[valider_document_kyc],
    )
    document_back = models.FileField(
        "Pièce d'identité (verso)",
        upload_to=chemin_document_kyc, storage=stockage_kyc,
        validators=[valider_document_kyc], blank=True, null=True,
    )
    selfie = models.FileField(
        "Photo du visage (selfie)",
        upload_to=chemin_document_kyc, storage=stockage_kyc,
        validators=[valider_document_kyc], blank=True, null=True,
    )
    diploma_file = models.FileField(
        "Justificatif de diplôme",
        upload_to=chemin_document_kyc, storage=stockage_kyc,
        validators=[valider_document_kyc], blank=True, null=True,
    )

    status = models.CharField("Statut", max_length=10, choices=Status.choices,
                             default=Status.PENDING, db_index=True)
    submitted_at = models.DateTimeField("Déposé le", default=timezone.now)
    reviewed_at  = models.DateTimeField("Examiné le", null=True, blank=True)
    reviewed_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kyc_reviewed", verbose_name="Examiné par",
    )
    rejection_reason = models.TextField("Motif du refus", blank=True)
    admin_notes = models.TextField("Notes internes (non visibles du répétiteur)", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Dossier KYC répétiteur"
        verbose_name_plural = "Dossiers KYC répétiteurs"
        indexes = [models.Index(fields=["status", "-submitted_at"])]

    def __str__(self):
        return f"KYC {self.user.phone} — {self.get_status_display()}"

    # ── Transitions métier ──────────────────────────────────────────────────
    # Un dossier déjà approuvé n'est jamais réécrit silencieusement : les deux
    # méthodes refusent l'opération et l'admin affiche un avertissement.
    def approve(self, par_admin=None):
        if self.status == self.Status.APPROVED:
            return False
        self.status = self.Status.APPROVED
        self.rejection_reason = ""
        self.reviewed_at = timezone.now()
        self.reviewed_by = par_admin
        self.save(update_fields=["status", "rejection_reason", "reviewed_at",
                                 "reviewed_by", "updated_at"])
        self._synchroniser_profil()
        return True

    def reject(self, motif="", par_admin=None):
        if self.status == self.Status.APPROVED:
            # Retirer une validation est une opération sensible : elle se fait
            # explicitement en modifiant le dossier, pas par une action de masse.
            return False
        self.status = self.Status.REJECTED
        self.rejection_reason = motif or self.rejection_reason
        self.reviewed_at = timezone.now()
        self.reviewed_by = par_admin
        self.save(update_fields=["status", "rejection_reason", "reviewed_at",
                                 "reviewed_by", "updated_at"])
        self._synchroniser_profil()
        return True

    def _synchroniser_profil(self):
        """Reporte le statut sur `Profile.tutor_status` (source de vérité API)."""
        profil = getattr(self.user, "profile", None)
        if profil is None:
            return
        if profil.tutor_status != self.status:
            profil.tutor_status = self.status
            profil.save(update_fields=["tutor_status", "updated_at"])


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTIFICATION GOOGLE (OpenID Connect) — 100 % ADDITIF
# ══════════════════════════════════════════════════════════════════════════════
#  Aucun champ n'est ajouté, renommé ou supprimé sur `User` ni sur `Profile`.
#  Google est une MÉTHODE D'AUTHENTIFICATION SUPPLÉMENTAIRE : la source de
#  vérité de l'identité reste `User.phone`, unique, vérifié par OTP.
#
#  Trois tables nouvelles, indépendantes du reste du schéma :
#    - GoogleAccount     : liaison durable « compte Kharandi ↔ compte Google » ;
#    - GoogleOAuthState  : état éphémère d'un flux OAuth (state / nonce / PKCE) ;
#    - GoogleAuthTicket  : jeton opaque à usage unique remis au frontend après
#                          le callback, pour ne JAMAIS faire circuler un JWT
#                          dans une URL de redirection ou un deep link.
# ══════════════════════════════════════════════════════════════════════════════

class GoogleAccount(models.Model):
    """Liaison entre un `User` Kharandi et un compte Google.

    La clé d'identité est `google_sub` (identifiant stable et non réutilisable
    fourni par Google), JAMAIS l'email : l'email Google est conservé à titre
    informatif pour l'admin et n'est utilisé pour aucun rapprochement de compte.
    """

    PROVIDER = "google"

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="google_account",
        verbose_name="utilisateur Kharandi",
    )
    google_sub = models.CharField(
        max_length=255, unique=True, db_index=True,
        verbose_name="identifiant Google (sub)",
    )
    email = models.EmailField(blank=True, verbose_name="email Google")
    email_verified = models.BooleanField(default=False, verbose_name="email vérifié par Google")
    given_name = models.CharField(max_length=150, blank=True, verbose_name="prénom Google")
    family_name = models.CharField(max_length=150, blank=True, verbose_name="nom Google")
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name="date de liaison")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="dernière connexion Google")

    class Meta:
        verbose_name = "compte Google lié"
        verbose_name_plural = "comptes Google liés"
        ordering = ("-linked_at",)

    def __str__(self):
        return f"Google · {self.user.phone}"

    def marquer_utilise(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])


class GoogleOAuthState(models.Model):
    """État éphémère d'un flux OAuth 2.0 / OIDC, à usage unique.

    Contient le `state` (anti-CSRF), le `nonce` (anti-rejeu de l'id_token) et le
    `code_verifier` PKCE. Ces valeurs restent exclusivement côté serveur : le
    navigateur ne voit que le `state`.
    """

    state = models.CharField(max_length=128, unique=True, db_index=True)
    nonce = models.CharField(max_length=128)
    code_verifier = models.CharField(max_length=128)
    platform = models.CharField(max_length=16, default="web")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "état OAuth Google"
        verbose_name_plural = "états OAuth Google"
        ordering = ("-created_at",)

    def est_utilisable(self):
        return self.used_at is None and timezone.now() <= self.expires_at

    def consommer(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class GoogleAuthTicket(models.Model):
    """Jeton opaque remis au frontend à la fin du flux Google.

    Deux natures :
      - LOGIN  : l'identité Google est déjà liée à un compte Kharandi. Le
                 frontend échange le ticket contre les JWT Kharandi habituels.
      - SIGNUP : l'identité Google est vérifiée mais aucun compte Kharandi n'y
                 est rattaché. Le ticket ne donne AUCUN accès : il doit être
                 complété par un téléphone vérifié par OTP et un rôle choisi.

    Seul le SHA-256 du code est stocké : une fuite de base ne permet pas de
    rejouer un ticket.
    """

    class Kind(models.TextChoices):
        LOGIN = "LOGIN", "Connexion"
        SIGNUP = "SIGNUP", "Inscription à compléter"

    code_hash = models.CharField(max_length=64, unique=True, db_index=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, null=True, blank=True,
        related_name="google_tickets",
    )
    google_sub = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    email_verified = models.BooleanField(default=False)
    given_name = models.CharField(max_length=150, blank=True)
    family_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "ticket d'authentification Google"
        verbose_name_plural = "tickets d'authentification Google"
        ordering = ("-created_at",)

    def est_utilisable(self):
        return self.used_at is None and timezone.now() <= self.expires_at

    def consommer(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
