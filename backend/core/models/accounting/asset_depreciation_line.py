from core.fields import DateField, Many2OneField, MonetaryField
from core.model_meta import BaseModel


class AssetDepreciationLine(BaseModel):
    """Baris jadwal depresiasi linear bulanan — dihasilkan oleh aksi Hitung Depresiasi (read-only)."""

    _model_name = 'accounting.asset_depreciation_line'
    _display_name = 'date'

    _fields = {
        'asset_id': Many2OneField(
            label='Aset',
            relation='accounting.asset',
            required=True,
        ),
        'date': DateField(
            label='Tanggal',
        ),
        'asset_value': MonetaryField(
            label='Nilai Aset',
            currency='IDR',
        ),
        'depreciation': MonetaryField(
            label='Depresiasi',
            currency='IDR',
        ),
        'residual_value': MonetaryField(
            label='Sisa Nilai',
            currency='IDR',
        ),
    }

    _list_view = {
        'columns': ['asset_id', 'date', 'asset_value', 'depreciation', 'residual_value'],
        'default_sort': ['date'],
    }

    _form_view = {
        'header': {
            'fields': ['asset_id', 'date', 'asset_value', 'depreciation', 'residual_value'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Depresiasi'
        verbose_name_plural = 'Baris Depresiasi'

    def __str__(self):
        return str(self.date) if self.date else ''
