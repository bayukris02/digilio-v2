"""Warehouse / Gudang model."""
from core.fields import CharField, TextField, BooleanField, Many2OneField
from core.model_meta import BaseModel


class Warehouse(BaseModel):
    """Warehouse / gudang penyimpanan barang."""

    _model_name = 'inventory.warehouse'
    _display_name = 'name'

    _fields = {
        'code': CharField(label='Kode Gudang', required=True),
        'name': CharField(label='Nama Gudang', required=True),
        'address': TextField(label='Alamat'),
        'phone': CharField(label='Telepon', max_length=50),
        'company_id': Many2OneField(
            label='Company',
            relation='settings.company',
        ),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'company_id', 'is_active'],
        'filters': ['company_id', 'is_active'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['code', 'name', 'company_id', 'address', 'phone', 'is_active'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'

    def __str__(self):
        return f'[{self.code}] {self.name}' if self.code else (self.name or '')
