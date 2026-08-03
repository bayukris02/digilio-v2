from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class Expense(BaseModel):
    """Input Biaya — pencatatan biaya operasional dengan line per akun COA."""

    _model_name = 'accounting.expense'
    _display_name = 'description'

    _fields = {
        'date': DateField(label='Tanggal', required=True),
        'description': TextField(label='Keterangan'),
        'expense_lines': One2ManyField(
            label='Expense Lines',
            relation='accounting.expense_line',
            inverse_field='expense_id',
        ),
    }

    _list_view = {
        'columns': ['date', 'description'],
        'filters': ['date'],
        'default_sort': ['-date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['date', 'description'],
                },
            ],
            'actions': [],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Expense Lines',
                'relation': 'expense_lines',
                'columns': ['description', 'amount', 'account'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Input Biaya'
        verbose_name_plural = 'Input Biaya'

    def __str__(self):
        return f'{self.date} - {self.description or ""}' if self.date else (self.description or f'#{self.pk}')
