from django.db import migrations, models


class Migration(migrations.Migration):
    """Perhitungan HPP: field `cost_method` pindah ke KATEGORI produk
    (Manual / Otomatis AVCO) + rename label Harga Beli → HPP (Harga Pokok)."""

    dependencies = [
        ('core', '0133_product_code_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=18, null=True, verbose_name='HPP (Harga Pokok)'),
        ),
        migrations.AddField(
            model_name='productcategory',
            name='cost_method',
            field=models.CharField(choices=[('manual', 'Manual'), ('avco', 'Otomatis (AVCO)')], default='manual', help_text='Manual: HPP produk diisi sendiri. Otomatis (AVCO): HPP dihitung dari pembelian/penyesuaian stok (average cost) dan tidak bisa diisi manual.', max_length=100, verbose_name='Perhitungan HPP'),
        ),
    ]
