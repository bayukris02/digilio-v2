import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Minimum Stock — revisi desain 2:
      * `location` CharField → many2many ke inventory.warehouse_location
        (otomatis terisi semua lokasi gudang, tetap bisa diubah user);
      * `notify_user` many2one → `notify_users` many2many ke auth user;
      * tambah FK `minimum_stock` di purchase.request & purchase.order
        (dipakai smart button PR/PO).
    """

    dependencies = [
        ('core', '0142_minimumstock_rev1'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(model_name='minimumstock', name='notify_user'),
        migrations.RemoveField(model_name='minimumstock', name='location'),
        migrations.AddField(
            model_name='minimumstock',
            name='location',
            field=models.ManyToManyField(blank=True, related_name='+', to='core.warehouselocation', verbose_name='Lokasi', help_text='Otomatis terisi semua lokasi gudang; bisa diubah'),
        ),
        migrations.AddField(
            model_name='minimumstock',
            name='notify_users',
            field=models.ManyToManyField(blank=True, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Email Notifikasi', help_text='User yang dikirimi email saat stok di bawah minimum'),
        ),
        migrations.AddField(
            model_name='purchaserequest',
            name='minimum_stock',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.minimumstock', verbose_name='Sumber Minimum Stock'),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='minimum_stock',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.minimumstock', verbose_name='Sumber Minimum Stock'),
        ),
    ]
