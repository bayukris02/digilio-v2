from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class CustomerReceipt(BaseModel):
    """Penerimaan dari customer — menerima pembayaran satu atau lebih Customer Invoice."""

    _model_name = 'accounting.customer_receipt'
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
            help_text='Pilih format nomor dokumen penerimaan',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
            confirm_onchange={
                'message': 'Mengganti customer akan mereset semua alokasi. Lanjutkan?',
                'reset_relations': ['receipt_lines'],
            },
        ),
        'quick_sales': Many2OneField(
            label='Quick Sales',
            relation='sales.quick_sales',
            required=False,
        ),
        'address': TextField(label='Alamat Customer', virtual=True),
        'code': TextField(label='Kode Customer', virtual=True),
        'payment_date': DateField(label='Tanggal Penerimaan', required=True),
        'payment_method': Many2OneField(
            label='Metode Pembayaran',
            relation='accounting.payment_method',
            required=True,
        ),
        'payment_ref': CharField(label='Referensi Pembayaran', placeholder='No. Cek / Transfer / dll'),
        'currency': CharField(label='Currency', default='IDR'),
        'total_amount': MonetaryField(
            label='Total Penerimaan', currency='IDR',
            compute='_compute_total_receipt',
        ),
        'total_allocation': MonetaryField(
            label='Total Alokasi', currency='IDR',
            compute='_compute_summary',
        ),
        'remaining_amount': MonetaryField(
            label='Sisa Alokasi', currency='IDR',
            compute='_compute_summary',
        ),

        'receipt_lines': One2ManyField(
            label='Baris Penerimaan',
            relation='accounting.customer_receipt_line',
            inverse_field='receipt_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'customer', 'payment_date', 'payment_method', 'status', 'total_amount'],
        'filters': ['status', 'customer', 'payment_method', 'payment_date'],
        'group_by': ['status', 'customer'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'customer', 'code', 'address',
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
                'label': 'Alokasi Penerimaan',
                'relation': 'receipt_lines',
                'add_line_guard': ['customer'],
                'columns': [{'name': 'invoice_id', 'display_field': 'reference'}, 'customer_name', 'due_amount', 'received_amount'],
                'summary': {
                    'columns': {'received_amount': 'sum'},
                    'grand_total': 'total_amount',
                    'compute_deps': ['total_amount'],
                    'after_grand_total': ['total_allocation', 'remaining_amount'],
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Penerimaan'
        verbose_name_plural = 'Penerimaan'

    # ── Config ──

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(
            model_ref='accounting.customer_receipt', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    def save(self, *args, **kwargs):
        """Setelah status ter-persist, sync pembayaran ke Detail Unit terkait."""
        super().save(*args, **kwargs)
        self._sync_invoice_unit_detail_payments()

    def _sync_invoice_unit_detail_payments(self):
        """Sync Tab Pembayaran Detail Unit untuk invoice yang dialokasikan.

        Dipanggil SETELAH save sehingga status receipt (confirmed/done/cancelled)
        sudah final di DB — menghindari race dengan framework yang set status
        sebelum effect dijalankan (model_api transition handler).
        """
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine
        seen = set()
        for line in CustomerReceiptLine.objects.filter(
            receipt_id=self.pk, is_deleted=False
        ).select_related('invoice_id'):
            inv = line.invoice_id
            if inv and inv.unit_detail and inv.pk not in seen:
                seen.add(inv.pk)
                inv._sync_unit_detail_payments()

    def _compute_total_receipt(self):
        """Total Receipt is set manually by the user — no auto-computation needed.
        This compute method exists so the field is included in get_computed_fields(),
        allowing the SummaryCard to display the value via the compute API."""
        pass

    def _compute_summary(self):
        """Hitung Total Allocation (sum received_amount dari lines) dan Remaining Amount."""
        from decimal import Decimal
        lines_data = getattr(self, '_tmp_one2many', {}).get('receipt_lines', [])

        # Fallback ke DB jika tidak ada tmp data
        if not lines_data and self.pk:
            fd = self._field_descriptors.get('receipt_lines')
            if fd:
                from core.model_meta import ErpModelBase
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    db_lines = child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    )
                    for line in db_lines:
                        lines_data.append({
                            'received_amount': float(getattr(line, 'received_amount', 0) or 0),
                        })

        total_alloc = sum(
            float(l.get('received_amount', 0) or 0) for l in lines_data
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

        # Update paid_amount pada setiap invoice yang dialokasikan
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine
        lines = CustomerReceiptLine.objects.filter(
            receipt_id=self.pk, is_deleted=False
        )
        for line in lines:
            invoice = line.invoice_id
            if invoice:
                invoice.paid_amount = (invoice.paid_amount or 0) + (line.received_amount or 0)
                invoice._run_compute()
                invoice.save()

        # Baris cicilan yang dialokasikan → Lunas/Sebagian
        self._sync_installment_statuses()

    def _effect_cancel(self):
        """Reverse paid_amount pada invoice yang dialokasikan saat receipt di-cancel."""
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine
        lines = CustomerReceiptLine.objects.filter(
            receipt_id=self.pk, is_deleted=False
        )
        for line in lines:
            invoice = line.invoice_id
            if invoice:
                invoice.paid_amount = max((invoice.paid_amount or 0) - (line.received_amount or 0), 0)
                invoice._run_compute()
                invoice.save()

        # Baris cicilan dihitung ulang TANPA receipt ini (akan berstatus cancelled)
        self._sync_installment_statuses(reverse=True)

    def _sync_installment_statuses(self, reverse=False):
        """Update payment_status baris cicilan dari total alokasi receipt.

        reverse=True dipakai saat cancel: alokasi receipt ini dikeluarkan
        (status di DB belum berubah ketika effect berjalan).
        Status: paid bila total diterima >= nominal cicilan, partial bila > 0.
        """
        from django.db.models import Sum
        from core.models.accounting.customer_invoice_installment import CustomerInvoiceInstallment
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine

        qs = CustomerReceiptLine.objects.filter(
            is_deleted=False
        ).exclude(installment_id__isnull=True)
        if reverse:
            qs = qs.exclude(receipt_id=self.pk)
        else:
            qs = qs.filter(receipt_id__status__in=['confirmed', 'done'])

        # Semua cicilan yang tersentuh: hasil agregasi qs + baris receipt ini
        # (saat confirm baris ini ditambah manual; saat cancel dikecualikan
        # sehingga totalnya 0 → status balik unpaid).
        inst_ids = set()
        totals = {}
        for row in qs.values('installment_id_id').annotate(total=Sum('received_amount')):
            inst_ids.add(row['installment_id_id'])
            totals[row['installment_id_id']] = float(row['total'] or 0)
        for line in CustomerReceiptLine.objects.filter(
            receipt_id=self.pk, is_deleted=False
        ).exclude(installment_id__isnull=True):
            inst_ids.add(line.installment_id_id)
            if not reverse:
                totals[line.installment_id_id] = (
                    totals.get(line.installment_id_id, 0) + float(line.received_amount or 0)
                )

        for inst_id in inst_ids:
            inst = CustomerInvoiceInstallment.objects.filter(
                pk=inst_id, is_deleted=False
            ).first()
            if not inst:
                continue
            total = totals.get(inst_id, 0.0)
            nominal = float(inst.amount or 0)
            if total + 0.005 >= nominal:
                status = 'paid'
            elif total > 0:
                status = 'partial'
            else:
                status = 'unpaid'
            if inst.payment_status != status:
                inst.payment_status = status
                inst.save(update_fields=['payment_status'])

    # ── Legacy Actions ──

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/accounting.customer_receipt/{self.pk}/preview/',
            'pdf_url': f'/api/print/accounting.customer_receipt/{self.pk}/download/',
        }

    def _print_context(self):
        data = super()._print_context()
        return data
