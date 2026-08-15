"""Satuan (Unit of Measure) model."""
from core.fields import CharField, BooleanField
from core.model_meta import BaseModel


class Uom(BaseModel):
    """Satuan / unit of measure untuk barang (pcs, box, kg, dll)."""

    _model_name = 'inventory.uom'
    _display_name = 'name'

    _fields = {
        'code': CharField(label='Kode', required=True, help_text='Singkatan, misal: pcs, box, kg'),
        'name': CharField(label='Nama Satuan', required=True, help_text='Misal: Pieces, Box, Kilogram'),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'is_active'],
        'filters': ['is_active'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['code', 'name', 'is_active'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Satuan'
        verbose_name_plural = 'Satuan'

    def __str__(self):
        return f'[{self.code}] {self.name}' if self.code else (self.name or '')
