from django.db import models
from core.fields import (
    CharField, TextField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class OrderTemplate(BaseModel):
    """Template Purchase Order — daftar produk standar yang sering dipesan."""

    _model_name = 'purchase.order_template'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Template', required=True),
        'notes': TextField(label='Catatan', chatter_show=False),
        'template_lines': One2ManyField(
            label='Baris Template',
            relation='purchase.order.template.line',
            inverse_field='template_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'notes'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'notes'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'color': 'green', 'action': 'print'},
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Template',
                'relation': 'template_lines',
                'columns': ['product', 'name', 'uom', 'qty'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Order Template'
        verbose_name_plural = 'Order Templates'
