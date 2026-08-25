from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class GoodsReceiptLine(BaseModel):
    _model_name = 'purchase.goods_receipt.line'

    _fields = {
        'receipt_id': Many2OneField(
            label='Penerimaan Barang',
            relation='purchase.goods_receipt',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'unit_price'},
        ),
        'name': TextField(label='Deskripsi'),
        'received_qty': FloatField(label='Qty Diterima', default=0, editable_statuses=['draft', 'waiting']),
        'unit_price': MonetaryField(label='Harga Satuan', currency='IDR'),
    }

    _list_view = {
        'columns': ['product', 'name', 'received_qty', 'unit_price'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'received_qty', 'unit_price'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Penerimaan Barang'
        verbose_name_plural = 'Baris Penerimaan Barang'
