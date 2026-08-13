from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel('Grade', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('subject', models.CharField(max_length=100)),
            ('grade_type', models.CharField(default='Devoir', max_length=50)),
            ('score', models.DecimalField(decimal_places=2, max_digits=5)),
            ('max_score', models.DecimalField(decimal_places=2, default=20, max_digits=5)),
            ('date', models.DateField()),
            ('comment', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='given_grades', to='users.user')),
            ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_grades', to='users.user')),
        ], options={'ordering': ['-created_at']}),
    ]
