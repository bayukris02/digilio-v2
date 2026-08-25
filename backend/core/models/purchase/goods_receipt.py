from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, BooleanField, IntegerField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class GoodsReceipt(BaseModel):
    _model_name = 'purchase.goods_receipt'
    _display_name = 'reference'

    # ── State Machine ──
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
        },
        {
            'name': 'cancel',
            'from': ['draft', 'waiting', 'done'],
            'to': 'cancelled',
            'label': 'Batal',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Tipe Dokumen',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen penerimaan barang',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'purchase_order': Many2OneField(
            label='PO',
            relation='purchase.order',
            required=False,
        ),
        'quick_purchase': Many2OneField(
            label='Quick Purchase',
            relation='purchase.quick_purchase',
            required=False,
        ),
        'receipt_date': DateField(label='Tanggal Terima', editable_statuses=['draft', 'waiting']),
        'warehouse': CharField(label='Gudang'),
        'notes': TextField(label='Catatan'),
        'receipt_lines': One2ManyField(
            label='Baris Penerimaan',
            relation='purchase.goods_receipt.line',
            inverse_field='receipt_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'purchase_order', 'receipt_date', 'status', 'warehouse'],
        'filters': ['status', 'receipt_date', 'warehouse'],
        'default_sort': ['-receipt_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'reference', 'sequence_id', 'purchase_order', 'receipt_date', 'warehouse'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'color': 'green', 'action': 'print'},
                {'label': 'Proses Penerimaan', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Konfirmasi', 'color': 'primary', 'action': 'mark_done', 'states': ['waiting']},
                {'label': 'Batal', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'waiting', 'done']},
            ],
            'smart_buttons': [
                {'label': 'PO', 'model': 'purchase.order', 'icon': 'FileTextOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Penerimaan',
                'relation': 'receipt_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Penerimaan Barang'
        verbose_name_plural = 'Penerimaan Barang'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='purchase.goods_receipt', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    # ── Guards ──

    def _guard_confirm(self):
        if not self.sequence_id:
            raise ValueError('Silakan pilih Tipe Dokumen (Sequence) terlebih dahulu.')

    # ── Effects ──

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    def _action_print(self, *args, **kwargs):
        """Print GR — tampilkan print preview di halaman yang sama."""
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/purchase.goods_receipt/{self.pk}/preview/',
            'pdf_url': f'/api/print/purchase.goods_receipt/{self.pk}/download/',
        }
