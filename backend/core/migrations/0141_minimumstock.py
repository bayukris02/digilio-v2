import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Minimum Stock — batas stok minimum per produk/gudang/lokasi + aksi auto order."""

    dependencies = [
        ('core', '0140_productunit_sifat_utama'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MinimumStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Deleted')),
                ('name', models.CharField(max_length=255, verbose_name='Nama Aturan')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('min_qty', models.FloatField(default=0, verbose_name='Minimum Stock', help_text='Stok minimum yang harus tersedia')),
                ('order_qty', models.FloatField(blank=True, default=0, null=True, verbose_name='Jumlah Order', help_text='Qty yang dipesan saat stok di bawah minimum')),
                ('max_qty', models.FloatField(blank=True, default=0, null=True, verbose_name='Maximum Stock', help_text='Otomatis: Minimum Stock + Jumlah Order')),
                ('on_hand', models.FloatField(blank=True, default=0, null=True, verbose_name='Stock Saat Ini')),
                ('below_min', models.BooleanField(default=False, verbose_name='Di Bawah Minimum')),
                ('action_type', models.CharField(choices=[('pr', 'Buat Purchase Request'), ('po', 'Buat Draft Purchase Order')], default='pr', max_length=100, verbose_name='Aksi Jika Di Bawah Stok')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Catatan')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.product', verbose_name='Produk')),
                ('warehouse', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.warehouse', verbose_name='Gudang')),
                ('location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.warehouselocation', verbose_name='Lokasi')),
                ('auto_vendors', models.ManyToManyField(blank=True, related_name='+', to='core.vendor', verbose_name='Auto Order Vendor')),
                ('notify_users', models.ManyToManyField(blank=True, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Email Notifikasi')),
            ],
            options={
                'verbose_name': 'Minimum Stock',
                'verbose_name_plural': 'Minimum Stock',
                'ordering': ['-updated_at'],
                'abstract': False,
            },
        ),
    ]
