import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

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
