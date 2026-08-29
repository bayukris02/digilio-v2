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
            label='Akun Perkiraan',
            relation='accounting.chart_of_account',
            required=True,
            help_text='Akun default untuk metode pembayaran ini',
        ),
        'description': TextField(label='Deskripsi'),
        'is_active': BooleanField(label='Aktif', default=True),
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
                    'label': 'Umum',
                    'fields': ['name', 'code', 'account', 'is_active'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['description'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Metode Pembayaran'
        verbose_name_plural = 'Metode Pembayaran'

    def __str__(self):
        return self.name or ''
