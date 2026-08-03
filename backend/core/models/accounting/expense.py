from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class Expense(BaseModel):
    """Input Biaya — pencatatan biaya operasional dengan line per akun COA.

    State machine: draft → confirmed → posted.
    - Reference dibuat otomatis (Draft#id saat draft, nomor sequence saat confirm).
    - Account di line baru wajib saat POST (guard di transisi post).
    """

    _model_name = 'accounting.expense'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
        'posted': {'allow_edit': False, 'allow_delete': False, 'label': 'Posted', 'color': 'success'},
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
            'name': 'post',
            'from': ['confirmed'],
            'to': 'posted',
            'label': 'POST',
            'icon': 'CheckCircleOutlined',
            'guard': '_guard_post',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen input biaya',
        ),
        'reference': CharField(label='Reference', required=True, editable_statuses=[], placeholder='Automatic'),
        'date': DateField(label='Tanggal', required=True),
        'description': TextField(label='Keterangan'),
        'payment_method': Many2OneField(
            label='Payment Method',
            relation='accounting.payment_method',
            required=False,
        ),
        'project_line': Many2OneField(
            label='Milestone',
            relation='project.project_line',
            required=False,
            help_text='Milestone terkait (otomatis dari wizard Input Expenses)',
        ),
        'expense_lines': One2ManyField(
            label='Expense Lines',
            relation='accounting.expense_line',
            inverse_field='expense_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'date', 'payment_method', 'status'],
        'filters': ['status', 'date'],
        'default_sort': ['-date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'sequence_id', 'date', 'payment_method', 'description'],
                },
            ],
            'actions': [
                {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'POST', 'icon': 'CheckCircleOutlined', 'color': 'success', 'action': 'post', 'states': ['confirmed']},
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Expense Lines',
                'relation': 'expense_lines',
                'columns': ['description', 'amount', 'account'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Input Biaya'
        verbose_name_plural = 'Input Biaya'

    def __str__(self):
        return self.reference or f'#{self.pk}'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(
            model_ref='accounting.expense', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    # ── Guards ──

    def _guard_confirm(self):
        """Wajib pilih sequence + minimal 1 line sebelum confirm."""
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('expense_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Expense Line sebelum confirm.')

    def _guard_post(self):
        """Saat POST: semua expense line WAJIB punya account (COA)."""
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('expense_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                lines = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                )
                if lines.count() == 0:
                    raise ValueError('Minimal harus ada 1 Expense Line sebelum POST.')
                missing = lines.filter(account__isnull=True)
                if missing.exists():
                    raise ValueError('Semua Expense Line wajib memilih Account sebelum POST.')

    # ── Effects ──

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)
