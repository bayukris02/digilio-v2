"""Deposit — terima atau bayar deposit (uang jaminan/titipan)."""
from django.db import models
from core.fields import (
    DateField, TextField, SelectionField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class Deposit(BaseModel):
    """Deposit — pencatatan terima/bayar deposit dengan kas/bank tujuan."""

    _model_name = 'accounting.deposit'

    _fields = {
        'deposit_type': SelectionField(
            label='Tipe Deposit',
            required=True,
            default='terima',
            options=[
                ('terima', 'Terima Deposit'),
                ('bayar', 'Bayar Deposit'),
            ],
        ),
        'bank_account': Many2OneField(
            label='Kas/Bank',
            relation='accounting.payment_method',
            required=True,
        ),
        'deposit_date': DateField(label='Tanggal', required=True),
        'amount': MonetaryField(label='Nominal', currency='IDR', required=True),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            help_text='Customer pemberi deposit (Tipe Deposit: Terima)',
        ),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            help_text='Vendor penerima deposit (Tipe Deposit: Bayar)',
        ),
        'notes': TextField(label='Catatan'),
    }

    _list_view = {
        'columns': ['deposit_type', 'bank_account', 'deposit_date', 'amount', 'customer', 'vendor'],
        'filters': ['deposit_type', 'bank_account'],
        'default_sort': ['-deposit_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': [
                        'deposit_type', 'bank_account', 'deposit_date',
                        'amount', 'customer', 'vendor', 'notes',
                    ],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Deposit'
        verbose_name_plural = 'Deposit'

    @classmethod
    def get_model_config(cls):
        """Show/hide Customer vs Vendor berdasarkan Tipe Deposit."""
        config = super().get_model_config()
        config['field_config_rules'] = {
            'customer': {
                'hide_when': {'deposit_type': 'bayar'},
            },
            'vendor': {
                'hide_when': {'deposit_type': 'terima'},
            },
        }
        return config

    def __str__(self):
        label = 'Terima' if self.deposit_type == 'terima' else 'Bayar'
        acc = str(self.bank_account) if self.bank_account_id else '?'
        return f'{label} Deposit — {acc}'
