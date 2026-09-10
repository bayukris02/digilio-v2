from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class VendorBillLine(BaseModel):
    _model_name = 'accounting.vendor_bill_line'

    _fields = {
        'bill_id': Many2OneField(
            label='Tagihan',
            relation='accounting.vendor_bill',
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
        verbose_name = 'Baris Tagihan'
        verbose_name_plural = 'Baris Tagihan'

    def _compute_total(self):
        qty = float(self.qty or 0)
        price = float(self.price or 0)
        subtotal = qty * price

        disc_pct = float(getattr(self, 'discount_percentage', 0) or 0)
        disc_amt = subtotal * (disc_pct / 100)
        taxable = subtotal - disc_amt

        # Pajak: include TIDAK menambah total (harga sudah termasuk pajak);
        # exclude ditambahkan di atas harga. Total baris Tagihan = harga bruto.
        from core.models.accounting.tax import line_tax_parts
        inc_tax, exc_tax, _net = line_tax_parts(taxable, getattr(self, 'taxes_id', None))

        self.discount_amount = round(disc_amt, 2)
        self.tax_amount = round(inc_tax + exc_tax, 2)
        self.total = round(qty * price, 2)
