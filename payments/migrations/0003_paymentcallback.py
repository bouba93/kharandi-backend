"""
Migration additive et NON destructive.

  * CREATE TABLE payments_paymentcallback  → journal des callbacks LengoPay
  * CREATE INDEX sur Transaction.gateway_ref et (status, created_at)

Aucune colonne existante n'est modifiée, aucune donnée n'est supprimée.
Réversible : la migration inverse ne fait que DROP de ces nouveaux objets.
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_transaction_order"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["gateway_ref"], name="tx_gateway_ref_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["status", "created_at"], name="tx_status_created_idx"
            ),
        ),
        migrations.CreateModel(
            name="PaymentCallback",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("pay_id", models.CharField(blank=True, db_index=True, max_length=200)),
                ("announced_status", models.CharField(blank=True, max_length=32)),
                ("applied_status", models.CharField(blank=True, max_length=32)),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("APPLIED", "Appliqué"),
                            ("DUPLICATE", "Doublon (déjà traité)"),
                            ("PENDING", "Statut encore en attente"),
                            ("ORPHAN", "Transaction introuvable"),
                            ("UNVERIFIED", "Non authentifié"),
                            ("MISMATCH", "Montant ou statut incohérent"),
                            ("INVALID", "Charge utile invalide"),
                            ("ERROR", "Erreur interne"),
                        ],
                        db_index=True,
                        max_length=12,
                    ),
                ),
                ("auth_method", models.CharField(blank=True, max_length=24)),
                ("source_ip", models.CharField(blank=True, max_length=64)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("detail", models.TextField(blank=True)),
                ("replayed", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "transaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="callbacks",
                        to="payments.transaction",
                    ),
                ),
            ],
            options={
                "verbose_name": "Callback LengoPay",
                "verbose_name_plural": "Callbacks LengoPay",
                "ordering": ["-created_at"],
            },
        ),
    ]
