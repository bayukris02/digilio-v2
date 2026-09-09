"""Deposit — terima atau bayar deposit (uang jaminan/titipan)."""
from django.db import models
from core.fields import (
    DateField, TextField, SelectionField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class Deposit(BaseModel):
    """Deposit — pencatatan terima/bayar deposit dengan kas/bank tujuan."""

    _model_name = 'accounting.deposit'

    # ── Document Flow ──
    _document_flow = {
        'children': [
            {
                'model': 'accounting.refund',
                'label': 'Refund',
                'icon': 'UndoOutlined',
                'source_field_in_child': 'deposit',
            },
        ],
    }

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
            'smart_buttons': [
                {'label': 'Refund', 'model': 'accounting.refund', 'icon': 'UndoOutlined'},
            ],
            'actions': [
                {'label': 'Refund', 'color': 'primary', 'action': 'refund', 'wizard': {
                    'title': 'Refund Deposit',
                    'modes': [
                        {
                            'value': 'refund',
                            'label': 'Catat Refund',
                            'icon': 'UndoOutlined',
                            'row_info': {
                                'title': 'Deposit',
                                'fields': [
                                    {'key': 'amount', 'label': 'Nominal Deposit', 'currency': True},
                                ],
                            },
                            'inputs': [
                                {'key': 'amount', 'label': 'Nominal Refund', 'type': 'number', 'min': 0,
                                 'help': 'Maksimal = Nominal Deposit dikurangi refund yang sudah dicatat.'},
                                {'key': 'refund_date', 'label': 'Tanggal Refund', 'type': 'date', 'default': 'today'},
                                {'key': 'payment_method', 'label': 'Kas/Bank', 'type': 'many2one',
                                 'relation': 'accounting.payment_method'},
                                {'key': 'notes', 'label': 'Catatan', 'type': 'text'},
                            ],
                        },
                    ],
                 }},
            ],
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

    # ── Refund ──

    def _action_refund(self, data=None):
        """Catat refund (partial) dari deposit ini."""
        from core.models.accounting.refund import create_refund
        refund = create_refund(self, data, source_field='deposit', total_field='amount')
        return {
            '_action_type': 'open_record',
            'model': 'accounting.refund',
            'record_id': refund.pk,
            'message': f'Refund Rp {float(refund.amount):,.0f} dicatat untuk {self}.',
        }

    def __str__(self):
        label = 'Terima' if self.deposit_type == 'terima' else 'Bayar'
        acc = str(self.bank_account) if self.bank_account_id else '?'
        return f'{label} Deposit — {acc}'
