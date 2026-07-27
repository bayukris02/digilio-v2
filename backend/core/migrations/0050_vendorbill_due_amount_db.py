# Manual migration: add due_amount column to DB table only
# State sudah dianggap ada via migration 0049 (di-fake)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_vendorbill_due_amount_vendorbill_paid_amount'),
    ]

    operations = [
        migrations.RunSQL(
            'ALTER TABLE core_vendorbill ADD COLUMN "due_amount" numeric(18, 2) NULL;',
            reverse_sql='ALTER TABLE core_vendorbill DROP COLUMN "due_amount";',
        ),
    ]
