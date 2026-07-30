from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class PurchaseRequestLine(BaseModel):
    _model_name = 'purchase.request.line'

    _fields = {
        'request_id': Many2OneField(
            label='Purchase Request',
            relation='purchase.request',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'name': 'name'},
        ),
        'description': TextField(label='Description'),
        'qty': FloatField(label='Quantity', default=1),
        'estimated_cost': MonetaryField(label='Estimated Cost', currency='IDR'),
        'total': MonetaryField(
            label='Total', currency='IDR',
            compute='_compute_total',
            depends=['qty', 'estimated_cost'],
        ),
    }

    _list_view = {
        'columns': ['product', 'description', 'qty', 'estimated_cost', 'total'],
        'default_sort': ['id'],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Request Line'
        verbose_name_plural = 'Purchase Request Lines'

    def _compute_total(self):
        qty = float(self.qty or 0)
        cost = float(self.estimated_cost or 0)
        self.total = round(qty * cost, 2)
