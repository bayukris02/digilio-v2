# Generated manually — add project_line (milestone) relation to VendorBill

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0075_vendorbill_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorbill',
            name='project_line',
            field=models.ForeignKey(blank=True, help_text='Milestone terkait (otomatis dari wizard Buat Tagihan)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.projectline', verbose_name='Milestone'),
        ),
    ]
