from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class VendorBill(BaseModel):
    _model_name = 'accounting.vendor_bill'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
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
            'name': 'cancel',
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen tagihan',
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
        'bill_date': DateField(label='Bill Date'),
        'due_date': DateField(label='Due Date'),
        'description': TextField(label='Description'),
        'notes': TextField(label='Notes', chatter_show=False),
        'purchase_order': Many2OneField(
            label='Purchase Order',
            relation='purchase.order',
            required=False,
        ),
        'project': Many2OneField(
            label='Project',
            relation='project.project',
            required=False,
            help_text='Project asal tagihan (otomatis dari wizard Buat Tagihan)',
        ),
        'project_line': Many2OneField(
            label='Milestone',
            relation='project.project_line',
            required=False,
            help_text='Milestone terkait (otomatis dari wizard Buat Tagihan)',
        ),

        # ── Down Payment ──
        'is_down_payment': BooleanField(label='DP Bill', default=False),
        'down_payment_amount': MonetaryField(label='Down Payment', currency='IDR',
            compute='_compute_down_payment', depends=['purchase_order']),

        # ── Summary fields ──
        'subtotal': MonetaryField(label='Subtotal', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'discount': MonetaryField(label='Discount', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'tax': MonetaryField(label='Tax', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'manual_discount': FloatField(label='Manual Disc (%)', default=0),
        'grand_total': MonetaryField(label='Grand Total', currency='IDR',
            compute='_compute_summary', depends=['bill_lines', 'manual_discount', 'down_payment_amount']),

        # ── Payment fields ──
        'due_amount': MonetaryField(label='Amount Due', currency='IDR',
            compute='_compute_payment_summary', depends=['grand_total', 'paid_amount']),
        'paid_amount': MonetaryField(label='Paid', currency='IDR', default=0),
        'payment_status': SelectionField(
            label='Payment Status',
            options=[('unpaid', 'Unpaid'), ('partial', 'Partial'), ('paid', 'Paid')],
            compute='_compute_payment_summary',
            depends=['grand_total', 'paid_amount'],
            default='unpaid',
            colors={'unpaid': 'red', 'partial': 'orange', 'paid': 'green'},
        ),

        'bill_lines': One2ManyField(
            label='Bill Lines',
            relation='accounting.vendor_bill_line',
            inverse_field='bill_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'project', 'project_line', 'purchase_order', 'vendor', 'bill_date', 'due_date', 'status', 'grand_total', 'due_amount', 'payment_status'],
        'filters': ['status', 'vendor', 'bill_date', 'payment_status', 'project', 'project_line'],
        'group_by': ['status', 'vendor', 'payment_status', 'project', 'project_line'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'project', 'project_line', 'purchase_order', 'vendor', 'code', 'address',
                               'bill_date', 'due_date', 'status', 'sequence_id',
                               'payment_status'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['notes'],
                },
            ],
            'smart_buttons': [
            {'label': 'Purchase Order', 'model': 'purchase.order', 'icon': 'FileTextOutlined'},
        ],
        'actions': [
                {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'primary', 'action': 'cancel', 'states': ['draft', 'confirmed']},
                {'label': 'Action', 'icon': 'MoreOutlined', 'color': 'primary'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Bill Lines',
                'relation': 'bill_lines',
                'summary': {
                    'columns': {'qty': 'sum', 'discount_percentage': 'avg', 'discount_amount': 'sum',
                                'tax_percentage': 'avg', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'manual_discount', 'tax', 'down_payment_amount'],
                    'inputs': ['manual_discount'],
                    'grand_total': 'grand_total',
                    'after_grand_total': ['due_amount'],
                    'child_details': {
                        'label': 'Payments',
                        'data_key': '_payment_details',
                        'model': 'accounting.vendor_payment',
                    },
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Vendor Bill'
        verbose_name_plural = 'Vendor Bills'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='accounting.vendor_bill', active=True, is_deleted=False).first()
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

    # ── Computed Fields ──

    def _compute_summary(self):
        lines_data = getattr(self, '_tmp_one2many', {}).get('bill_lines', [])

        def sum_lines(field):
            if lines_data:
                return sum(float(line.get(field, 0) or 0) for line in lines_data)
            fd = self._field_descriptors.get('bill_lines')
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
        raw_subtotal = line_total

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
        """Cari DP bill untuk PO yang sama, ambil grand_total-nya."""
        if not self.purchase_order or self.is_down_payment:
            self.down_payment_amount = 0
            return
        dp_bill = self.__class__.objects.filter(
            purchase_order=self.purchase_order,
            is_down_payment=True,
            is_deleted=False,
        ).first()
        self.down_payment_amount = dp_bill.grand_total if dp_bill else 0

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

    # ── Auto Progress Milestone ──

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_milestone_progress()

    def _sync_milestone_progress(self):
        """Auto-update progress milestone = rata-rata kontribusi semua dokumen aktif.

        Kontribusi per bill: draft 0% / confirmed 50% / paid 100%.
        Bill cancelled di-exclude; kalau tidak ada dokumen aktif → progress 0.
        """
        line = self.project_line
        if not line:
            return

        bills = self.__class__.objects.filter(
            project_line=line, is_deleted=False
        ).exclude(status='cancelled')
        if not bills.exists():
            line.progress = 0.0
            line.save(update_fields=['progress'])
            return

        total = sum(
            100.0 if b.payment_status == 'paid'
            else 50.0 if b.status == 'confirmed'
            else 0.0
            for b in bills
        )
        avg = total / bills.count()
        line.progress = round(avg, 1)
        line.save(update_fields=['progress'])

    # ── Legacy Actions ──

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/accounting.vendor_bill/{self.pk}/preview/',
            'pdf_url': f'/api/print/accounting.vendor_bill/{self.pk}/download/',
        }

    def _print_context(self):
        data = super()._print_context()
        lines = data.get('bill_lines', [])
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
        """Sertakan daftar payment terkait untuk child_details di summary."""
        data = super().to_record()
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        lines = VendorPaymentLine.objects.filter(
            bill_id=self.pk, is_deleted=False
        ).exclude(payment_id__status='cancelled').order_by('pk')
        data['_payment_details'] = []
        for line in lines:
            p = line.payment_id
            data['_payment_details'].append({
                'id': p.pk,
                'label': 'Payment',
                'ref': p.reference or f'#{p.pk}',
                'amount': float(line.paid_amount or 0),
            })
        return data
