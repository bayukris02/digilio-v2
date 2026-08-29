"""
Chart of Account — master data akun akuntansi.
Struktur hierarkis: parent-child untuk akun header/sub-akun.
"""
from django.db import models
from core.fields import (
    CharField, TextField, BooleanField, SelectionField, Many2OneField,
)
from core.model_meta import BaseModel


class ChartOfAccount(BaseModel):
    """Akun akuntansi — Chart of Account."""

    _model_name = 'accounting.chart_of_account'
    _display_name = None  # fallback __str__ → '[kode] nama' (konsisten dgn kolom list & dropdown m2o)

    _fields = {
        'code': CharField(
            label='Kode Akun',
            required=True,
            help_text='Format: 1-1000, 1-2000, dst.',
        ),
        'name': CharField(
            label='Nama Akun',
            required=True,
        ),
        'type': SelectionField(
            label='Tipe Akun',
            required=True,
            options=[
                ('asset', 'Asset'),
                ('liability', 'Liability'),
                ('equity', 'Equity'),
                ('revenue', 'Revenue'),
                ('expense', 'Expense'),
            ],
            colors={
                'asset': 'blue',
                'liability': 'orange',
                'equity': 'purple',
                'revenue': 'green',
                'expense': 'red',
            },
        ),
        'parent': Many2OneField(
            label='Parent Akun',
            relation='accounting.chart_of_account',
            help_text='Akun induk untuk struktur hierarki',
        ),
        'description': TextField(label='Deskripsi'),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'type', 'parent', 'is_active'],
        'filters': ['type', 'is_active'],
        'group_by': ['type'],
        'default_sort': ['code'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['code', 'name', 'type', 'parent', 'is_active'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['description'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Chart of Account'
        verbose_name_plural = 'Chart of Accounts'

    def __str__(self):
        return f'[{self.code}] {self.name}'
