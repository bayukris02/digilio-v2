from django.db import migrations, models


def dedupe_product_codes(apps, schema_editor):
    """Rapikan kode produk sebelum constraint unik dipasang:
    - kode kosong → NULL (boleh banyak)
    - kode dobel  → nomor berikutnya yang bebas dengan prefix yang sama
    """
    Product = apps.get_model('core', 'Product')
    used = {}
    for product in Product.objects.order_by('id'):
        code = (product.code or '').strip()
        if not code:
            Product.objects.filter(pk=product.pk).update(code=None)
            continue
        key = code.lower()
        if key not in used:
            used[key] = product.pk
            continue
        prefix = code.split('-')[0]
        n = 1
        while f'{prefix}-{n:03d}'.lower() in used:
            n += 1
        new_code = f'{prefix}-{n:03d}'
        Product.objects.filter(pk=product.pk).update(code=new_code)
        used[new_code.lower()] = product.pk


class Migration(migrations.Migration):
    """SKU produk unik (satu kode hanya untuk satu produk)."""

    dependencies = [
        ('core', '0132_productcategory_code_3char'),
    ]

    operations = [
        migrations.RunPython(dedupe_product_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='code',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, unique=True, verbose_name='SKU / Kode'),
        ),
    ]
