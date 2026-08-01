from core.fields import (
    CharField, TextField, MonetaryField,
)
from core.model_meta import BaseModel


class Unit(BaseModel):
    """Daftar luaran (output) fisik maupun non-fisik yang dihasilkan dari proyek."""

    _model_name = 'project.unit'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Unit Produk',
            required=True,
            help_text='Misal: Kavling, Rumah Type A, Modul Sistem',
        ),
        'specifications': TextField(label='Spesifikasi'),
        'quality_standard': TextField(
            label='Standar Kualitas (Checkout List)',
            help_text='Checklist standar kualitas luaran',
        ),
        'base_price': MonetaryField(
            label='Harga Jual Dasar',
            currency='IDR',
        ),
    }

    _list_view = {
        'columns': ['name', 'specifications', 'quality_standard', 'base_price'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'base_price'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['specifications', 'quality_standard'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'

    def __str__(self):
        return self.name or ''
