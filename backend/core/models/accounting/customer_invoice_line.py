from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class CustomerInvoiceLine(BaseModel):
    _model_name = 'accounting.customer_invoice_line'

    _fields = {
        'invoice_id': Many2OneField(
            label='Customer Invoice',
            relation='accounting.customer_invoice',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=False,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'price'},
        ),
        'name': TextField(label='Description'),
        'qty': FloatField(label='Quantity', default=1),
        'uom': CharField(label='UOM', default='pcs'),
        'price': MonetaryField(label='Unit Price', currency='IDR'),
        'discount_percentage': FloatField(label='Disc (%)', default=0),
        'discount_amount': MonetaryField(label='Discount', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage']),
        'tax_percentage': FloatField(label='Tax (%)', default=0),
        'tax_amount': MonetaryField(label='Tax', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'tax_percentage']),
        'total': MonetaryField(label='Total', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'tax_percentage']),
    }

    _list_view = {
        'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'tax_percentage', 'tax_amount', 'total'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'qty', 'price', 'total'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Customer Invoice Line'
        verbose_name_plural = 'Customer Invoice Lines'

    def _compute_total(self):
        qty = float(self.qty or 0)
        price = float(self.price or 0)
        subtotal = qty * price

        disc_pct = float(getattr(self, 'discount_percentage', 0) or 0)
        disc_amt = subtotal * (disc_pct / 100)
        taxable = subtotal - disc_amt

        tax_pct = float(getattr(self, 'tax_percentage', 0) or 0)
        tax_amt = taxable * (tax_pct / 100)

        self.discount_amount = round(disc_amt, 2)
        self.tax_amount = round(tax_amt, 2)
        # total = subtotal - diskon + pajak (konsisten dgn PO / QuickSalesLine)
        self.total = round(subtotal - disc_amt + tax_amt, 2)
