import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_userdevice'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='points',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='PointTransaction',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='point_transactions',
                    to='users.user'
                )),
                ('type', models.CharField(
                    max_length=6,
                    choices=[('CREDIT', 'Crédit'), ('DEBIT', 'Débit')]
                )),
                ('source', models.CharField(max_length=15, default='EXERCISE')),
                ('points', models.PositiveIntegerField()),
                ('balance_after', models.PositiveIntegerField(default=0)),
                ('description', models.CharField(max_length=255)),
                ('reference', models.CharField(max_length=100, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Transaction de points'},
        ),
    ]
