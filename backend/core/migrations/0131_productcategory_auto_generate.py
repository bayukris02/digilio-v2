from django.db import migrations, models


class Migration(migrations.Migration):
    """Auto generate kode produk: flag + prefix di kategori."""

    dependencies = [
        ('core', '0130_userrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcategory',
            name='auto_generate',
            field=models.BooleanField(default=False, verbose_name='Auto Generate Kode'),
        ),
        migrations.AddField(
            model_name='productcategory',
            name='code_prefix',
            field=models.CharField(blank=True, default=None, help_text='Maksimal 7 karakter, contoh: ELEK', max_length=7, null=True, verbose_name='Prefix Kode'),
        ),
    ]
