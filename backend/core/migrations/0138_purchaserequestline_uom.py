import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Kolom Satuan pada baris Permintaan Pembelian.

    Many2one ke baris Multi Satuan produk (`inventory.product_unit`) — bukan
    ke master Satuan (uom).
    """

    dependencies = [
        ('core', '0137_productunit'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaserequestline',
            name='uom',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+', to='core.productunit',
                verbose_name='Satuan',
            ),
        ),
    ]
