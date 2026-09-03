from django.db import models
from core.fields import (
    CharField, TextField, DateField, IntegerField, MonetaryField,
    SelectionField, Many2OneField,
)
from core.model_meta import BaseModel


class CustomerInvoiceInstallment(BaseModel):
    _model_name = 'accounting.customer_invoice_installment'

    _fields = {
        'invoice_id': Many2OneField(
            label='Faktur',
            relation='accounting.customer_invoice',
            required=True,
        ),
        'term_no': IntegerField(label='Cicilan Ke'),
        'due_date': DateField(label='Jatuh Tempo'),
        'amount': MonetaryField(label='Nominal', currency='IDR'),
        'note': TextField(label='Catatan'),
        'payment_status': SelectionField(
            label='Status Pembayaran',
            options=[('unpaid', 'Belum Dibayar'), ('partial', 'Sebagian'), ('paid', 'Lunas')],
            default='unpaid',
            colors={'unpaid': 'red', 'partial': 'orange', 'paid': 'green'},
        ),
    }

    _list_view = {
        'columns': ['term_no', 'due_date', 'amount', 'note', 'payment_status'],
        'default_sort': ['term_no'],
    }

    _form_view = {
        'header': {
            'fields': ['invoice_id', 'term_no', 'due_date', 'amount', 'note', 'payment_status'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Cicilan'
        verbose_name_plural = 'Cicilan'

    def to_record(self):
        """Sertakan _paid/_remaining (dari receipt confirmed/done) — dipakai
        info wizard Input Penerimaan & blokir tombol saat lunas."""
        data = super().to_record()
        from django.db.models import Sum
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine
        total = CustomerReceiptLine.objects.filter(
            installment_id=self.pk, is_deleted=False,
            receipt_id__status__in=['confirmed', 'done'],
        ).aggregate(total=Sum('received_amount'))['total'] or 0
        data['_paid'] = float(total or 0)
        data['_remaining'] = max(float(self.amount or 0) - float(total or 0), 0)
        return data
