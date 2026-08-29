"""Stock Keluar (Transfer Stock) model."""
from core.fields import (
    CharField, TextField, DateField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class StockOut(BaseModel):
    _model_name = 'inventory.stock_out'
    _display_name = 'reference'

    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Dikonfirmasi', 'color': 'processing'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Dibatalkan', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'confirmed',
            'label': 'Konfirmasi',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Batal',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'source_warehouse': Many2OneField(
            label='Gudang Asal',
            relation='inventory.warehouse',
            required=True,
        ),
        'source_location': Many2OneField(
            label='Lokasi Asal',
            relation='inventory.warehouse_location',
            required=True,
            domain={'warehouse_id': 'source_warehouse'},
        ),
        'destination_warehouse': Many2OneField(
            label='Gudang Tujuan',
            relation='inventory.warehouse',
            required=True,
        ),
        'destination_location': Many2OneField(
            label='Lokasi Tujuan',
            relation='inventory.warehouse_location',
            required=True,
            domain={'warehouse_id': 'destination_warehouse'},
        ),
        'transfer_date': DateField(label='Tanggal Transfer'),
        'request_ref': Many2OneField(
            label='Nomor Transfer Request',
            relation='inventory.stock_request',
            required=False,
        ),
        'notes': TextField(label='Keterangan'),
        'out_lines': One2ManyField(
            label='Baris Transfer',
            relation='inventory.stock_out.line',
            inverse_field='out_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'source_warehouse', 'destination_warehouse', 'transfer_date', 'request_ref', 'status'],
        'filters': ['status', 'source_warehouse', 'destination_warehouse'],
        'default_sort': ['-transfer_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'reference', 'source_warehouse', 'source_location',
                               'destination_warehouse', 'destination_location', 'transfer_date', 'request_ref'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'actions': [
                {'label': 'Konfirmasi', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Batal', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'confirmed']},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Transfer',
                'relation': 'out_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Stock Keluar'
        verbose_name_plural = 'Stock Keluar'

    def __str__(self):
        return self.reference or f'SOUT#{self.pk}'

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f'Draft#{self.pk}'
            self.save(update_fields=['reference'])

    def _guard_confirm(self):
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('out_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Transfer sebelum konfirmasi.')
