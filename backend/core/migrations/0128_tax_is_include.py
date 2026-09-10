from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_refund_reference_alter_customerinvoice_sales_order_and_more'),
    ]

    operations = [
        # Fitur "Pajak Include": master tax bisa ditandai include — harga baris
        # dianggap SUDAH termasuk pajak (dasar = harga/(1+rate), tidak menambah
        # total tagihan). Perhitungan include diterapkan di baris Faktur.
        migrations.AddField(
            model_name='tax',
            name='is_include',
            field=models.BooleanField(
                default=False,
                help_text='Centang bila harga di baris dokumen SUDAH termasuk pajak ini. '
                          'Pajak dihitung dari dasar (harga/(1+rate)) & TIDAK menambah total tagihan.',
                verbose_name='Termasuk Pajak (Include)',
            ),
        ),
    ]
