from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial'), ('learning', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Order', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('status', models.CharField(choices=[('PENDING','En attente'),('PAID','Payée'),('CANCELLED','Annulée')], default='PENDING', max_length=12)),
            ('total', models.DecimalField(decimal_places=2, max_digits=12)),
            ('currency', models.CharField(default='GNF', max_length=5)),
            ('note', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='users.user')),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel(name='OrderItem', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('name', models.CharField(max_length=255)),
            ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
            ('quantity', models.PositiveSmallIntegerField(default=1)),
            ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='ecommerce.order')),
            ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='learning.document')),
        ]),
    ]
