from django.db import models
from core.fields import (
    CharField, TextField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class CustomerReceiptLine(BaseModel):
    """Baris alokasi penerimaan — menghubungkan Receipt dengan Customer Invoice."""

    _model_name = 'accounting.customer_receipt_line'

    _fields = {
        'receipt_id': Many2OneField(
            label='Penerimaan',
            relation='accounting.customer_receipt',
            required=True,
        ),
        'invoice_id': Many2OneField(
            label='Faktur',
            relation='accounting.customer_invoice',
            required=True,
            domain={'customer': 'customer', 'status': 'confirmed'},
            autofill={'due_amount': 'due_amount', 'customer_name': 'customer'},
        ),
        'installment_id': Many2OneField(
            label='Cicilan',
            relation='accounting.customer_invoice_installment',
            required=False,
            editable_statuses=[],
            help_text='Baris cicilan yang dibayar (alur Input Penerimaan di tab Cicilan Faktur)',
        ),
        'customer_name': TextField(
            label='Customer',
            virtual=True,
            editable_statuses=[],
        ),
        'due_amount': MonetaryField(
            label='Sisa Tagihan', currency='IDR',
            virtual=True,
            editable_statuses=[],
            compute='_compute_total',
        ),
        'received_amount': MonetaryField(
            label='Jumlah Diterima', currency='IDR',
            required=True,
        ),
    }

    _list_view = {
        'columns': ['invoice_id', 'customer_name', 'due_amount', 'received_amount'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['invoice_id', 'received_amount'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Penerimaan'
        verbose_name_plural = 'Baris Penerimaan'

    def _compute_total(self):
        """Populate customer_name/due_amount dari invoice & validasi received_amount ≤ due_amount."""
        invoice = getattr(self, 'invoice_id', None)
        if invoice:
            self.customer_name = str(invoice.customer.name) if invoice.customer else ''
            self.due_amount = float(invoice.due_amount or 0)

        received = float(self.received_amount or 0)
        due = float(getattr(self, 'due_amount', 0) or 0)
        if received > due > 0:
            raise ValueError(
                f'Penerimaan ({received:,.0f}) melebihi Sisa Tagihan ({due:,.0f}).'
            )

    def to_record(self):
        data = super().to_record()
        # Populate customer_name & due_amount from invoice
        invoice_id = getattr(self, 'invoice_id', None)
        if invoice_id and hasattr(invoice_id, 'customer'):
            data['customer_name'] = str(invoice_id.customer.name) if invoice_id.customer else ''
        if invoice_id:
            data['due_amount'] = float(invoice_id.due_amount or 0)
        return data
