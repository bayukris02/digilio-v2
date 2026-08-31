"""Stock Adjustment (Stock Opname) model."""
from core.fields import (
    CharField, TextField, DateField, FloatField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class StockAdjustment(BaseModel):
    _model_name = 'inventory.stock_adjustment'
    _display_name = 'reference'

    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Selesai', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Dibatalkan', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'done',
            'label': 'Konfirmasi',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'done'],
            'to': 'cancelled',
            'label': 'Batal',
            'icon': 'StopOutlined',
            'effect': '_effect_cancel',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Tipe Dokumen',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen (ADJ, dll)',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'name': CharField(label='Nama Stock Count', required=True),
        'warehouse': Many2OneField(
            label='Gudang',
            relation='inventory.warehouse',
            required=True,
        ),
        'location': Many2OneField(
            label='Lokasi',
            relation='inventory.warehouse_location',
            domain={'warehouse_id': 'warehouse'},
            required=True,
        ),
        'adjustment_date': DateField(label='Tanggal', required=True),
        'notes': TextField(label='Catatan'),
        'total_selisih': FloatField(
            label='Total Selisih', default=0,
            compute='_compute_lines', depends=['adjustment_lines', 'location'],
        ),
        'adjustment_lines': One2ManyField(
            label='Baris Stock Opname',
            relation='inventory.stock_adjustment.line',
            inverse_field='adjustment_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'name', 'warehouse', 'location', 'adjustment_date', 'total_selisih', 'status'],
        'filters': ['status', 'warehouse'],
        'default_sort': ['-adjustment_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'sequence_id', 'reference', 'name', 'warehouse', 'location', 'adjustment_date'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'actions': [
                {'label': 'Konfirmasi', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Batal', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'done']},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Stock Opname',
                'relation': 'adjustment_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustment'

    def __str__(self):
        return self.reference or f'ADJ#{self.pk}'

    def save(self, *args, **kwargs):
        # Validasi gudang & lokasi saat simpan
        if (self.warehouse_id and self.location
                and self.location.warehouse_id_id != self.warehouse_id):
            raise ValueError('Lokasi tidak sesuai dengan Gudang yang dipilih.')
        super().save(*args, **kwargs)
        if not self.reference:
            self.reference = f'Draft#{self.pk}'
            self.save(update_fields=['reference'])

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='inventory.stock_adjustment', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    # ── Compute ──

    def _compute_lines(self):
        """Compute stock_sistem & stock_akhir per baris (real-time preview) + total selisih."""
        from core.stock_engine import StockEngine
        lines_data = getattr(self, '_tmp_one2many', {}).get('adjustment_lines', [])

        # Jika tidak ada data tmp, load dari DB
        if not lines_data and self.pk:
            fd = self._field_descriptors.get('adjustment_lines')
            if fd:
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    for line in child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    ):
                        lines_data.append({
                            '_key': f'k{line.pk}',
                            'product': line.product,
                            'selisih': float(getattr(line, 'selisih', 0) or 0),
                            'stock_sistem': float(getattr(line, 'stock_sistem', 0) or 0),
                        })

        location_id = getattr(self, 'location_id', None)
        computed = []
        total = 0.0
        for line in lines_data:
            prod = line.get('product')
            if isinstance(prod, dict):
                product_id = prod.get('id')
            elif hasattr(prod, 'pk'):
                product_id = prod.pk
            else:
                product_id = prod
            selisih = float(line.get('selisih', 0) or 0)
            sistem = 0.0
            if product_id and location_id:
                try:
                    sistem = float(StockEngine.on_hand(product_id, location_id) or 0)
                except Exception:
                    sistem = 0.0
            akhir = sistem + selisih
            total += selisih
            computed.append({
                '_key': line.get('_key'),
                'product': product_id,
                'stock_sistem': round(sistem, 3),
                'selisih': selisih,
                'stock_akhir': round(akhir, 3),
            })

        self.total_selisih = round(total, 3)
        # Per-line computed values untuk response API compute
        self._computed_o2m_lines = {
            'adjustment_lines': [c for c in computed if c.get('_key')],
        }

    # ── Guards ──

    def _guard_confirm(self):
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        if not self.sequence_id:
            raise ValueError('Silakan pilih Tipe Dokumen (Sequence) terlebih dahulu.')
        if not self.location_id:
            raise ValueError('Silakan pilih Lokasi terlebih dahulu.')
        if self.warehouse_id and self.location and self.location.warehouse_id_id != self.warehouse_id:
            raise ValueError('Lokasi tidak sesuai dengan Gudang yang dipilih.')
        fd = self._field_descriptors.get('adjustment_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Stock Opname sebelum konfirmasi.')

    # ── Effects ──

    def _effect_confirm(self):
        """Posting selisih opname (+/-) ke stock ledger Lokasi terpilih."""
        from core.sequence_engine import SequenceEngine
        from core.stock_engine import StockEngine
        from core.models.inventory.stock_adjustment_line import StockAdjustmentLine

        # Nomor dokumen dari sequence (bukan Draft#)
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

        if not self.location_id:
            raise ValueError('Silakan pilih Lokasi terlebih dahulu.')

        lines = []
        for line in StockAdjustmentLine.objects.filter(adjustment_id=self.pk, is_deleted=False):
            selisih = float(line.selisih or 0)
            if line.product_id and selisih != 0:
                lines.append({
                    'product_id': line.product_id,
                    'location_id': self.location_id,
                    'quantity': selisih,
                    'description': line.name or (str(line.product) if line.product_id else ''),
                    'source_line_id': line.pk,
                })
        if lines:
            StockEngine.post(
                document={
                    'model': 'inventory.stock_adjustment',
                    'id': self.pk,
                    'reference': self.reference,
                    'date': self.adjustment_date,
                },
                lines=lines,
            )

    def _effect_cancel(self):
        """Batalkan dampak stok — soft-delete row ledger (history tetap di DB)."""
        from core.stock_engine import StockEngine
        StockEngine.delete(document={'model': 'inventory.stock_adjustment', 'id': self.pk})
