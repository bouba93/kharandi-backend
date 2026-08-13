import uuid
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_profile_onboarding_completed'),
    ]
    operations = [
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to='users.user')),
                ('device_token', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('user_agent', models.TextField(blank=True)),
                ('last_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-last_used']},
        ),
    ]
