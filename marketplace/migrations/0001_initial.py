from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.CreateModel('Product', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('title', models.CharField(max_length=255)),
            ('description', models.TextField(blank=True)),
            ('price', models.DecimalField(decimal_places=2, max_digits=12)),
            ('stock', models.PositiveIntegerField(default=10)),
            ('category', models.CharField(blank=True, max_length=100)),
            ('image_url', models.URLField(blank=True)),
            ('status', models.CharField(choices=[('active','Actif'),('inactive','Inactif')], default='active', max_length=10)),
            ('variants', models.JSONField(blank=True, default=list)),
            ('is_boosted', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='users.user')),
        ], options={'ordering': ['-is_boosted', '-created_at']}),
        migrations.CreateModel('PromoCode', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('discount', models.PositiveIntegerField(default=10)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promos', to='users.user')),
        ]),
        migrations.CreateModel('Order', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('product_title', models.CharField(max_length=255)),
            ('price', models.DecimalField(decimal_places=2, max_digits=12)),
            ('status', models.CharField(choices=[('pending','En attente'),('completed','Terminée'),('shipped','Expédiée'),('delivered','Livrée'),('cancelled','Annulée')], default='pending', max_length=12)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_orders', to='users.user')),
            ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketplace.product')),
            ('promo_code', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='marketplace.promocode')),
        ], options={'ordering': ['-created_at']}),
    ]
