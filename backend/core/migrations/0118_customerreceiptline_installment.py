# Migrasi: relasi baris penerimaan (customer_receipt_line) ke baris cicilan
# (customer_invoice_installment) — dipakai alur "Input Penerimaan" per cicilan
# di tab Cicilan Faktur: receipt dibuat dari tombol baris, alokasi mengarah ke
# cicilan spesifik sehingga saat confirm, cicilan itu bisa ditandai Lunas.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0117_tax_m2o'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerreceiptline',
            name='installment_id',
            field=models.ForeignKey(blank=True, help_text='Baris cicilan yang dibayar (alur Input Penerimaan di tab Cicilan Faktur)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.customerinvoiceinstallment', verbose_name='Cicilan'),
        ),
    ]
