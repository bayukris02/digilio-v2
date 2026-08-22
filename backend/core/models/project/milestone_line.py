from core.fields import (
    CharField, PercentageField, Many2OneField,
)
from core.model_meta import BaseModel


class MilestoneLine(BaseModel):
    """Aktivitas detail di dalam sebuah milestone (type, aktivitas, bobot)."""

    _model_name = 'project.milestone_line'
    _display_name = 'name'

    _fields = {
        'milestone_id': Many2OneField(
            label='Milestone',
            relation='project.milestone',
            required=True,
        ),
        'type': CharField(
            label='Tipe',
            help_text='Tipe aktivitas (bebas), misal: Persiapan, Struktur, Dokumen',
        ),
        'name': CharField(
            label='Aktivitas',
            required=True,
            help_text='Nama aktivitas yang harus diselesaikan',
        ),
        'weight': PercentageField(
            label='Bobot (%)',
            help_text='Bobot aktivitas terhadap milestone',
        ),
    }

    _list_view = {
        'columns': ['type', 'name', 'weight'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['type', 'name', 'weight'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Milestone'
        verbose_name_plural = 'Baris Milestone'

    def __str__(self):
        return self.name or ''
