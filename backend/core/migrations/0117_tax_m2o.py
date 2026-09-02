# Migrasi: kolom Pajak (taxes) di 6 line model berubah dari many2many → many2one.
# Urutan penting: kumpulkan pilihan lama (bisa >1) → ambil tax pertama per line
# → RemoveField m2m (drop through table) → AddField FK taxes_id → restore.

import django.db.models.deletion
from django.db import migrations, models

LINE_MODELS = (
    ('CustomerInvoiceLine', 'customerinvoiceline'),
    ('VendorBillLine', 'vendorbillline'),
    ('SalesOrderLine', 'salesorderline'),
    ('PurchaseOrderLine', 'purchaseorderline'),
    ('QuickSalesLine', 'quicksalesline'),
    ('QuickPurchaseLine', 'quickpurchaseline'),
)

_picked = {}  # {model_name: {line_id: first_tax_id}}


def pick_first_tax(apps, schema_editor):
    """Simpan tax pertama (by pk) per line sebelum m2m dihapus."""
    for model_name, _table in LINE_MODELS:
        LineModel = apps.get_model('core', model_name)
        mapping = {}
        # Manager m2m masih tersedia pada state migrasi ini
        for line in LineModel.objects.all().iterator():
            first = line.taxes.order_by('pk').first()
            if first is not None:
                mapping[line.pk] = first.pk
        if mapping:
            _picked[model_name] = mapping


def restore_tax(apps, schema_editor):
    """Set taxes_id dari hasil pick (FK sudah ada)."""
    for model_name, mapping in _picked.items():
        LineModel = apps.get_model('core', model_name)
        for line_id, tax_id in mapping.items():
            LineModel.objects.filter(pk=line_id).update(taxes_id=tax_id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0114_tax_m2m'),
    ]

    operations = [
        migrations.RunPython(pick_first_tax, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='customerinvoiceline',
            name='taxes',
        ),
        migrations.RemoveField(
            model_name='vendorbillline',
            name='taxes',
        ),
        migrations.RemoveField(
            model_name='salesorderline',
            name='taxes',
        ),
        migrations.RemoveField(
            model_name='purchaseorderline',
            name='taxes',
        ),
        migrations.RemoveField(
            model_name='quicksalesline',
            name='taxes',
        ),
        migrations.RemoveField(
            model_name='quickpurchaseline',
            name='taxes',
        ),
        migrations.AddField(
            model_name='customerinvoiceline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.AddField(
            model_name='vendorbillline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.AddField(
            model_name='salesorderline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.AddField(
            model_name='purchaseorderline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.AddField(
            model_name='quicksalesline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.AddField(
            model_name='quickpurchaseline',
            name='taxes',
            field=models.ForeignKey(blank=True, help_text='Pilih pajak (PPN, PPh, dll)', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='core.tax', verbose_name='Pajak'),
        ),
        migrations.RunPython(restore_tax, migrations.RunPython.noop),
    ]
