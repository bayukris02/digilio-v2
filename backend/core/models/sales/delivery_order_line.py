from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class DeliveryOrderLine(BaseModel):
    _model_name = 'sales.delivery.order.line'

    _fields = {
        'delivery_id': Many2OneField(
            label='Pengiriman Barang',
            relation='sales.delivery_order',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'unit_price'},
        ),
        'name': TextField(label='Deskripsi'),
        'delivered_qty': FloatField(
            label='Qty Terkirim', default=0,
            editable_statuses=['draft', 'waiting'],
        ),
        'unit_price': MonetaryField(label='Harga Satuan', currency='IDR'),
    }

    _list_view = {
        'columns': ['product', 'name', 'delivered_qty', 'unit_price'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'delivered_qty', 'unit_price'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Pengiriman Barang'
        verbose_name_plural = 'Baris Pengiriman Barang'
