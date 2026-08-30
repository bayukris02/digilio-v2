"""Stock Keluar (Transfer Stock) model."""
from core.fields import (
    CharField, TextField, DateField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class StockOut(BaseModel):
    _model_name = 'inventory.stock_out'
    _display_name = 'reference'

    # ── State Machine (sama seperti Delivery Order / Penerimaan Barang) ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'waiting': {'allow_edit': False, 'allow_delete': False, 'label': 'Menunggu', 'color': 'processing'},
        'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Selesai', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Dibatalkan', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'waiting',
            'label': 'Konfirmasi',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'mark_done',
            'from': ['waiting'],
            'to': 'done',
            'label': 'Tandai Selesai',
            'icon': 'CheckCircleOutlined',
            'guard': '_guard_mark_done',
            'effect': '_effect_mark_done',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'waiting', 'done'],
            'to': 'cancelled',
            'label': 'Batal',
            'icon': 'StopOutlined',
            'effect': '_effect_cancel',
        },
    ]

    # ── Document Flow (smart button: buka Terima Stock yang terkait) ──
    _document_flow = {
        'children': [
            {
                'model': 'inventory.stock_in',
                'label': 'Terima Stock',
                'icon': 'DownloadOutlined',
                'source_field_in_child': 'transfer_out',
                'constraints': {'max_per_parent': 1, 'unique_per_parent': True},
            },
        ],
    }

    _fields = {
        'sequence_id': Many2OneField(
            label='Tipe Dokumen',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen (SOUT, dll)',
        ),
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
        'columns': ['reference', 'sequence_id', 'source_warehouse', 'destination_warehouse', 'transfer_date', 'request_ref', 'status'],
        'filters': ['status', 'source_warehouse', 'destination_warehouse'],
        'default_sort': ['-transfer_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'sequence_id', 'reference', 'source_warehouse', 'source_location',
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
                {'label': 'Tandai Selesai', 'color': 'green', 'action': 'mark_done', 'states': ['waiting']},
                {'label': 'Batal', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'waiting', 'done']},
            ],
            'smart_buttons': [
                {'label': 'Nomor Request', 'model': 'inventory.stock_request', 'icon': 'FileTextOutlined'},
                {'label': 'Terima Stock', 'model': 'inventory.stock_in', 'icon': 'DownloadOutlined'},
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

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='inventory.stock_out', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    def _guard_confirm(self):
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        if not self.sequence_id:
            raise ValueError('Silakan pilih Tipe Dokumen (Sequence) terlebih dahulu.')
        if not self.source_location_id:
            raise ValueError('Silakan pilih Lokasi Asal terlebih dahulu.')
        if not self.destination_location_id:
            raise ValueError('Silakan pilih Lokasi Tujuan terlebih dahulu.')
        if (self.source_warehouse_id and self.source_location
                and self.source_location.warehouse_id_id != self.source_warehouse_id):
            raise ValueError('Lokasi Asal tidak sesuai dengan Gudang Asal yang dipilih.')
        if (self.destination_warehouse_id and self.destination_location
                and self.destination_location.warehouse_id_id != self.destination_warehouse_id):
            raise ValueError('Lokasi Tujuan tidak sesuai dengan Gudang Tujuan yang dipilih.')
        fd = self._field_descriptors.get('out_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Transfer sebelum konfirmasi.')

    def _guard_mark_done(self):
        """Cek stok sebelum Tandai Selesai: minus butuh konfirmasi user."""
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        if (self.source_warehouse_id and self.source_location
                and self.source_location.warehouse_id_id != self.source_warehouse_id):
            raise ValueError('Lokasi Asal tidak sesuai dengan Gudang Asal yang dipilih.')
        if (self.destination_warehouse_id and self.destination_location
                and self.destination_location.warehouse_id_id != self.destination_warehouse_id):
            raise ValueError('Lokasi Tujuan tidak sesuai dengan Gudang Tujuan yang dipilih.')
        # Cek stok minus di Lokasi Asal sebelum transfer keluar
        from core.models.inventory.stock_out_line import StockOutLine
        lines = []
        for line in StockOutLine.objects.filter(out_id=self.pk, is_deleted=False):
            if line.product_id and line.transfer_qty:
                lines.append({
                    'product_id': line.product_id,
                    'location_id': self.source_location_id,
                    'quantity': -float(line.transfer_qty),
                })
        from core.stock_engine import StockEngine
        warnings = StockEngine.check_negative(lines)
        confirmed = (getattr(self, '_action_request_data', {}) or {}).get('confirmed')
        if warnings and not confirmed:
            detail = '\n'.join(
                f"• {w['product_name']} @ {w['location_name']}: tersedia {w['available']:g}, "
                f"dibutuhkan {w['required']:g} (minus {w['deficit']:g})"
                for w in warnings
            )
            return {
                '_action_type': 'confirm',
                'confirm_message': f'Stok tidak mencukupi untuk transfer keluar ini:\n{detail}\n\n'
                                   f'Lanjutkan? Stok akan menjadi minus.',
            }

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm (draft → menunggu)."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    def _effect_mark_done(self):
        """Posting stok keluar (−qty) dari Lokasi Asal ke stock ledger."""
        from core.sequence_engine import SequenceEngine
        from core.stock_engine import StockEngine
        from core.models.inventory.stock_out_line import StockOutLine

        # Nomor dokumen dari sequence (bukan Draft#) — untuk dokumen yg lahir dari request
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

        lines = []
        for line in StockOutLine.objects.filter(out_id=self.pk, is_deleted=False):
            if line.product_id and line.transfer_qty:
                lines.append({
                    'product_id': line.product_id,
                    'location_id': self.source_location_id,
                    'quantity': -float(line.transfer_qty),
                    'description': line.name,
                    'source_line_id': line.pk,
                })
        StockEngine.post(
            document={
                'model': 'inventory.stock_out',
                'id': self.pk,
                'reference': self.reference,
                'date': self.transfer_date,
            },
            lines=lines,
        )

    def _effect_cancel(self):
        """Batalkan dampak stok — soft-delete row ledger (history tetap di DB)."""
        from core.stock_engine import StockEngine
        StockEngine.delete(document={'model': 'inventory.stock_out', 'id': self.pk})
