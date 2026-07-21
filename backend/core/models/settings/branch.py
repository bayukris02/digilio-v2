"""
Branch model for multi-branch support.
Setiap Branch adalah cabang fisik dalam satu Company.
"""
from core.fields import (
    CharField, TextField, BooleanField, Many2OneField,
)
from core.model_meta import BaseModel


class Branch(BaseModel):
    """Cabang dari suatu Company."""

    _model_name = 'settings.branch'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Branch Name',
            required=True,
        ),
        'code': CharField(
            label='Code',
            required=True,
            help_text='Short identifier, e.g. HQ, GDG1',
        ),
        'company_id': Many2OneField(
            label='Company',
            relation='settings.company',
            required=True,
        ),
        'address': TextField(label='Address'),
        'phone': CharField(label='Phone', max_length=50),
        'active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'company_id', 'phone', 'active'],
        'filters': ['company_id', 'active'],
    }

    _form_view = {
        'header': {
            'fields': ['code', 'name', 'company_id', 'address', 'phone', 'active'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'

    def __str__(self):
        return f'[{self.code}] {self.name}'
