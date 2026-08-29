"""Stock Ledger — row immutable pergerakan stok (ditulis oleh StockEngine)."""
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField, IntegerField,
    Many2OneField,
)
from core.model_meta import BaseModel


class StockLedger(BaseModel):
    """Ledger stok: setiap baris = 1 pergerakan (+masuk / -keluar) di 1 lokasi.

    Row hanya ditulis/di-soft-delete oleh core.stock_engine.StockEngine.
    On-hand stok = SUM(quantity) dari row aktif (is_deleted=False).
    """

    _model_name = 'inventory.stock_ledger'
    _display_name = 'source_reference'
    _allow_create = False  # data hanya dari StockEngine — create manual diblokir

    _fields = {
        'date': DateField(label='Tanggal'),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
        ),
        'location': Many2OneField(
            label='Lokasi',
            relation='inventory.warehouse_location',
            required=True,
        ),
        'quantity': FloatField(label='Qty (+/-)', default=0),
        'source_model': CharField(label='Model Sumber'),
        'source_reference': CharField(label='Referensi Sumber'),
        'source_id': IntegerField(label='ID Sumber'),
        'source_line_id': IntegerField(label='ID Baris Sumber', default=0),
        'unit_cost': MonetaryField(label='Harga Satuan', currency='IDR'),
        'description': TextField(label='Deskripsi'),
    }

    _list_view = {
        'columns': ['date', 'product', 'location', 'quantity', 'source_reference', 'source_model'],
        'filters': ['product', 'location', 'source_model'],
        'default_sort': ['-date'],
    }

    _form_view = {
        'header': {
            'fields': ['date', 'product', 'location', 'quantity',
                       'source_reference', 'source_model', 'source_id', 'source_line_id',
                       'unit_cost', 'description'],
            'actions': [],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Stock Ledger'
        verbose_name_plural = 'Stock Ledger'

    def __str__(self):
        return self.source_reference or f'Ledger#{self.pk}'
