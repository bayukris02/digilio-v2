"""
JurnalLine — baris detail jurnal akuntansi.
Setiap line memiliki akun (COA), nilai debit/credit, dan deskripsi.
"""
from django.db import models
from core.fields import (
    CharField, TextField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class JurnalLine(BaseModel):
    """Baris detail jurnal — debit/credit per akun."""

    _model_name = 'accounting.jurnal_line'
    _display_name = 'name'

    _fields = {
        'jurnal_id': Many2OneField(
            label='Jurnal',
            relation='accounting.jurnal',
            required=True,
        ),
        'account': Many2OneField(
            label='Akun',
            relation='accounting.chart_of_account',
            required=True,
            help_text='Akun debit/credit',
        ),
        'debit': MonetaryField(
            label='Debit',
            currency='IDR',
            default=0,
        ),
        'credit': MonetaryField(
            label='Credit',
            currency='IDR',
            default=0,
        ),
        'description': CharField(
            label='Deskripsi',
            help_text='Keterangan baris jurnal',
        ),
    }

    _list_view = {
        'columns': ['account', 'debit', 'credit', 'description'],
    }

    _form_view = {
        'header': {
            'fields': ['account', 'debit', 'credit', 'description'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Jurnal Line'
        verbose_name_plural = 'Jurnal Lines'

    def __str__(self):
        return f'{self.account} - D:{self.debit} C:{self.credit}'
