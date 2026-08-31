"""Baris Stock Adjustment (Stock Opname) model."""
from core.fields import (
    CharField, TextField, FloatField,
    Many2OneField,
)
from core.model_meta import BaseModel


class StockAdjustmentLine(BaseModel):
    _model_name = 'inventory.stock_adjustment.line'

    _fields = {
        'adjustment_id': Many2OneField(
            label='Stock Adjustment',
            relation='inventory.stock_adjustment',
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name'},
        ),
        'name': TextField(label='Deskripsi'),
        'uom': CharField(label='UOM'),
        'stock_sistem': FloatField(
            label='Stock Sistem', default=0,
            compute='_compute_stock', editable_statuses=[],
        ),
        'selisih': FloatField(
            label='Selisih', default=0,
            help_text='Selisih fisik vs sistem (boleh minus)',
        ),
        'stock_akhir': FloatField(
            label='Stock Akhir', default=0,
            compute='_compute_stock', editable_statuses=[],
        ),
    }

    _list_view = {
        'columns': ['product', 'name', 'uom', 'stock_sistem', 'selisih', 'stock_akhir'],
        'default_sort': ['id'],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Stock Adjustment'
        verbose_name_plural = 'Baris Stock Adjustment'

    def _compute_stock(self):
        """stock_sistem = on-hand di lokasi header; stock_akhir = sistem + selisih."""
        from core.stock_engine import StockEngine
        location_id = None
        adj = getattr(self, 'adjustment_id', None)
        if adj is not None and not isinstance(adj, int):
            location_id = getattr(adj, 'location_id', None)
        sistem = 0.0
        if self.product_id and location_id:
            try:
                sistem = float(StockEngine.on_hand(self.product_id, location_id) or 0)
            except Exception:
                sistem = 0.0
        self.stock_sistem = sistem
        self.stock_akhir = round(sistem + float(self.selisih or 0), 3)
