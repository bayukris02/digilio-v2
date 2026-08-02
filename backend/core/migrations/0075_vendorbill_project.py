# Generated manually — add project relation to VendorBill

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0074_projectunit_qty_available_projectunit_qty_sold_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorbill',
            name='project',
            field=models.ForeignKey(blank=True, help_text='Project asal tagihan (otomatis dari wizard Buat Tagihan)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.project', verbose_name='Project'),
        ),
    ]
