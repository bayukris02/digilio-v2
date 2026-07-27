from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class VendorPayment(BaseModel):
    """Pembayaran ke vendor — melunasi satu atau lebih Vendor Bill."""

    _model_name = 'accounting.vendor_payment'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
        'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Done', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'confirmed',
            'label': 'Confirm',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'mark_done',
            'from': ['confirmed'],
            'to': 'done',
            'label': 'Mark Done',
            'icon': 'CheckCircleOutlined',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'confirmed', 'done'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen pembayaran',
        ),
        'reference': CharField(label='Reference', required=True, editable_statuses=[], placeholder='Automatic'),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
        ),
        'address': TextField(label='Alamat Vendor', virtual=True),
        'code': TextField(label='Kode Vendor', virtual=True),
        'payment_date': DateField(label='Payment Date', required=True),
        'payment_method': Many2OneField(
            label='Payment Method',
            relation='accounting.payment_method',
            required=True,
        ),
        'payment_ref': CharField(label='Payment Reference', placeholder='No. Cek / Transfer / dll'),
        'currency': CharField(label='Currency', default='IDR'),
        'total_amount': MonetaryField(label='Total Amount', currency='IDR'),

        'payment_lines': One2ManyField(
            label='Payment Lines',
            relation='accounting.vendor_payment_line',
            inverse_field='payment_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'vendor', 'payment_date', 'payment_method', 'status', 'total_amount'],
        'filters': ['status', 'vendor', 'payment_method', 'payment_date'],
        'group_by': ['status', 'vendor'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'vendor', 'code', 'address',
                               'payment_date', 'payment_method', 'payment_ref', 'currency',
                               'total_amount', 'status', 'sequence_id'],
                },
            ],
            'smart_buttons': [],
            'actions': [
                {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'primary', 'action': 'cancel', 'states': ['draft', 'confirmed', 'done']},
                {'label': 'Action', 'icon': 'MoreOutlined', 'color': 'primary'},
            ],
        },
        'notebook': [
            {
                'key': 'allocations',
                'label': 'Payment Allocations',
                'relation': 'payment_lines',
                'columns': ['bill_id', 'vendor_name', 'due_amount', 'paid_amount'],
                'summary': {
                    'columns': {'paid_amount': 'sum'},
                    'grand_total': 'total_amount',
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Vendor Payment'
        verbose_name_plural = 'Vendor Payments'

    # ── Config ──

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(
            model_ref='accounting.vendor_payment', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    # ── Guards ──

    def _guard_confirm(self):
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

    # ── Effects ──

    def _effect_confirm(self):
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    # ── Legacy Actions ──

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/accounting.vendor_payment/{self.pk}/preview/',
            'pdf_url': f'/api/print/accounting.vendor_payment/{self.pk}/download/',
        }

    def _print_context(self):
        data = super()._print_context()
        return data
