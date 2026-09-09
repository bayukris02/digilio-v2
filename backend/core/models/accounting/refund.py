"""Refund — catatan pengembalian dana dari transaksi keuangan.

Satu tabel untuk tiga sumber: accounting.vendor_payment, accounting.customer_receipt,
dan accounting.deposit. Relasi ditandai lewat salah satu FK sumber (sisanya NULL)
sehingga tetap ketahuan refund itu berasal dari transaksi yang mana.
Row dibuat via action "Refund" di model sumber — mendukung partial (banyak row
refund per sumber, maksimum = total sumber − total refund sebelumnya).
"""
from django.db.models import Sum
from core.fields import (
    CharField, TextField, DateField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


def create_refund(source, data=None, *, source_field, total_field='total_amount',
                  statuses=None):
    """Buat row Refund dari dokumen sumber (dipanggil action Refund).

    source: instance model sumber (vendor_payment / customer_receipt / deposit)
    data: payload wizard {amount, refund_date, payment_method, notes}
    source_field: nama FK di Refund yang mengarah ke model sumber
    total_field: field nominal total pada model sumber (default 'total_amount')
    statuses: tuple status yang boleh direfund; None = tanpa cek status.
    Guard partial: amount <= total sumber − total refund yg sudah ada.
    """
    data = data or {}
    try:
        amount = float(data.get('amount') or 0)
    except (TypeError, ValueError):
        amount = 0.0

    if statuses is not None and getattr(source, 'status', None) not in statuses:
        raise ValueError(
            'Refund hanya bisa dicatat untuk transaksi yang sudah dikonfirmasi/selesai.')

    if amount <= 0:
        raise ValueError('Nominal refund harus lebih dari 0.')

    refund_date = str(data.get('refund_date') or '')[:10]
    if not refund_date:
        from datetime import date as date_cls
        refund_date = str(date_cls.today())

    method_raw = data.get('payment_method')
    method_id = None
    try:
        method_id = int(method_raw)
    except (TypeError, ValueError):
        method_id = None

    notes = str(data.get('notes') or '').strip()

    total = float(getattr(source, total_field) or 0)
    refunded = float(
        Refund.objects.filter(
            is_deleted=False, **{source_field: source.pk}
        ).aggregate(total=Sum('amount'))['total'] or 0
    )
    available = total - refunded
    if amount - available > 0.005:
        raise ValueError(
            f'Melebihi sisa refund. Sisa yang bisa direfund: '
            f'Rp {available:,.0f} (total Rp {total:,.0f} − refund sebelumnya Rp {refunded:,.0f}).'
        )

    refund = Refund.objects.create(
        refund_date=refund_date,
        amount=round(amount, 2),
        payment_method_id=method_id,
        notes=notes,
        **{source_field: source},
    )
    return refund


class Refund(BaseModel):
    """Refund — satu baris = satu pengembalian dana dari transaksi sumber."""

    _model_name = 'accounting.refund'
    _display_name = 'reference'

    _fields = {
        'reference': CharField(label='No. Refund', editable_statuses=[], placeholder='Otomatis'),
        'refund_date': DateField(label='Tanggal Refund', required=True),
        'amount': MonetaryField(label='Nominal Refund', currency='IDR', required=True),
        'vendor_payment': Many2OneField(
            label='Dari Pembayaran Vendor',
            relation='accounting.vendor_payment',
            help_text='Terisi bila refund dari Pembayaran Vendor.',
        ),
        'customer_receipt': Many2OneField(
            label='Dari Penerimaan Customer',
            relation='accounting.customer_receipt',
            help_text='Terisi bila refund dari Penerimaan Customer.',
        ),
        'deposit': Many2OneField(
            label='Dari Deposit',
            relation='accounting.deposit',
            help_text='Terisi bila refund dari Deposit.',
        ),
        'payment_method': Many2OneField(
            label='Kas/Bank',
            relation='accounting.payment_method',
            help_text='Kas/bank yang menerima / mengeluarkan refund.',
        ),
        'notes': TextField(label='Catatan'),
    }

    _list_view = {
        'columns': ['reference', 'refund_date', 'vendor_payment', 'customer_receipt', 'deposit',
                    'payment_method', 'amount'],
        'filters': ['refund_date', 'vendor_payment', 'customer_receipt', 'deposit'],
        'default_sort': ['-refund_date', '-id'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'refund_date', 'amount', 'vendor_payment',
                               'customer_receipt', 'deposit', 'payment_method', 'notes'],
                },
            ],
            'smart_buttons': [
                {'label': 'Pembayaran Vendor', 'model': 'accounting.vendor_payment', 'icon': 'FileTextOutlined'},
                {'label': 'Penerimaan Customer', 'model': 'accounting.customer_receipt', 'icon': 'FileTextOutlined'},
                {'label': 'Deposit', 'model': 'accounting.deposit', 'icon': 'FileTextOutlined'},
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Refund'
        verbose_name_plural = 'Refund'

    @property
    def source_display(self):
        """Label sumber transaksi (refund dari trx yang mana)."""
        if self.vendor_payment_id:
            return f'Pembayaran Vendor · {self.vendor_payment}'
        if self.customer_receipt_id:
            return f'Penerimaan Customer · {self.customer_receipt}'
        if self.deposit_id:
            return f'Deposit · {self.deposit}'
        return '—'

    def save(self, *args, **kwargs):
        """Auto-generate No. Refund (RFND/Tahun/urutan) bila belum ada."""
        from datetime import date as date_cls
        super().save(*args, **kwargs)
        if not self.reference or str(self.reference).startswith('Draft#'):
            date_raw = str(self.refund_date or '')
            year = int(date_raw[:4]) if len(date_raw) >= 4 and date_raw[:4].isdigit() else date_cls.today().year
            self.reference = f'RFND/{year}/{self.pk:05d}'
            self.save(update_fields=['reference'])
        self._refresh_source_docs()

    def _refresh_source_docs(self):
        """Perbarui due_amount & payment_status invoice/bill yang tersentuh refund.

        Refund mengurangi pembayaran/penerimaan efektif → sisa tagihan naik.
        Dipanggil setelah refund dibuat/diubah/soft-delete (save).
        """
        try:
            if self.vendor_payment_id:
                from core.models.accounting.vendor_payment_line import VendorPaymentLine
                from core.models.accounting.vendor_bill import VendorBill
                bill_ids = list(VendorPaymentLine.objects.filter(
                    payment_id=self.vendor_payment_id, is_deleted=False
                ).values_list('bill_id', flat=True))
                for bill in VendorBill.objects.filter(pk__in=bill_ids, is_deleted=False):
                    bill._run_compute()
                    bill.save()
            elif self.customer_receipt_id:
                from core.models.accounting.customer_receipt_line import CustomerReceiptLine
                from core.models.accounting.customer_invoice import CustomerInvoice
                inv_ids = list(CustomerReceiptLine.objects.filter(
                    receipt_id=self.customer_receipt_id, is_deleted=False
                ).values_list('invoice_id', flat=True))
                for inv in CustomerInvoice.objects.filter(pk__in=inv_ids, is_deleted=False):
                    inv._run_compute()
                    inv.save()
        except Exception:
            pass

    def __str__(self):
        ref = self.reference or f'#{self.pk}'
        return f'{ref} — {self.source_display}'
