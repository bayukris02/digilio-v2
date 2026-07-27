from django.db import models
from core.fields import (
    CharField, TextField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class VendorPaymentLine(BaseModel):
    """Baris alokasi pembayaran — menghubungkan Payment dengan Vendor Bill."""

    _model_name = 'accounting.vendor_payment_line'

    _fields = {
        'payment_id': Many2OneField(
            label='Vendor Payment',
            relation='accounting.vendor_payment',
            required=True,
        ),
        'bill_id': Many2OneField(
            label='Bill',
            relation='accounting.vendor_bill',
            required=True,
            autofill={'due_amount': 'due_amount'},
        ),
        'vendor_name': TextField(
            label='Vendor',
            virtual=True,
        ),
        'due_amount': MonetaryField(
            label='Amount Due', currency='IDR',
            virtual=True,
        ),
        'paid_amount': MonetaryField(
            label='Payment', currency='IDR',
        ),
    }

    _list_view = {
        'columns': ['bill_id', 'vendor_name', 'due_amount', 'paid_amount'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['bill_id', 'paid_amount'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Vendor Payment Line'
        verbose_name_plural = 'Vendor Payment Lines'

    def to_record(self):
        data = super().to_record()
        # Populate vendor_name & due_amount from bill
        bill_id = getattr(self, 'bill_id', None)
        if bill_id and hasattr(bill_id, 'vendor'):
            data['vendor_name'] = str(bill_id.vendor.name) if bill_id.vendor else ''
        if bill_id:
            data['due_amount'] = float(bill_id.due_amount or 0)
        return data
