from django.db import models
from core.fields import (
    CharField, TextField, BooleanField, MonetaryField,
    SelectionField, FloatField, Many2OneField,
)
from core.model_meta import BaseModel


class Product(BaseModel):
    _model_name = 'inventory.product'
    _display_name = 'code'

    _fields = {
        'name': CharField(label='Nama Produk', required=True),
        'code': CharField(label='SKU / Kode'),
        'description': TextField(label='Deskripsi'),
        'category': Many2OneField(
            label='Kategori',
            relation='inventory.product_category',
        ),
        'price': MonetaryField(label='Harga Jual', currency='IDR'),
        'cost': MonetaryField(label='Harga Beli', currency='IDR'),
        'uom': CharField(label='Satuan', default='pcs'),
        'weight': FloatField(label='Berat (kg)'),
        'is_active': BooleanField(label='Aktif', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'category', 'price', 'uom', 'is_active'],
        'filters': ['category', 'is_active'],
        'group_by': ['category'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'code', 'category', 'price', 'cost', 'uom', 'weight', 'is_active'],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'details',
                'label': 'Detail',
                'fields': ['description'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'

    def __str__(self):
        return self.name or ''
