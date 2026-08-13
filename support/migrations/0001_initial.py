from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Ticket', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('title', models.CharField(max_length=255)),
            ('description', models.TextField()),
            ('category', models.CharField(choices=[('PAIEMENT','Paiement'),('TECHNIQUE','Technique'),('CONTENU','Contenu'),('ABONNEMENT','Abonnement'),('AUTRE','Autre')], default='AUTRE', max_length=15)),
            ('status', models.CharField(choices=[('OUVERT','Ouvert'),('EN_COURS','En cours'),('RESOLU','Résolu'),('FERME','Fermé')], default='OUVERT', max_length=10)),
            ('priority', models.PositiveSmallIntegerField(default=2)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='users.user')),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel(name='TicketReply', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('message', models.TextField()),
            ('is_staff', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user')),
            ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='support.ticket')),
        ], options={'ordering': ['created_at']}),
    ]
