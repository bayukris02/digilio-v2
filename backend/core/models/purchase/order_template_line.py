from django.db import models
from core.fields import (
    CharField, TextField, FloatField,
    Many2OneField,
)
from core.model_meta import BaseModel


class OrderTemplateLine(BaseModel):
    """Baris template PO — produk standar dengan deskripsi & qty default."""

    _model_name = 'purchase.order.template.line'

    _fields = {
        'template_id': Many2OneField(
            label='Order Template',
            relation='purchase.order_template',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name'},
        ),
        'name': TextField(label='Deskripsi'),
        'uom': CharField(label='UOM', default='pcs'),
        'qty': FloatField(label='Jumlah', default=1),
    }

    _list_view = {
        'columns': ['product', 'name', 'uom', 'qty'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'name', 'uom', 'qty'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Order Template Line'
        verbose_name_plural = 'Order Template Lines'
