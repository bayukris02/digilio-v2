"""Transfer Kas/Bank — pemindahan dana antar akun kas/bank."""
from django.db import models
from core.fields import (
    DateField, TextField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class TransferCashBank(BaseModel):
    """Transfer Kas/Bank — pindah dana dari satu akun kas/bank ke akun lain."""

    _model_name = 'accounting.transfer_cash_bank'

    _fields = {
        'from_account': Many2OneField(
            label='Kas/Bank Asal',
            relation='accounting.payment_method',
            required=True,
        ),
        'to_account': Many2OneField(
            label='Kas/Bank Tujuan',
            relation='accounting.payment_method',
            required=True,
        ),
        'transfer_date': DateField(label='Tanggal', required=True),
        'amount': MonetaryField(label='Nominal', currency='IDR', required=True),
        'fee_amount': MonetaryField(label='Biaya Admin', currency='IDR'),
        'fee_account': Many2OneField(
            label='Akun Biaya Admin',
            relation='accounting.chart_of_account',
            help_text='Akun beban untuk biaya admin transfer',
        ),
        'notes': TextField(label='Catatan'),
    }

    _list_view = {
        'columns': ['from_account', 'to_account', 'transfer_date', 'amount', 'fee_amount'],
        'filters': ['from_account', 'to_account', 'transfer_date'],
        'default_sort': ['-transfer_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': [
                        'from_account', 'to_account', 'transfer_date',
                        'amount', 'fee_amount', 'fee_account', 'notes',
                    ],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Transfer Kas/Bank'
        verbose_name_plural = 'Transfer Kas/Bank'

    def save(self, *args, **kwargs):
        """Validasi: Kas/Bank Asal dan Tujuan tidak boleh sama."""
        if (
            self.from_account_id
            and self.from_account_id == self.to_account_id
        ):
            raise ValueError('Kas/Bank Asal dan Tujuan tidak boleh sama.')
        super().save(*args, **kwargs)

    def __str__(self):
        src = str(self.from_account) if self.from_account_id else '?'
        dst = str(self.to_account) if self.to_account_id else '?'
        return f'{src} → {dst}'
