from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Subject', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('name', models.CharField(max_length=100, unique=True)),
            ('icon', models.CharField(blank=True, max_length=50)),
        ], options={'verbose_name': 'Matière'}),
        migrations.CreateModel(name='Document', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('title', models.CharField(db_index=True, max_length=255)),
            ('description', models.TextField(blank=True)),
            ('doc_type', models.CharField(choices=[('LIVRE','Livre'),('COURS','Cours'),('EXERCICE','Exercice'),('CORRECTION','Correction'),('VIDEO','Vidéo')], default='COURS', max_length=15)),
            ('level', models.CharField(blank=True, max_length=10)),
            ('file', models.FileField(blank=True, null=True, upload_to='documents/')),
            ('external_url', models.URLField(blank=True)),
            ('thumbnail', models.ImageField(blank=True, null=True, upload_to='thumbnails/')),
            ('is_free', models.BooleanField(default=False)),
            ('downloads', models.PositiveIntegerField(default=0)),
            ('search_vector', SearchVectorField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('subject', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='learning.subject')),
        ], options={'ordering': ['-created_at']}),
        migrations.AddIndex(model_name='document',
            index=GinIndex(fields=['search_vector'], name='learning_do_search__idx')),
        migrations.CreateModel(name='QCM', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('subject', models.CharField(max_length=100)),
            ('level', models.CharField(max_length=10)),
            ('topic', models.CharField(max_length=200)),
            ('difficulty', models.CharField(choices=[('FACILE','Facile'),('MOYEN','Moyen'),('DIFFICILE','Difficile')], default='MOYEN', max_length=10)),
            ('questions', models.JSONField(default=list)),
            ('score', models.FloatField(blank=True, null=True)),
            ('completed', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qcms', to='users.user')),
        ], options={'ordering': ['-created_at']}),
    ]
