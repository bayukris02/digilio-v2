from core.fields import (
    CharField, TextField, IntegerField, PercentageField, SelectionField,
)
from core.model_meta import BaseModel


class Dokumen(BaseModel):
    """Standarisasi jenis risiko, perizinan, dan kewajiban pajak/legalitas."""

    _model_name = 'project.dokumen'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Dokumen',
            required=True,
            help_text='Misal: PBG, Pemecahan Sertifikat, SHM, PPH Final 4%',
        ),
        'doc_type': SelectionField(
            label='Jenis Dokumen',
            options=[
                ('risk', 'Kategori Risiko'),
                ('license', 'Perizinan'),
                ('tax', 'Perpajakan'),
            ],
            default='license',
            colors={
                'risk': 'orange',
                'license': 'blue',
                'tax': 'purple',
            },
        ),
        'reference': CharField(
            label='Dasar Hukum / Referensi',
            help_text='Misal: PP 16/2021, UU 28/2009',
        ),
        'rate': PercentageField(
            label='Tarif (%)',
            help_text='Tarif persen untuk aturan perpajakan (PPH, BPHTB, Pajak Konstruksi)',
        ),
        'validity_days': IntegerField(
            label='Masa Berlaku (hari)',
            help_text='Masa berlaku dokumen perizinan',
        ),
        'description': TextField(
            label='Keterangan',
            help_text='Standar kualitas, kewajiban, atau catatan legalitas',
        ),
    }

    _list_view = {
        'columns': ['name', 'doc_type', 'reference', 'rate', 'validity_days'],
        'filters': ['doc_type'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'doc_type', 'reference'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['rate', 'validity_days', 'description'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Dokumen'
        verbose_name_plural = 'Dokumen'

    def __str__(self):
        return self.name or ''
