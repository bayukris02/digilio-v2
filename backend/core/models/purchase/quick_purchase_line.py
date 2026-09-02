from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField, PercentageField,
    Many2OneField,
)
from core.model_meta import BaseModel


class QuickPurchaseLine(BaseModel):
    _model_name = 'purchase.quick_purchase.line'

    _fields = {
        'quick_purchase_id': Many2OneField(
            label='Quick Purchase',
            relation='purchase.quick_purchase',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'price'},
        ),
        'name': TextField(label='Deskripsi'),
        'qty': FloatField(label='Jumlah', default=1),
        'uom': CharField(label='UOM', default='pcs'),
        'price': MonetaryField(label='Harga Satuan', currency='IDR'),
        'discount_percentage': PercentageField(label='Diskon (%)', default=0),
        'discount_amount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_total'),
        'taxes': Many2OneField(
            label='Pajak',
            relation='accounting.tax',
            required=False,
            allow_duplicate=True,
            help_text='Pilih pajak (PPN, PPh, dll)',
        ),
        'tax_amount': MonetaryField(label='Nilai Pajak', currency='IDR', compute='_compute_total', depends=['qty', 'price', 'discount_amount', 'taxes']),
        'total': MonetaryField(label='Total', currency='IDR', compute='_compute_total', depends=['qty', 'price', 'discount_amount', 'tax_amount']),
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
        verbose_name = 'Quick Purchase Line'
        verbose_name_plural = 'Quick Purchase Lines'

    def _compute_total(self):
        """Compute discount, tax, and total from stored discount_amount."""
        qty = float(self.qty or 0)
        price = float(self.price or 0)
        subtotal = qty * price

        # Hitung discount: jika ada %, override stored discount_amount
        disc_pct = float(getattr(self, 'discount_percentage', 0) or 0)
        if disc_pct > 0:
            disc_amt = subtotal * (disc_pct / 100)
        else:
            disc_amt = float(self.discount_amount or 0)

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
        self.total = round(subtotal - disc_amt + tax_amt, 2)
