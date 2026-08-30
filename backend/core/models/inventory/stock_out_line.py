"""Baris Stock Keluar (Transfer Stock) model."""
from core.fields import CharField, TextField, FloatField, Many2OneField
from core.model_meta import BaseModel


class StockOutLine(BaseModel):
    _model_name = 'inventory.stock_out.line'

    _fields = {
        'out_id': Many2OneField(
            label='Stock Keluar',
            relation='inventory.stock_out',
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
        'transfer_qty': FloatField(label='Transfer Qty', default=0, editable_statuses=['draft', 'waiting']),
    }

    _list_view = {
        'columns': ['product', 'name', 'uom', 'transfer_qty'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'uom', 'transfer_qty'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Stock Keluar'
        verbose_name_plural = 'Baris Stock Keluar'
