from django.db import models
from core.fields import (
    CharField, TextField, BooleanField, Many2OneField,
)
from core.model_meta import BaseModel


class PaymentMethod(BaseModel):
    """Master data metode pembayaran — Cash, Transfer, Cek, dll."""

    _model_name = 'accounting.payment_method'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Metode', required=True),
        'code': CharField(label='Kode'),
        'account': Many2OneField(
            label='Akun COA',
            relation='accounting.chart_of_account',
            help_text='Akun default untuk metode pembayaran ini',
        ),
        'description': TextField(label='Deskripsi'),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'account', 'is_active'],
        'filters': ['is_active'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'code', 'account', 'is_active'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['description'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'

    def __str__(self):
        return self.name or ''
