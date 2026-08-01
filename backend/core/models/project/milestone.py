from core.fields import (
    CharField, TextField, PercentageField,
)
from core.model_meta import BaseModel


class Milestone(BaseModel):
    """Pangkalan data acuan/master titik pencapaian (milestone) standar beserta bobot acuan dan syarat pembayarannya."""

    _model_name = 'project.milestone'
    _display_name = 'name'

    _fields = {
        'code': CharField(
            label='Kode Milestone',
            required=True,
            help_text='Kode standar, misal: MS-01, MS-02',
        ),
        'name': CharField(
            label='Nama Milestone',
            required=True,
            help_text='Misal: DP / Tanda Jadi, Pondasi, Struktur & Atap, Finishing, Retensi',
        ),
        'weight': PercentageField(
            label='Bobot (%)',
            help_text='Estimasi bobot persentase milestone (misal: Pondasi 25%, Struktur & Atap 30%)',
        ),
        'claim_requirements': TextField(
            label='Syarat Klaim / Kelengkapan Dokumen',
            help_text='Syarat kelengkapan dokumen atau syarat klaim pembayaran milestone',
        ),
    }

    _list_view = {
        'columns': ['code', 'name', 'weight', 'claim_requirements'],
        'default_sort': ['code'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['code', 'name', 'weight'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['claim_requirements'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'

    def __str__(self):
        return f'{self.code or ""} - {self.name or ""}'.strip(' -')
