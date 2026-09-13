from django.db import migrations


def normalize_base_units(apps, schema_editor):
    """Baris satuan utama: sifat = 'utama' + konversi 1.

    Sifat 'utama' hanya nilai internal (disembunyikan dari dropdown user) agar
    kolom wajib "Sifat Satuan" pada baris pertama tetap terisi.
    """
    ProductUnit = apps.get_model('core', 'ProductUnit')
    rows = ProductUnit.objects.filter(is_base=True, is_deleted=False).exclude(sifat='utama')
    for row in rows.iterator():
        ProductUnit.objects.filter(pk=row.pk).update(sifat='utama', konversi=1)


class Migration(migrations.Migration):
    """Normalisasi baris satuan utama Multi Satuan (sifat 'utama')."""

    dependencies = [
        ('core', '0139_productunit_is_base'),
    ]

    operations = [
        migrations.RunPython(normalize_base_units, migrations.RunPython.noop),
    ]
