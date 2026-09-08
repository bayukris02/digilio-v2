# Generated manually — add deduct_dp (opt-in potong DP) ke VendorBill.
# Migration data: bill regular lama yang sudah punya down_payment_amount>0 dan
# grand_total >= 0 di-backfill deduct_dp=True agar perilaku lama (DP terpotong
# otomatis) tetap terjaga. Bill yang grand_total-nya minus (rusak karena DP
# otomatis > nilai tagihan) TIDAK di-backfill — DP-nya akan hilang saat
# recompute berikutnya sehingga nilai tagihan jadi wajar (positif).

from django.db import migrations, models


def backfill_deduct_dp(apps, schema_editor):
    from core.models.accounting.vendor_bill import VendorBill
    qs = VendorBill.objects.filter(
        is_down_payment=False,
        is_deleted=False,
    ).exclude(status='cancelled')
    for b in qs:
        dp = float(b.down_payment_amount or 0)
        gt = float(b.grand_total or 0)
        if dp > 0 and gt >= -0.005:
            b.deduct_dp = True
            b.save(update_fields=['deduct_dp'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0124_customerreceipt_difference_account_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorbill',
            name='deduct_dp',
            field=models.BooleanField(default=False, verbose_name='Potong DP dari Tagihan ini'),
        ),
        migrations.RunPython(backfill_deduct_dp, migrations.RunPython.noop),
    ]
