from django.db import migrations, models


class Migration(migrations.Migration):
    """Stock ledger menyimpan HPP rata-rata (AVCO) per pergerakan."""

    dependencies = [
        ('core', '0134_product_cost_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockledger',
            name='avg_cost',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=18, null=True, verbose_name='HPP (Avg)'),
        ),
    ]
