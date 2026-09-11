import re

from django.db import migrations, models


def _code_from_name(name):
    alnum = re.sub(r'[^0-9A-Za-z]', '', name or '').upper()
    if not alnum:
        return ''
    code = alnum[:3]
    while len(code) < 3:
        code += code[-1]
    return code


def fill_category_codes(apps, schema_editor):
    """Isi kode kategori lama (NULL/kosong) dari nama, sebelum kolom jadi NOT NULL."""
    ProductCategory = apps.get_model('core', 'ProductCategory')
    rows = list(ProductCategory.objects.all().order_by('id'))
    used = {(c.code or '').strip().upper() for c in rows if (c.code or '').strip()}
    for cat in rows:
        if (cat.code or '').strip():
            continue
        code = _code_from_name(cat.name)
        if not code or code in used:
            code = ''  # biarkan kosong — user melengkapi lewat form (guard unik)
        else:
            used.add(code)
        ProductCategory.objects.filter(pk=cat.pk).update(code=code)


class Migration(migrations.Migration):
    """Kode Kategori 3 karakter (auto dari nama, wajib & unik)."""

    dependencies = [
        ('core', '0131_productcategory_auto_generate'),
    ]

    operations = [
        migrations.RunPython(fill_category_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='productcategory',
            name='code',
            field=models.CharField(max_length=3, verbose_name='Kode Kategori'),
        ),
        migrations.AlterField(
            model_name='productcategory',
            name='code_prefix',
            field=models.CharField(blank=True, default=None, help_text='Maksimal 7 karakter, contoh: ATK', max_length=7, null=True, verbose_name='Prefix Kode'),
        ),
    ]
