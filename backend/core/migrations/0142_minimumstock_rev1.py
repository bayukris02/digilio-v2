import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Minimum Stock — revisi desain:
      * hapus `order_qty` (qty order dihitung otomatis = max_qty - on_hand);
      * `location` FK → CharField (otomatis = daftar seluruh lokasi gudang);
      * `auto_vendors` many2many → `auto_vendor` many2one ke purchase.vendor;
      * `notify_users` many2many → `notify_user` many2one ke auth user.
    """

    dependencies = [
        ('core', '0141_minimumstock'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(model_name='minimumstock', name='auto_vendors'),
        migrations.RemoveField(model_name='minimumstock', name='notify_users'),
        migrations.RemoveField(model_name='minimumstock', name='order_qty'),
        migrations.RemoveField(model_name='minimumstock', name='location'),
        migrations.AddField(
            model_name='minimumstock',
            name='location',
            field=models.CharField(default='', max_length=255, verbose_name='Lokasi'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='minimumstock',
            name='auto_vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.vendor', verbose_name='Auto Order Vendor'),
        ),
        migrations.AddField(
            model_name='minimumstock',
            name='notify_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Email Notifikasi'),
        ),
        migrations.AlterField(
            model_name='minimumstock',
            name='action_type',
            field=models.CharField(choices=[('pr', 'Buat Purchase Request'), ('po', 'Buat Draft Purchase Order')], default='pr', max_length=100, verbose_name='Aksi Otomatis Jika Di Bawah Stok'),
        ),
        migrations.AlterField(
            model_name='minimumstock',
            name='max_qty',
            field=models.FloatField(blank=True, default=0, null=True, verbose_name='Maximum Stock', help_text='Stok maksimum — qty order otomatis = Maximum Stock - Stock Saat Ini'),
        ),
    ]
