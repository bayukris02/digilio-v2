"""Lokasi Gudang model — subsection/detail dari Warehouse."""
from core.fields import CharField, Many2OneField
from core.model_meta import BaseModel


class WarehouseLocation(BaseModel):
    """Lokasi di dalam gudang (misal: Lantai 1, Lantai 2, Toko)."""

    _model_name = 'inventory.warehouse_location'
    _display_name = 'name'

    _fields = {
        'warehouse_id': Many2OneField(
            label='Gudang',
            relation='inventory.warehouse',
            required=True,
        ),
        'name': CharField(label='Nama Lokasi', required=True),
    }

    _list_view = {
        'columns': ['warehouse_id', 'name'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'fields': ['warehouse_id', 'name'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Lokasi Gudang'
        verbose_name_plural = 'Lokasi Gudang'

    def __str__(self):
        return self.name or f'Lokasi #{self.pk}'
