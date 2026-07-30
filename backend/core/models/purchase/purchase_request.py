from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class PurchaseRequest(BaseModel):
    _model_name = 'purchase.request'
    _display_name = 'reference'

    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'confirmed',
            'label': 'Confirm',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Document Type',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen (PR, dll)',
        ),
        'reference': CharField(
            label='Reference', required=True, editable_statuses=[],
            placeholder='Automatic',
        ),
        'requested_by': Many2OneField(
            label='Requested By',
            relation='settings.user',
            required=False,
        ),
        'request_date': DateField(label='Request Date', required=True),
        'estimated_receipt_date': DateField(label='Estimated Receipt Date'),
        'notes': TextField(label='Notes'),
        'request_lines': One2ManyField(
            label='Request Lines',
            relation='purchase.request.line',
            inverse_field='request_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'requested_by', 'request_date', 'estimated_receipt_date', 'status'],
        'filters': ['status', 'request_date'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'sequence_id', 'requested_by', 'request_date',
                               'estimated_receipt_date', 'notes'],
                },
            ],
            'actions': [
                {
                    'label': 'Confirm',
                    'icon': 'CheckOutlined',
                    'color': 'primary',
                    'action': 'confirm',
                    'states': ['draft'],
                },
                {
                    'label': 'Cancel',
                    'icon': 'StopOutlined',
                    'color': 'red',
                    'action': 'cancel',
                    'states': ['draft', 'confirmed'],
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Request Lines',
                'relation': 'request_lines',
                'columns': ['product', 'description', 'qty', 'estimated_cost', 'total', 'vendor'],
                'summary': {
                    'columns': {'qty': 'sum', 'estimated_cost': 'sum', 'total': 'sum'},
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Request'
        verbose_name_plural = 'Purchase Requests'

    def __str__(self):
        return self.reference or f'PR#{self.pk}'

    def save(self, *args, **kwargs):
        """Auto-fill requested_by (dari user yg buat) & request_date (hari ini)."""
        is_new = not self.pk
        if is_new:
            if not self.requested_by_id and hasattr(self, 'created_by_id') and self.created_by_id:
                self.requested_by_id = self.created_by_id
            if not self.request_date:
                from datetime import date
                self.request_date = date.today()
        super().save(*args, **kwargs)

    # ── Guards ──

    def _guard_confirm(self):
        """Wajib pilih sequence & minimal 1 line sebelum konfirmasi."""
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence (Document Type) terlebih dahulu.')

        # Validasi minimal 1 request line
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        from core.model_meta import ErpModelBase
        fd = self._field_descriptors.get('request_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Request Line sebelum konfirmasi.')

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence, request_date (hari ini), & requested_by (user login)."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(
            model_ref='purchase.request', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk

        # Default request_date = hari ini
        from datetime import date
        config['fields']['request_date']['default'] = date.today().isoformat()

        return config
