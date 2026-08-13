from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_document_price_certification'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='content',
            field=models.TextField(
                blank=True,
                help_text="Contenu texte du cours (si pas de fichier PDF/vidéo)"
            ),
        ),
    ]
