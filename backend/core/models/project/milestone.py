from core.fields import (
    CharField, TextField, One2ManyField,
)
from core.model_meta import BaseModel


class Milestone(BaseModel):
    """Pangkalan data acuan/master titik pencapaian (milestone) standar beserta bobot acuan dan syarat pembayarannya."""

    _model_name = 'project.milestone'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Milestone',
            required=True,
            help_text='Misal: DP / Tanda Jadi, Pondasi, Struktur & Atap, Finishing, Retensi',
        ),
        'claim_requirements': TextField(
            label='Syarat Klaim / Kelengkapan Dokumen',
            help_text='Syarat kelengkapan dokumen atau syarat klaim pembayaran milestone',
        ),
        'lines': One2ManyField(
            label='Milestone Lines',
            relation='project.milestone_line',
            inverse_field='milestone_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'claim_requirements'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'claim_requirements'],
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Milestone Lines',
                'relation': 'lines',
                'columns': ['type', 'name', 'weight'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'

    def __str__(self):
        return self.name or ''
