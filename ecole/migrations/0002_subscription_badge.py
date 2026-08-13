import uuid
import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ecole', '0001_initial'),
    ]

    operations = [
        # ── SchoolSubscription ──────────────────────────────────────────────
        migrations.CreateModel(
            name='SchoolSubscription',
            fields=[
                ('id',                     models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('school',                 models.ForeignKey('ecole.School', on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions')),
                ('status',                 models.CharField(max_length=10, choices=[('pending','En attente'),('active','Actif'),('expired','Expiré'),('canceled','Annulé')], default='pending')),
                ('student_count',          models.PositiveIntegerField(default=10)),
                ('unlocked_badges_option', models.BooleanField(default=False)),
                ('payment_method',         models.CharField(max_length=20, blank=True)),
                ('amount_gnf',             models.DecimalField(max_digits=14, decimal_places=0, default=0)),
                ('payment_ref',            models.CharField(max_length=200, blank=True)),
                ('starts_at',              models.DateTimeField(null=True, blank=True)),
                ('expires_at',             models.DateTimeField(null=True, blank=True)),
                ('created_at',             models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        # ── SchoolBadge ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SchoolBadge',
            fields=[
                ('id',        models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('school',    models.ForeignKey('ecole.School', on_delete=django.db.models.deletion.CASCADE, related_name='badges')),
                ('student',   models.ForeignKey('ecole.SchoolStudent', on_delete=django.db.models.deletion.CASCADE, related_name='badges')),
                ('title',     models.CharField(max_length=200)),
                ('category',  models.CharField(max_length=20, choices=[('Gold','Or'),('Silver','Argent'),('Bronze','Bronze'),('Cyan','Cyan'),('Platinum','Platine')], default='Gold')),
                ('message',   models.TextField(blank=True)),
                ('signatory', models.CharField(max_length=200, blank=True)),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-issued_at']},
        ),
    ]
