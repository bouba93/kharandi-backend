from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Plan', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('name', models.CharField(max_length=100)),
            ('period', models.CharField(choices=[('MENSUEL','Mensuel'),('ANNUEL','Annuel'),('GRATUIT','Gratuit'),('SEMESTRIEL','Semestriel')], max_length=12)),
            ('price', models.DecimalField(decimal_places=2, max_digits=10)),
            ('currency', models.CharField(default='GNF', max_length=5)),
            ('features', models.JSONField(default=list)),
            ('is_active', models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name='Subscription', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('status', models.CharField(choices=[('ACTIVE','Actif'),('EXPIRED','Expiré'),('PENDING','En attente'),('CANCELLED','Annulé')], default='PENDING', max_length=10)),
            ('start_date', models.DateTimeField(blank=True, null=True)),
            ('end_date', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('plan', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='payments.plan')),
            ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to='users.user')),
        ]),
        migrations.CreateModel(name='Transaction', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('reference', models.CharField(db_index=True, max_length=100, unique=True)),
            ('gateway_ref', models.CharField(blank=True, max_length=200)),
            ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
            ('currency', models.CharField(default='GNF', max_length=5)),
            ('provider', models.CharField(choices=[('LENGOPAY','LengoPay')], default='LENGOPAY', max_length=15)),
            ('status', models.CharField(choices=[('PENDING','En attente'),('SUCCESS','Réussie'),('FAILED','Échouée'),('REFUNDED','Remboursée')], default='PENDING', max_length=10)),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('webhook_payload', models.JSONField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='users.user')),
            ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.subscription')),
        ], options={'ordering': ['-created_at']}),
    ]
