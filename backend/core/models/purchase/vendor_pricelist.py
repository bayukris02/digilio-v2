from django.db import models
from core.fields import (
    CharField, DateField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class VendorPricelist(BaseModel):
    """Daftar harga vendor — autofill harga di Purchase Order.

    Matching di PO: vendor + product sama, dan qty PO >= min_qty.
    Dari beberapa entry yang cocok, dipakai min_qty TERBESAR yang <= qty PO.
    """

    _model_name = 'purchase.vendor_pricelist'

    def __str__(self):
        vendor = getattr(self, 'vendor', None)
        product = getattr(self, 'product', None)
        vname = str(vendor) if vendor else '-'
        pname = str(product) if product else '-'
        return f'{vname} - {pname} (min {getattr(self, "min_qty", 0) or 0})'

    _fields = {
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom'},
        ),
        'min_qty': FloatField(label='Min Qty', default=1),
        'uom': CharField(label='UOM', default='pcs'),
        'unit_price': MonetaryField(label='Unit Price', currency='IDR', required=True),
        'start_date': DateField(
            label='Periode Mulai',
            required=False,
            help_text='Kosongkan jika berlaku sejak awal',
        ),
        'end_date': DateField(
            label='Periode Selesai',
            required=False,
            help_text='Kosongkan jika aktif terus (tanpa batas akhir)',
        ),
    }

    _list_view = {
        'columns': ['vendor', 'product', 'min_qty', 'uom', 'unit_price', 'start_date', 'end_date'],
        'filters': ['vendor', 'product'],
        'default_sort': ['vendor', 'product', 'min_qty'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['vendor', 'product', 'min_qty', 'uom', 'unit_price',
                               'start_date', 'end_date'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'color': 'green', 'action': 'print'},
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Vendor Pricelist'
        verbose_name_plural = 'Vendor Pricelists'

    def save(self, *args, **kwargs):
        """Validasi unik: kombinasi (vendor, product, min_qty) tidak boleh duplikat."""
        vendor = getattr(self, 'vendor', None)
        product = getattr(self, 'product', None)
        min_qty = float(getattr(self, 'min_qty', 0) or 0)
        if vendor and product:
            qs = self.__class__.objects.filter(
                vendor=vendor,
                product=product,
                min_qty=min_qty,
                is_deleted=False,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValueError(
                    'Vendor, Produk, dan Min Qty yang sama sudah ada di Price List. '
                    'Ubah Min Qty untuk membuat harga bertingkat.'
                )
        super().save(*args, **kwargs)
