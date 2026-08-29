from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class CustomerInvoice(BaseModel):
    _model_name = 'accounting.customer_invoice'
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
            help_text='Pilih format nomor dokumen faktur',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
        ),
        'address': TextField(label='Alamat Customer', virtual=True),
        'code': TextField(label='Kode Customer', virtual=True),
        'invoice_date': DateField(label='Tanggal Faktur'),
        'due_date': DateField(label='Jatuh Tempo'),
        'description': TextField(label='Deskripsi'),
        'notes': TextField(label='Catatan', chatter_show=False),
        'sales_order': Many2OneField(
            label='Penjualan',
            relation='sales.order',
            required=False,
        ),
        'quick_sales': Many2OneField(
            label='Quick Sales',
            relation='sales.quick_sales',
            required=False,
        ),
        'unit_detail': Many2OneField(
            label='Detail Unit',
            relation='project.project_unit_detail',
            required=False,
            help_text='Detail Unit proyek yang dijual lewat invoice ini',
        ),

        # ── Down Payment ──
        'is_down_payment': BooleanField(label='Faktur DP', default=False),
        'down_payment_amount': MonetaryField(label='Jumlah DP', currency='IDR',
            compute='_compute_down_payment', depends=['sales_order']),

        # ── Summary fields ──
        'subtotal': MonetaryField(label='Subtotal', currency='IDR',
            compute='_compute_summary', depends=['invoice_lines']),
        'discount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_summary', depends=['invoice_lines']),
        'tax': MonetaryField(label='Pajak', currency='IDR',
            compute='_compute_summary', depends=['invoice_lines']),
        'manual_discount': FloatField(label='Diskon Manual (%)', default=0),
        'grand_total': MonetaryField(label='Grand Total', currency='IDR',
            compute='_compute_summary', depends=['invoice_lines', 'manual_discount', 'down_payment_amount']),

        'invoice_lines': One2ManyField(
            label='Baris Faktur',
            relation='accounting.customer_invoice_line',
            inverse_field='invoice_id',
        ),

        # ── Payment fields ──
        'due_amount': MonetaryField(label='Sisa Tagihan', currency='IDR',
            compute='_compute_payment_summary', depends=['grand_total', 'paid_amount']),
        'paid_amount': MonetaryField(label='Sudah Dibayar', currency='IDR', default=0),
        'payment_status': SelectionField(
            label='Status Pembayaran',
            options=[('unpaid', 'Belum Dibayar'), ('partial', 'Sebagian'), ('paid', 'Lunas')],
            compute='_compute_payment_summary',
            depends=['grand_total', 'paid_amount'],
            default='unpaid',
            colors={'unpaid': 'red', 'partial': 'orange', 'paid': 'green'},
        ),
    }

    _list_view = {
        'columns': ['reference', 'sales_order', 'customer', 'invoice_date', 'due_date', 'status', 'grand_total', 'due_amount', 'payment_status'],
        'filters': ['status', 'customer', 'invoice_date', 'payment_status'],
        'group_by': ['status', 'customer', 'payment_status'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'sales_order', 'customer', 'code', 'address',
                               'invoice_date', 'due_date', 'status', 'sequence_id',
                               'payment_status'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'smart_buttons': [
                {'label': 'SO', 'model': 'sales.order', 'icon': 'FileTextOutlined'},
                {'label': 'Detail Unit', 'model': 'project.project_unit_detail', 'icon': 'HomeOutlined'},
            ],
            'actions': [
                {'label': 'Print', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Cancel', 'color': 'primary', 'action': 'cancel', 'states': ['draft', 'confirmed', 'done']},
                {'label': 'Action', 'color': 'primary'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Faktur',
                'relation': 'invoice_lines',
                'summary': {
                    'columns': {'qty': 'sum', 'discount_percentage': 'avg', 'discount_amount': 'sum',
                                'tax_percentage': 'avg', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'manual_discount', 'tax', 'down_payment_amount'],
                    'inputs': ['manual_discount'],
                    'grand_total': 'grand_total',
                    'after_grand_total': ['due_amount'],
                    'child_details': {
                        'label': 'Pembayaran',
                        'data_key': '_receipt_details',
                        'model': 'accounting.customer_receipt',
                    },
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Faktur'
        verbose_name_plural = 'Faktur'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='accounting.customer_invoice', active=True, is_deleted=False).first()
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

    # ── Auto-fill Pembayaran Detail Unit ──

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_unit_detail_payments()

    def _sync_unit_detail_payments(self):
        """Autofill unit_detail_payment dari pembayaran invoice (customer_receipt).

        Hanya berlaku kalau invoice ter-link ke project.project_unit_detail.
        Sinkronisasi di-REPLACE total (hapus lama, buat ulang dari receipt aktif)
        supaya data pembayaran selalu mencerminkan receipt terkini.
        """
        if not self.unit_detail:
            return
        from core.models.project.unit_detail_payment import UnitDetailPayment
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine

        # Hapus semua payment lama milik unit_detail ini (hanya yang berasal dari invoice ini)
        UnitDetailPayment.objects.filter(
            unit_detail_id=self.unit_detail, is_deleted=False
        ).update(is_deleted=True)

        receipts = CustomerReceiptLine.objects.filter(
            invoice_id=self.pk, is_deleted=False
        ).filter(receipt_id__status__in=['confirmed', 'done']).select_related('receipt_id')

        seq = 0
        for line in receipts:
            seq += 1
            r = line.receipt_id
            method = r.payment_method
            UnitDetailPayment.objects.create(
                unit_detail_id=self.unit_detail,
                name=r.reference or f'#{r.pk}',
                payment_method=str(method) if method else '',
                payment_ref=r.payment_ref or '',
                amount=float(line.received_amount or 0),
                payment_date=r.payment_date,
            )

    # ── Computed Fields ──

    def _compute_summary(self):
        lines_data = getattr(self, '_tmp_one2many', {}).get('invoice_lines', [])

        def sum_lines(field):
            if lines_data:
                return sum(float(line.get(field, 0) or 0) for line in lines_data)
            fd = self._field_descriptors.get('invoice_lines')
            if self.pk and fd:
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    return sum(
                        float(getattr(line, field, 0) or 0)
                        for line in child_model.objects.filter(
                            **{fd.inverse_field: self.pk, 'is_deleted': False}
                        )
                    )
            return 0

        line_total = sum_lines('total')
        line_discount = sum_lines('discount_amount')
        line_tax = sum_lines('tax_amount')

        # Raw subtotal = sum(qty*price)
        raw_subtotal = line_total + line_discount - line_tax

        # Pre-tax base setelah line discounts
        after_line_disc = raw_subtotal - line_discount

        # Manual discount applied to pre-tax base
        manual_disc_pct = float(getattr(self, 'manual_discount', 0) or 0)
        manual_disc_amt = after_line_disc * (manual_disc_pct / 100)

        self.subtotal = raw_subtotal
        self.discount = line_discount
        self.tax = line_tax
        dp_amount = float(getattr(self, 'down_payment_amount', 0) or 0)
        self.grand_total = after_line_disc - manual_disc_amt + line_tax - dp_amount

    def _compute_down_payment(self):
        """Cari DP invoice untuk SO yang sama, ambil grand_total-nya."""
        if not self.sales_order or self.is_down_payment:
            self.down_payment_amount = 0
            return
        dp_inv = self.__class__.objects.filter(
            sales_order=self.sales_order,
            is_down_payment=True,
            is_deleted=False,
        ).first()
        self.down_payment_amount = dp_inv.grand_total if dp_inv else 0

    def _compute_payment_summary(self):
        """Hitung due_amount & payment_status berdasarkan grand_total dan paid_amount."""
        paid = float(getattr(self, 'paid_amount', 0) or 0)
        grand = float(getattr(self, 'grand_total', 0) or 0)
        self.due_amount = max(grand - paid, 0)
        if paid <= 0:
            self.payment_status = 'unpaid'
        elif paid >= grand:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'

    # ── Legacy Actions ──

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/accounting.customer_invoice/{self.pk}/preview/',
            'pdf_url': f'/api/print/accounting.customer_invoice/{self.pk}/download/',
        }

    def _print_context(self):
        data = super()._print_context()
        lines = data.get('invoice_lines', [])
        lines_total = sum(float(line.get('total', 0) or 0) for line in lines)
        lines_discount = sum(float(line.get('discount_amount', 0) or 0) for line in lines)
        lines_tax = sum(float(line.get('tax_amount', 0) or 0) for line in lines)
        manual_disc_pct = float(data.get('manual_discount', 0) or 0)
        dp_amount = float(data.get('down_payment_amount', 0) or 0)

        data['subtotal'] = lines_total
        data['discount'] = lines_discount
        data['tax'] = lines_tax
        data['manual_discount'] = lines_total * (manual_disc_pct / 100)
        data['grand_total'] = lines_total - lines_discount + lines_tax - data['manual_discount'] - dp_amount
        return data

    def to_record(self):
        """Sertakan daftar receipt terkait untuk child_details di summary."""
        data = super().to_record()
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine
        lines = CustomerReceiptLine.objects.filter(
            invoice_id=self.pk, is_deleted=False
        ).exclude(receipt_id__status='cancelled').order_by('pk')
        data['_receipt_details'] = []
        for line in lines:
            r = line.receipt_id
            data['_receipt_details'].append({
                'id': r.pk,
                'label': 'Penerimaan',
                'ref': r.reference or f'#{r.pk}',
                'amount': float(line.received_amount or 0),
            })
        return data
