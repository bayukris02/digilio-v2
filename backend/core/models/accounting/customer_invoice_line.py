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
        base = subtotal - disc_amt

        # Pajak: tarif pajak terpilih (many2one), dipisah include vs exclude.
        # Include → harga di baris SUDAH termasuk pajak: dasar = base/(1+rate),
        #           porsi pajak TIDAK menambah total tagihan.
        # Exclude → pajak biasa: net_base × rate, ditambahkan ke total.
        from core.models.accounting.tax import taxes_include_exclude
        tax_id = getattr(self, 'taxes_id', None)
        inc_rate, exc_rate = taxes_include_exclude(tax_id)

        if inc_rate > 0:
            net_base = base / (1 + inc_rate / 100.0)
            inc_tax = base - net_base
        else:
            net_base = base
            inc_tax = 0.0
        exc_tax = net_base * (exc_rate / 100.0)

        self.discount_amount = round(disc_amt, 2)
        self.tax_amount = round(inc_tax + exc_tax, 2)
        # total = harga (sudah termasuk include tax) + exclude tax
        self.total = round(base + exc_tax, 2)
