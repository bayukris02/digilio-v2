"""Baris Terima Stock (Transfer Stock) model."""
from core.fields import CharField, TextField, FloatField, Many2OneField
from core.model_meta import BaseModel


class StockInLine(BaseModel):
    _model_name = 'inventory.stock_in.line'

    _fields = {
        'in_id': Many2OneField(
            label='Terima Stock',
            relation='inventory.stock_in',
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
        'received_qty': FloatField(label='Qty Diterima', default=0, editable_statuses=['draft', 'waiting']),
    }

    _list_view = {
        'columns': ['product', 'name', 'uom', 'received_qty'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'uom', 'received_qty'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Terima Stock'
        verbose_name_plural = 'Baris Terima Stock'
