import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Multi Satuan produk — baris satuan tambahan + konversi ke satuan utama."""

    dependencies = [
        ('core', '0136_goodsreceipt_schedule_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Deleted')),
                ('sifat', models.CharField(blank=True, choices=[('besar', 'Lebih besar dari satuan utama'), ('kecil', 'Lebih kecil dari satuan utama')], default=None, max_length=100, null=True, verbose_name='Sifat Satuan')),
                ('konversi', models.FloatField(blank=True, default=1, null=True, verbose_name='Konversi')),
                ('keterangan', models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Keterangan')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.product', verbose_name='Produk')),
                ('uom', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.uom', verbose_name='Nama Satuan')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
            ],
            options={
                'verbose_name': 'Multi Satuan',
                'verbose_name_plural': 'Multi Satuan',
                'ordering': ['-updated_at'],
                'abstract': False,
            },
        ),
    ]
