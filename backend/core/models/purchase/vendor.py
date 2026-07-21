from django.db import models
from core.fields import (
    CharField, TextField, BooleanField, SelectionField,
)
from core.model_meta import BaseModel


class Vendor(BaseModel):
    _model_name = 'purchase.vendor'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Vendor', required=True),
        'code': CharField(label='Kode Vendor'),
        'address': TextField(label='Alamat Vendor'),
        'bill_method': SelectionField(
            label='Metode Tagihan',
            options=[('on_order', 'On Order'), ('on_receipt', 'On Receipt')],
            default='on_order',
        ),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'bill_method', 'address', 'is_active'],
        'filters': ['is_active', 'bill_method'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'code', 'bill_method', 'is_active'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['address'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __str__(self):
        return self.name or ''
