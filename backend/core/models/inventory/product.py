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
        'name': CharField(label='Product Name', required=True),
        'code': CharField(label='SKU / Code'),
        'description': TextField(label='Description'),
        'category': Many2OneField(
            label='Category',
            relation='inventory.product_category',
        ),
        'price': MonetaryField(label='Sales Price', currency='IDR'),
        'cost': MonetaryField(label='Cost', currency='IDR'),
        'uom': CharField(label='Unit of Measure', default='pcs'),
        'weight': FloatField(label='Weight (kg)'),
        'is_active': BooleanField(label='Active', default=True),
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
                'label': 'Details',
                'fields': ['description'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name or ''
