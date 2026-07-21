"""
Sequence & SequenceDateRange for auto-numbering documents.

Mengadopsi konsep Odoo ir.sequence:
- Sequence: definisi prefix/suffix/padding/reset_period
- SequenceDateRange: counter per periode (yearly/monthly/no_reset)
- SequenceEngine: logic untuk generate nomor berikutnya
"""
from core.fields import (
    CharField, SelectionField, IntegerField, BooleanField,
    Many2OneField, DateField,
)
from core.model_meta import BaseModel


class Sequence(BaseModel):
    """Definisi sequence untuk auto-numbering dokumen."""

    _model_name = 'settings.sequence'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Name', required=True),
        'code': CharField(
            label='Code',
            required=True,
            help_text='Unique identifier, e.g. "purchase.order.local"',
        ),
        'prefix': CharField(
            label='Prefix',
            default='%(year)s/',
            help_text='Support formats: %(year)s, %(y)s, %(month)s, %(day)s',
        ),
        'suffix': CharField(label='Suffix', default=''),
        'padding': IntegerField(label='Padding', default=3),
        'reset_period': SelectionField(
            label='Reset Period',
            default='yearly',
            options=[
                ('yearly', 'Yearly'),
                ('monthly', 'Monthly'),
                ('no_reset', 'No Reset'),
            ],
            help_text='When to reset counter: yearly / monthly / never',
        ),
        'active': BooleanField(label='Active', default=True),
        'model_ref': CharField(
            label='Document Type',
            help_text='Model yg menggunakan sequence ini, e.g. "purchase.order"',
        ),
    }

    _list_view = {
        'columns': ['name', 'code', 'model_ref', 'prefix', 'reset_period', 'active'],
        'filters': ['model_ref', 'reset_period', 'active'],
    }

    _form_view = {
        'header': {
            'fields': [
                'name', 'code', 'model_ref', 'prefix', 'suffix',
                'padding', 'reset_period', 'active',
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Sequence'
        verbose_name_plural = 'Sequences'


class SequenceDateRange(BaseModel):
    """Counter per periode — auto-created oleh SequenceEngine."""

    _model_name = 'settings.sequence_date_range'

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            required=True,
        ),
        'date_from': DateField(label='Date From', required=True),
        'date_to': DateField(label='Date To'),
        'number_next': IntegerField(label='Next Number', default=1),
    }

    _list_view = {
        'columns': ['sequence_id', 'date_from', 'date_to', 'number_next'],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Sequence Date Range'
        verbose_name_plural = 'Sequence Date Ranges'
