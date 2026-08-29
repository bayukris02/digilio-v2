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
            'effect': '_effect_cancel',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen pembayaran',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
            confirm_onchange={
                'message': 'Mengganti vendor akan mereset semua alokasi. Lanjutkan?',
                'reset_relations': ['payment_lines'],
            },
        ),
        'address': TextField(label='Alamat Vendor', virtual=True),
        'code': TextField(label='Kode Vendor', virtual=True),
        'payment_date': DateField(label='Tanggal Pembayaran', required=True),
        'payment_method': Many2OneField(
            label='Metode Pembayaran',
            relation='accounting.payment_method',
            required=True,
        ),
        'payment_ref': CharField(label='Referensi Pembayaran', placeholder='No. Cek / Transfer / dll'),
        'quick_purchase': Many2OneField(
            label='Quick Purchase',
            relation='purchase.quick_purchase',
            required=False,
        ),
        'currency': CharField(label='Currency', default='IDR'),
        'total_amount': MonetaryField(
            label='Total Pembayaran', currency='IDR',
            compute='_compute_total_payment',
        ),
        'total_allocation': MonetaryField(
            label='Total Alokasi', currency='IDR',
            compute='_compute_summary',
        ),
        'remaining_amount': MonetaryField(
            label='Sisa Alokasi', currency='IDR',
            compute='_compute_summary',
        ),

        'payment_lines': One2ManyField(
            label='Baris Pembayaran',
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
                    'label': 'Umum',
                    'fields': ['reference', 'vendor', 'code', 'address',
                               'payment_date', 'payment_method', 'payment_ref', 'currency',
                               'total_amount', 'status', 'sequence_id'],
                },
            ],
            'smart_buttons': [],
            'actions': [
                {'label': 'Print', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Cancel', 'color': 'primary', 'action': 'cancel', 'states': ['draft', 'confirmed', 'done']},
                {'label': 'Action', 'color': 'primary'},
            ],
        },
        'notebook': [
            {
                'key': 'allocations',
                'label': 'Alokasi Pembayaran',
                'relation': 'payment_lines',
                'add_line_guard': ['vendor'],
                'columns': [{'name': 'bill_id', 'display_field': 'reference'}, 'vendor_name', 'due_amount', 'paid_amount'],
                'summary': {
                    'columns': {'paid_amount': 'sum'},
                    'grand_total': 'total_amount',
                    'compute_deps': ['total_amount'],
                    'after_grand_total': ['total_allocation', 'remaining_amount'],
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Pembayaran'
        verbose_name_plural = 'Pembayaran'

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

    def _compute_total_payment(self):
        """Total Payment is set manually by the user — no auto-computation needed.
        This compute method exists so the field is included in get_computed_fields(),
        allowing the SummaryCard to display the value via the compute API."""
        pass

    def _compute_summary(self):
        """Hitung Total Allocation (sum paid_amount dari lines) dan Remaining Amount."""
        from decimal import Decimal
        lines_data = getattr(self, '_tmp_one2many', {}).get('payment_lines', [])

        # Fallback ke DB jika tidak ada tmp data
        if not lines_data and self.pk:
            fd = self._field_descriptors.get('payment_lines')
            if fd:
                from core.model_meta import ErpModelBase
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    db_lines = child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    )
                    for line in db_lines:
                        lines_data.append({
                            'paid_amount': float(getattr(line, 'paid_amount', 0) or 0),
                        })

        total_alloc = sum(
            float(l.get('paid_amount', 0) or 0) for l in lines_data
        )
        self.total_allocation = total_alloc
        # Convert ke float biar konsisten (MonetaryField menerima float)
        self.remaining_amount = float(self.total_amount or 0) - total_alloc

    # ── Guards ──

    def _guard_confirm(self):
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

    # ── Effects ──

    def _effect_confirm(self):
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

        # Update paid_amount pada setiap bill yang dialokasikan
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        lines = VendorPaymentLine.objects.filter(
            payment_id=self.pk, is_deleted=False
        )
        for line in lines:
            bill = line.bill_id
            if bill:
                bill.paid_amount = (bill.paid_amount or 0) + (line.paid_amount or 0)
                bill._run_compute()
                bill.save()

    def _effect_cancel(self):
        """Reverse paid_amount pada bill yang dialokasikan saat payment di-cancel."""
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        lines = VendorPaymentLine.objects.filter(
            payment_id=self.pk, is_deleted=False
        )
        for line in lines:
            bill = line.bill_id
            if bill:
                bill.paid_amount = max((bill.paid_amount or 0) - (line.paid_amount or 0), 0)
                bill._run_compute()
                bill.save()

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
