from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel('News', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('title', models.CharField(max_length=255)),
            ('excerpt', models.TextField(blank=True)),
            ('content', models.TextField(blank=True)),
            ('category', models.CharField(blank=True, max_length=100)),
            ('color', models.CharField(blank=True, default='bg-primary/10 text-primary', max_length=100)),
            ('date', models.CharField(blank=True, max_length=50)),
            ('is_published', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel('SchoolRanking', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('rank', models.PositiveIntegerField()),
            ('name', models.CharField(max_length=255)),
            ('location', models.CharField(blank=True, max_length=255)),
            ('school_type', models.CharField(blank=True, max_length=100)),
            ('score', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
            ('year', models.PositiveIntegerField(default=2024)),
        ], options={'ordering': ['rank']}),
        migrations.CreateModel('StudyAbroad', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('university', models.CharField(max_length=255)),
            ('program_name', models.CharField(max_length=255)),
            ('country', models.CharField(max_length=100)),
            ('city', models.CharField(blank=True, max_length=100)),
            ('level', models.CharField(blank=True, max_length=50)),
            ('link', models.URLField(blank=True)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['country', 'university']}),
        migrations.CreateModel('TutorAd', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('ad_type', models.CharField(choices=[('offer','Offre de cours'),('request','Demande de répétiteur')], default='offer', max_length=10)),
            ('subject', models.CharField(max_length=100)),
            ('level', models.CharField(blank=True, max_length=50)),
            ('location', models.CharField(blank=True, max_length=100)),
            ('description', models.TextField()),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('author_name', models.CharField(blank=True, max_length=200)),
            ('is_boosted', models.BooleanField(default=False)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tutor_ads', to='users.user')),
        ], options={'ordering': ['-is_boosted', '-created_at']}),
        migrations.CreateModel('Notification', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('title', models.CharField(max_length=255)),
            ('message', models.TextField()),
            ('notif_type', models.CharField(choices=[('info','Information'),('success','Succès'),('warning','Avertissement'),('promo','Promotion')], default='info', max_length=10)),
            ('link', models.CharField(blank=True, max_length=255)),
            ('is_read', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifs', to='users.user')),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel('ReadingProgress', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('document_id', models.CharField(db_index=True, max_length=100)),
            ('progress', models.PositiveIntegerField(default=0)),
            ('is_read', models.BooleanField(default=False)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user')),
        ], options={'unique_together': {('user', 'document_id')}}),
    ]
