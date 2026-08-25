from django.db import models
from core.fields import (
    CharField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class SalesPricelistLine(BaseModel):
    """Baris harga dalam pricelist — product + rentang qty + fix price."""

    _model_name = 'sales.pricelist.line'

    _fields = {
        'pricelist_id': Many2OneField(
            label='Pricelist',
            relation='sales.pricelist',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom'},
        ),
        'uom': CharField(label='UOM', default='pcs'),
        'min_qty': FloatField(label='Min Qty', default=1),
        'max_qty': FloatField(label='Max Qty', required=False,
            help_text='Kosongkan jika tanpa batas atas'),
        'fix_price': MonetaryField(label='Fix Price', currency='IDR', required=True),
    }

    _list_view = {
        'columns': ['product', 'uom', 'min_qty', 'max_qty', 'fix_price'],
        'default_sort': ['product', 'min_qty'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'uom', 'min_qty', 'max_qty', 'fix_price'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Sales Pricelist Line'
        verbose_name_plural = 'Sales Pricelist Lines'

    def save(self, *args, **kwargs):
        """Validasi: min_qty tidak boleh melebihi max_qty (jika diisi)."""
        min_qty = float(getattr(self, 'min_qty', 0) or 0)
        max_qty = getattr(self, 'max_qty', None)
        if max_qty is not None and min_qty > float(max_qty or 0):
            raise ValueError('Min Qty tidak boleh lebih besar dari Max Qty.')
        super().save(*args, **kwargs)
