from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, BooleanField, IntegerField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class DeliveryOrder(BaseModel):
    _model_name = 'sales.delivery_order'
    _display_name = 'reference'

    # ── State Machine (sama seperti Goods Receipt) ──
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
            help_text='Pilih format nomor dokumen pengiriman barang',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'sales_order': Many2OneField(
            label='SO',
            relation='sales.order',
            required=False,
        ),
        'quick_sales': Many2OneField(
            label='Quick Sales',
            relation='sales.quick_sales',
            required=False,
        ),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            required=True,
        ),
        'delivery_date': DateField(label='Tanggal Kirim'),
        'warehouse': CharField(label='Gudang'),
        'address': TextField(label='Alamat Pengiriman'),
        'notes': TextField(label='Catatan'),
        'delivery_lines': One2ManyField(
            label='Baris Pengiriman',
            relation='sales.delivery.order.line',
            inverse_field='delivery_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'sales_order', 'customer', 'delivery_date', 'warehouse', 'status'],
        'filters': ['status', 'delivery_date', 'warehouse'],
        'default_sort': ['-delivery_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'reference', 'sequence_id', 'sales_order', 'customer', 'delivery_date', 'warehouse'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['address', 'notes'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
                {
                    'label': 'Konfirmasi',
                    'icon': 'CheckOutlined',
                    'color': 'primary',
                    'action': 'confirm',
                    'states': ['draft'],
                },
                {
                    'label': 'Tandai Selesai',
                    'icon': 'CheckCircleOutlined',
                    'color': 'green',
                    'action': 'mark_done',
                    'states': ['waiting'],
                },
                {
                    'label': 'Batal',
                    'icon': 'StopOutlined',
                    'color': 'red',
                    'action': 'cancel',
                    'states': ['draft', 'waiting', 'done'],
                },
                {'label': 'Action', 'icon': 'MoreOutlined', 'color': 'primary'},
            ],
            'smart_buttons': [
                {'label': 'SO', 'model': 'sales.order', 'icon': 'FileTextOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Pengiriman',
                'relation': 'delivery_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Pengiriman Barang'
        verbose_name_plural = 'Pengiriman Barang'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='sales.delivery_order', active=True, is_deleted=False).first()
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
        """Print DO — tampilkan print preview di halaman yang sama."""
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/sales.delivery_order/{self.pk}/preview/',
            'pdf_url': f'/api/print/sales.delivery_order/{self.pk}/download/',
        }
