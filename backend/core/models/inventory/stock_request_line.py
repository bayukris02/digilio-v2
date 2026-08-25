"""Baris Request Transfer (Transfer Stock) model."""
from core.fields import CharField, TextField, FloatField, Many2OneField
from core.model_meta import BaseModel


class StockRequestLine(BaseModel):
    _model_name = 'inventory.stock_request.line'

    _fields = {
        'request_id': Many2OneField(
            label='Request Transfer',
            relation='inventory.stock_request',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name'},
        ),
        'name': TextField(label='Deskripsi'),
        'uom': CharField(label='UOM'),
        'request_qty': FloatField(label='Request Qty', default=0, editable_statuses=['draft']),
    }

    _list_view = {
        'columns': ['product', 'name', 'uom', 'request_qty'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'uom', 'request_qty'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Request Transfer'
        verbose_name_plural = 'Baris Request Transfer'
