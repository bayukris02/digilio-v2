from django.db import migrations, models


class Migration(migrations.Migration):
    """Penerimaan barang: field Jadwal Penerimaan (tipe wizard 'Jadwalkan Penerimaan')."""

    dependencies = [
        ('core', '0135_stockledger_avg_cost'),
    ]

    operations = [
        migrations.AddField(
            model_name='goodsreceipt',
            name='schedule_date',
            field=models.DateField(
                blank=True, null=True, verbose_name='Jadwal Penerimaan',
                help_text='Tanggal rencana penerimaan barang (diisi saat Jadwalkan Penerimaan)',
            ),
        ),
    ]
