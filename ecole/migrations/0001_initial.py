from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='School', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('name', models.CharField(max_length=200)),
            ('email', models.EmailField(unique=True)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('password_hash', models.CharField(blank=True, max_length=255)),
            ('is_activated', models.BooleanField(default=False)),
            ('logo_url', models.URLField(blank=True)),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('address', models.TextField(blank=True)),
            ('subscription_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['name']}),
        migrations.CreateModel(name='SchoolClass', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='ecole.school')),
            ('name', models.CharField(max_length=100)),
        ]),
        migrations.CreateModel(name='SchoolTeacher', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teachers', to='ecole.school')),
            ('name', models.CharField(max_length=200)),
            ('email', models.CharField(max_length=200, unique=True)),
            ('password_hash', models.CharField(max_length=255)),
            ('classes', models.JSONField(default=list)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name='SchoolStudent', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='ecole.school')),
            ('school_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='ecole.schoolclass')),
            ('name', models.CharField(max_length=200)),
            ('matricule', models.CharField(max_length=50, unique=True)),
            ('parent_phone', models.CharField(blank=True, max_length=20)),
            ('date_of_birth', models.DateField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name='SchoolGrade', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='ecole.schoolstudent')),
            ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ecole.schoolteacher')),
            ('subject', models.CharField(max_length=100)),
            ('value', models.FloatField()),
            ('trimester', models.CharField(choices=[('T1','Trimestre 1'),('T2','Trimestre 2'),('T3','Trimestre 3')], default='T1', max_length=5)),
            ('comment', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name='SchoolPayment', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='ecole.schoolstudent')),
            ('amount', models.DecimalField(decimal_places=0, max_digits=14)),
            ('label', models.CharField(max_length=200)),
            ('is_paid', models.BooleanField(default=False)),
            ('paid_at', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name='SchoolAbsence', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
            ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absences', to='ecole.schoolstudent')),
            ('date', models.DateField()),
            ('subject', models.CharField(blank=True, max_length=100)),
            ('is_justified', models.BooleanField(default=False)),
            ('comment', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
    ]
