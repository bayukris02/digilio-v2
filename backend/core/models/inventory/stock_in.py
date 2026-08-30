"""Terima Stock (Transfer Stock) model."""
from core.fields import (
    CharField, TextField, DateField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class StockIn(BaseModel):
    _model_name = 'inventory.stock_in'
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
        ),
        'source_location': Many2OneField(
            label='Lokasi Asal',
            relation='inventory.warehouse_location',
            domain={'warehouse_id': 'source_warehouse'},
        ),
        'destination_warehouse': Many2OneField(
            label='Gudang Tujuan',
            relation='inventory.warehouse',
        ),
        'destination_location': Many2OneField(
            label='Lokasi Tujuan',
            relation='inventory.warehouse_location',
            domain={'warehouse_id': 'destination_warehouse'},
        ),
        'transfer_date': DateField(label='Tanggal Transfer'),
        'transfer_out': Many2OneField(
            label='Transfer Keluar',
            relation='inventory.stock_out',
            required=False,
        ),
        'notes': TextField(label='Keterangan'),
        'in_lines': One2ManyField(
            label='Baris Transfer',
            relation='inventory.stock_in.line',
            inverse_field='in_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'source_warehouse', 'destination_warehouse', 'transfer_date', 'transfer_out', 'status'],
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
                               'destination_warehouse', 'destination_location', 'transfer_date', 'transfer_out'],
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
                'relation': 'in_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Terima Stock'
        verbose_name_plural = 'Terima Stock'

    def __str__(self):
        return self.reference or f'SIN#{self.pk}'

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f'Draft#{self.pk}'
            self.save(update_fields=['reference'])

    def _guard_confirm(self):
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        if self.transfer_out_id:
            from core.models.inventory.stock_out import StockOut
            out = StockOut.objects.get(pk=self.transfer_out_id)
            if out.status != 'confirmed':
                raise ValueError('Proses Stock Keluar (OUT) terlebih dahulu sebelum Terima Stock (IN).')
        if not self.destination_location_id:
            raise ValueError('Silakan pilih Lokasi Tujuan terlebih dahulu.')
        if (self.source_warehouse_id and self.source_location
                and self.source_location.warehouse_id_id != self.source_warehouse_id):
            raise ValueError('Lokasi Asal tidak sesuai dengan Gudang Asal yang dipilih.')
        if (self.destination_warehouse_id and self.destination_location
                and self.destination_location.warehouse_id_id != self.destination_warehouse_id):
            raise ValueError('Lokasi Tujuan tidak sesuai dengan Gudang Tujuan yang dipilih.')
        fd = self._field_descriptors.get('in_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Transfer sebelum konfirmasi.')

    def _effect_confirm(self):
        """Posting stok masuk (+qty) ke Lokasi Tujuan di stock ledger."""
        from core.stock_engine import StockEngine
        from core.models.inventory.stock_in_line import StockInLine
        lines = []
        for line in StockInLine.objects.filter(in_id=self.pk, is_deleted=False):
            if line.product_id and line.received_qty:
                lines.append({
                    'product_id': line.product_id,
                    'location_id': self.destination_location_id,
                    'quantity': float(line.received_qty),
                    'description': line.name,
                    'source_line_id': line.pk,
                })
        StockEngine.post(
            document={
                'model': 'inventory.stock_in',
                'id': self.pk,
                'reference': self.reference,
                'date': self.transfer_date,
            },
            lines=lines,
        )

    def _effect_cancel(self):
        """Batalkan dampak stok — soft-delete row ledger (history tetap di DB)."""
        from core.stock_engine import StockEngine
        StockEngine.delete(document={'model': 'inventory.stock_in', 'id': self.pk})
