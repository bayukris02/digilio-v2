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
            label='Goods Receipt',
            relation='purchase.goods_receipt',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'unit_price'},
        ),
        'name': TextField(label='Description'),
        'received_qty': FloatField(label='Received Qty', default=0, editable_statuses=['draft', 'waiting']),
        'unit_price': MonetaryField(label='Unit Price', currency='IDR'),
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
        verbose_name = 'Goods Receipt Line'
        verbose_name_plural = 'Goods Receipt Lines'
