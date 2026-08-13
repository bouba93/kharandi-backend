from django.db import migrations, models
import django.utils.timezone
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('auth', '0012_alter_user_first_name_max_length')]
    operations = [
        migrations.CreateModel(name='User', fields=[
            ('password', models.CharField(max_length=128, verbose_name='password')),
            ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
            ('is_superuser', models.BooleanField(default=False)),
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('phone', models.CharField(db_index=True, max_length=20, unique=True)),
            ('role', models.CharField(choices=[('STUDENT','Élève'),('TUTOR','Tuteur'),('PARENT','Parent'),('ADMIN','Administrateur')], default='STUDENT', max_length=10)),
            ('is_active', models.BooleanField(default=True)),
            ('is_staff', models.BooleanField(default=False)),
            ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
            ('groups', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
            ('user_permissions', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
        ], options={'verbose_name': 'Utilisateur'}),
        migrations.CreateModel(name='Profile', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('first_name', models.CharField(blank=True, max_length=100)),
            ('last_name', models.CharField(blank=True, max_length=100)),
            ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
            ('school_level', models.CharField(blank=True, max_length=50)),
            ('birth_date', models.DateField(blank=True, null=True)),
            ('city', models.CharField(blank=True, max_length=100)),
            ('bio', models.TextField(blank=True)),
            ('onboarding_completed', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='profile', to='users.user')),
        ], options={'verbose_name': 'Profil'}),
        migrations.CreateModel(name='OTPRecord', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('phone', models.CharField(db_index=True, max_length=20)),
            ('verificationid', models.CharField(blank=True, max_length=100)),
            ('sent_at', models.DateTimeField(auto_now_add=True)),
            ('verified', models.BooleanField(default=False)),
            ('expires_at', models.DateTimeField()),
        ], options={'verbose_name': 'OTP', 'ordering': ['-sent_at']}),
    ]
