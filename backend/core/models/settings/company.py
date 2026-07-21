"""
Company model for multi-company support.
Setiap Company adalah entitas legal terpisah.
"""
from core.fields import (
    CharField, TextField, BooleanField,
)
from core.model_meta import BaseModel


class Company(BaseModel):
    """Legal entity / perusahaan."""

    _model_name = 'settings.company'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Company Name',
            required=True,
        ),
        'code': CharField(
            label='Code',
            required=True,
            help_text='Unique short code, e.g. PTABC',
        ),
        'address': TextField(label='Address'),
        'phone': CharField(label='Phone', max_length=50),
        'email': CharField(label='Email', max_length=255),
        'active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'phone', 'email', 'active'],
        'filters': ['active'],
    }

    _form_view = {
        'header': {
            'fields': ['code', 'name', 'address', 'phone', 'email', 'active'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return f'[{self.code}] {self.name}'
