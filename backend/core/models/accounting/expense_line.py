from django.db import models
from core.fields import (
    CharField, TextField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class ExpenseLine(BaseModel):
    """Line biaya — deskripsi, nominal, akun COA."""

    _model_name = 'accounting.expense_line'

    _fields = {
        'expense_id': Many2OneField(
            label='Input Biaya',
            relation='accounting.expense',
            required=True,
        ),
        'description': TextField(label='Deskripsi'),
        'amount': MonetaryField(label='Nominal', currency='IDR', required=True),
        'account': Many2OneField(
            label='Akun',
            relation='accounting.chart_of_account',
            required=False,
            help_text='Wajib diisi saat POST',
        ),
    }

    _list_view = {
        'columns': ['description', 'amount', 'account'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['description', 'amount', 'account'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Biaya'
        verbose_name_plural = 'Baris Biaya'

    def __str__(self):
        return self.description or f'#{self.pk}'
