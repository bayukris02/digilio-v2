"""Request Transfer (Transfer Stock) model."""
from core.fields import (
    CharField, TextField, DateField, FloatField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class StockRequest(BaseModel):
    _model_name = 'inventory.stock_request'
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
            domain={'warehouse': 'source_warehouse'},
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
            domain={'warehouse': 'destination_warehouse'},
        ),
        'deadline': DateField(label='Deadline Request'),
        'notes': TextField(label='Keterangan'),
        'requested_by': Many2OneField(
            label='User Request',
            relation='settings.user',
            required=False,
        ),
        'request_lines': One2ManyField(
            label='Baris Transfer',
            relation='inventory.stock_request.line',
            inverse_field='request_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'source_warehouse', 'destination_warehouse', 'deadline', 'status', 'requested_by'],
        'filters': ['status', 'source_warehouse', 'destination_warehouse'],
        'default_sort': ['-deadline'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['status', 'reference', 'source_warehouse', 'source_location',
                               'destination_warehouse', 'destination_location', 'deadline', 'requested_by'],
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
                'relation': 'request_lines',
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Request Transfer'
        verbose_name_plural = 'Request Transfer'

    def __str__(self):
        return self.reference or f'SR#{self.pk}'

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new:
            if not self.requested_by_id and hasattr(self, 'created_by_id') and self.created_by_id:
                self.requested_by_id = self.created_by_id
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f'Draft#{self.pk}'
            self.save(update_fields=['reference'])

    def _guard_confirm(self):
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('request_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Transfer sebelum konfirmasi.')
