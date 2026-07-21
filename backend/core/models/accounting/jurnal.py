"""
Jurnal — transaksi jurnal akuntansi (general journal entry).
Header + Lines: satu jurnal punya banyak baris debit/credit.
"""
from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class Jurnal(BaseModel):
    """Header jurnal akuntansi."""

    _model_name = 'accounting.jurnal'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'posted': {'allow_edit': False, 'allow_delete': False, 'label': 'Posted', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'post',
            'from': ['draft'],
            'to': 'posted',
            'label': 'Post',
            'icon': 'CheckCircleOutlined',
        },
        {
            'name': 'cancel',
            'from': ['draft'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'reference': CharField(
            label='Reference',
            required=True,
            help_text='Nomor referensi jurnal',
        ),
        'date': DateField(
            label='Tanggal Jurnal',
            required=True,
        ),
        'description': TextField(
            label='Deskripsi',
            help_text='Keterangan transaksi jurnal',
        ),
        'journal_type': SelectionField(
            label='Tipe Jurnal',
            required=True,
            options=[
                ('general', 'General Journal'),
                ('sales', 'Sales Journal'),
                ('purchase', 'Purchase Journal'),
                ('cash', 'Cash Journal'),
            ],
            colors={
                'general': 'blue',
                'sales': 'green',
                'purchase': 'orange',
                'cash': 'purple',
            },
        ),
        'total_debit': MonetaryField(
            label='Total Debit',
            currency='IDR',
            compute='_compute_totals',
            depends=['jurnal_lines'],
        ),
        'total_credit': MonetaryField(
            label='Total Credit',
            currency='IDR',
            compute='_compute_totals',
            depends=['jurnal_lines'],
        ),
        'jurnal_lines': One2ManyField(
            label='Jurnal Lines',
            relation='accounting.jurnal_line',
            inverse_field='jurnal_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'date', 'journal_type', 'total_debit', 'total_credit', 'status'],
        'filters': ['status', 'journal_type', 'date'],
        'group_by': ['status', 'journal_type'],
        'default_sort': ['-date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'date', 'journal_type', 'description'],
                },
            ],
            'actions': [
                {'label': 'Post', 'icon': 'CheckCircleOutlined', 'color': 'primary', 'action': 'post', 'states': ['draft']},
                {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'red', 'action': 'cancel', 'states': ['draft']},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Jurnal Lines',
                'relation': 'jurnal_lines',
                'summary': {
                    'columns': {'debit': 'sum', 'credit': 'sum'},
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Jurnal'
        verbose_name_plural = 'Jurnal'

    # ── Computed Fields ──

    def _compute_totals(self):
        """Hitung total debit dan credit dari jurnal lines."""
        lines_data = getattr(self, '_tmp_one2many', {}).get('jurnal_lines', [])
        if lines_data:
            total_debit = sum(float(line.get('debit', 0) or 0) for line in lines_data)
            total_credit = sum(float(line.get('credit', 0) or 0) for line in lines_data)
        elif self.pk:
            total_debit = 0
            total_credit = 0
            from core.model_meta import ErpModelBase
            fd = self._field_descriptors.get('jurnal_lines')
            if fd:
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    for line in child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    ):
                        total_debit += float(line.debit or 0)
                        total_credit += float(line.credit or 0)
        else:
            total_debit = 0
            total_credit = 0

        self.total_debit = total_debit
        self.total_credit = total_credit

    def __str__(self):
        return self.reference or ''
