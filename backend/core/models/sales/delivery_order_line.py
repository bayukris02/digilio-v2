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
            label='Delivery Order',
            relation='sales.delivery_order',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'unit_price'},
        ),
        'name': TextField(label='Description'),
        'delivered_qty': FloatField(
            label='Delivered Qty', default=0,
            editable_statuses=['draft', 'waiting'],
        ),
        'unit_price': MonetaryField(label='Unit Price', currency='IDR'),
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
        verbose_name = 'Delivery Order Line'
        verbose_name_plural = 'Delivery Order Lines'
