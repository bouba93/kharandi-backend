import uuid
from django.db import models
from django.utils import timezone


class School(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=200)
    email        = models.EmailField(unique=True)
    code         = models.CharField(max_length=20, unique=True)
    password_hash= models.CharField(max_length=255, blank=True)
    is_activated = models.BooleanField(default=False)
    logo_url     = models.URLField(blank=True)
    phone        = models.CharField(max_length=20, blank=True)
    address      = models.TextField(blank=True)
    subscription_active = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def check_password(self, raw):
        from django.contrib.auth.hashers import check_password
        return check_password(raw, self.password_hash)

    def set_password(self, raw):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw)


class SchoolSubscription(models.Model):
    """Abonnement annuel d'un établissement scolaire."""

    class Status(models.TextChoices):
        PENDING  = "pending",  "En attente"
        ACTIVE   = "active",   "Actif"
        EXPIRED  = "expired",  "Expiré"
        CANCELED = "canceled", "Annulé"

    class PaymentMethod(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MONEY    = "mtn_money",    "MTN Mobile Money"
        CARD         = "card",         "Carte bancaire"
        CASH         = "cash",         "Espèces"

    # Tarifs en vigueur
    BASE_PRICE_PER_STUDENT     = 60_000   # GNF/élève/an
    BADGES_PRICE_PER_STUDENT   = 40_000   # GNF/élève/an (option)
    MIN_STUDENTS               = 10

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school                = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subscriptions")
    status                = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    student_count         = models.PositiveIntegerField(default=10)
    unlocked_badges_option= models.BooleanField(default=False)
    payment_method        = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    amount_gnf            = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    payment_ref           = models.CharField(max_length=200, blank=True)
    starts_at             = models.DateTimeField(null=True, blank=True)
    expires_at            = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def is_active(self):
        return (
            self.status == self.Status.ACTIVE and
            self.expires_at is not None and
            self.expires_at > timezone.now()
        )

    def students_used(self):
        return self.school.students.count()

    @classmethod
    def compute_amount(cls, student_count: int, badges: bool) -> int:
        total = student_count * cls.BASE_PRICE_PER_STUDENT
        if badges:
            total += student_count * cls.BADGES_PRICE_PER_STUDENT
        return total


class SchoolBadge(models.Model):
    """Badge / distinction décerné à un élève par l'école."""

    class Category(models.TextChoices):
        GOLD     = "Gold",     "Or"
        SILVER   = "Silver",   "Argent"
        BRONZE   = "Bronze",   "Bronze"
        CYAN     = "Cyan",     "Cyan"
        PLATINUM = "Platinum", "Platine"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school     = models.ForeignKey(School, on_delete=models.CASCADE, related_name="badges")
    student    = models.ForeignKey("SchoolStudent", on_delete=models.CASCADE, related_name="badges")
    title      = models.CharField(max_length=200)
    category   = models.CharField(max_length=20, choices=Category.choices, default=Category.GOLD)
    message    = models.TextField(blank=True)
    signatory  = models.CharField(max_length=200, blank=True)
    issued_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.title} → {self.student.name}"


class SchoolClass(models.Model):
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classes")
    name   = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.school.name} — {self.name}"


class SchoolTeacher(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school        = models.ForeignKey(School, on_delete=models.CASCADE, related_name="teachers")
    name          = models.CharField(max_length=200)
    email         = models.CharField(max_length=200, unique=True)
    password_hash = models.CharField(max_length=255)
    classes       = models.JSONField(default=list)
    created_at    = models.DateTimeField(auto_now_add=True)

    def check_password(self, raw):
        from django.contrib.auth.hashers import check_password
        return check_password(raw, self.password_hash)

    def set_password(self, raw):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw)


class SchoolStudent(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school       = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL, related_name="students")
    name         = models.CharField(max_length=200)
    matricule    = models.CharField(max_length=50, unique=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    date_of_birth= models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.matricule})"


class SchoolGrade(models.Model):
    TRIMESTERS = [("T1","Trimestre 1"),("T2","Trimestre 2"),("T3","Trimestre 3")]
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student   = models.ForeignKey(SchoolStudent, on_delete=models.CASCADE, related_name="grades")
    teacher   = models.ForeignKey(SchoolTeacher, null=True, blank=True, on_delete=models.SET_NULL)
    subject   = models.CharField(max_length=100)
    value     = models.FloatField()
    trimester = models.CharField(max_length=5, choices=TRIMESTERS, default="T1")
    comment   = models.TextField(blank=True)
    created_at= models.DateTimeField(auto_now_add=True)


class SchoolPayment(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student    = models.ForeignKey(SchoolStudent, on_delete=models.CASCADE, related_name="payments")
    amount     = models.DecimalField(max_digits=14, decimal_places=0)
    label      = models.CharField(max_length=200)
    is_paid    = models.BooleanField(default=False)
    paid_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SchoolAbsence(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student      = models.ForeignKey(SchoolStudent, on_delete=models.CASCADE, related_name="absences")
    date         = models.DateField()
    subject      = models.CharField(max_length=100, blank=True)
    is_justified = models.BooleanField(default=False)
    comment      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
