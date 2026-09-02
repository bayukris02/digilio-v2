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
            label='Faktur',
            relation='accounting.customer_invoice',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=False,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'price'},
        ),
        'name': TextField(label='Deskripsi'),
        'qty': FloatField(label='Jumlah', default=1),
        'uom': CharField(label='UOM', default='pcs'),
        'price': MonetaryField(label='Harga Satuan', currency='IDR'),
        'discount_percentage': FloatField(label='Diskon (%)', default=0),
        'discount_amount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage']),
        'taxes': Many2OneField(
            label='Pajak',
            relation='accounting.tax',
            required=False,
            allow_duplicate=True,
            help_text='Pilih pajak (PPN, PPh, dll)',
        ),
        'tax_amount': MonetaryField(label='Nilai Pajak', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'taxes']),
        'total': MonetaryField(label='Total', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'taxes']),
    }

    _list_view = {
        'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'taxes', 'tax_amount', 'total'],
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
        verbose_name = 'Baris Faktur'
        verbose_name_plural = 'Baris Faktur'

    def _compute_total(self):
        qty = float(self.qty or 0)
        price = float(self.price or 0)
        subtotal = qty * price

        disc_pct = float(getattr(self, 'discount_percentage', 0) or 0)
        disc_amt = subtotal * (disc_pct / 100)
        taxable = subtotal - disc_amt

        # Pajak: tarif pajak terpilih (many2one) × dasar pengenaan pajak
        from core.models.accounting.tax import Tax
        tax_id = getattr(self, 'taxes_id', None)
        tax_pct = 0.0
        if tax_id:
            tax = Tax.objects.filter(pk=tax_id, is_active=True).first()
            if tax:
                tax_pct = float(tax.rate or 0)
        tax_amt = taxable * (tax_pct / 100)

        self.discount_amount = round(disc_amt, 2)
        self.tax_amount = round(tax_amt, 2)
        # total = subtotal - diskon + pajak (konsisten dgn PO / QuickSalesLine)
        self.total = round(subtotal - disc_amt + tax_amt, 2)
