from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Prix du document en GNF (0 = gratuit)', max_digits=10),
        ),
        migrations.AddField(
            model_name='document',
            name='has_certification',
            field=models.BooleanField(default=False, help_text='Le document délivre-t-il une certification ?'),
        ),
    ]
