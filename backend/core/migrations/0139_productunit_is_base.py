from django.db import migrations, models


def backfill_base_units(apps, schema_editor):
    """Pastikan setiap produk punya 1 baris Multi Satuan `is_base = True`.

    Baris satuan utama sebelumnya hanya turunan dari field `Satuan` header
    (tidak tersimpan). Sekarang baris ini disimpan supaya bisa dirujuk
    many2one (mis. kolom Satuan di Permintaan Pembelian).
    """
    Product = apps.get_model('core', 'Product')
    ProductUnit = apps.get_model('core', 'ProductUnit')

    for product in Product.objects.filter(is_deleted=False).exclude(uom_id=None).iterator():
        rows = list(ProductUnit.objects.filter(
            product_id=product.pk, is_deleted=False,
        ).order_by('id'))

        # Baris yang sudah ber-flag is_base → sisakan satu saja
        bases = [r for r in rows if r.is_base]
        if bases:
            for dup in bases[1:]:
                dup.is_deleted = True
                dup.save(update_fields=['is_deleted'])
            continue

        # Sudah ada baris tersimpan dengan satuan = Satuan produk → jadikan base
        candidate = next((r for r in rows if r.uom_id == product.uom_id), None)
        if candidate is None:
            ProductUnit.objects.create(
                product_id=product.pk, uom_id=product.uom_id,
                is_base=True, konversi=1, sifat=None, is_deleted=False,
            )
            continue

        candidate.is_base = True
        candidate.konversi = 1
        candidate.sifat = None
        candidate.save(update_fields=['is_base', 'konversi', 'sifat'])


class Migration(migrations.Migration):
    """Satuan utama (baris 1 Multi Satuan) jadi baris tersimpan + backfill."""

    dependencies = [
        ('core', '0138_purchaserequestline_uom'),
    ]

    operations = [
        migrations.AddField(
            model_name='productunit',
            name='is_base',
            field=models.BooleanField(default=False, verbose_name='Satuan Utama'),
        ),
        migrations.RunPython(backfill_base_units, migrations.RunPython.noop),
    ]
