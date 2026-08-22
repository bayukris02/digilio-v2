from core.fields import (
    CharField, DateField, PercentageField, Many2OneField,
)
from core.model_meta import BaseModel


class UnitDetailProgress(BaseModel):
    """Progress per unit detail (unit di dalam project)."""

    _model_name = 'project.unit_detail_progress'
    _display_name = 'name'

    _fields = {
        'unit_detail_id': Many2OneField(
            label='Unit Detail',
            relation='project.project_unit_detail',
            required=True,
        ),
        'name': CharField(
            label='Tahap',
            required=True,
            help_text='Misal: Termin 1, Termin 2, Finishing',
        ),
        'progress': PercentageField(
            label='Progress (%)',
        ),
        'date': DateField(
            label='Tanggal',
        ),
    }

    _list_view = {
        'columns': ['name', 'progress', 'date'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'progress', 'date'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Progress Unit'
        verbose_name_plural = 'Progress Unit'

    def __str__(self):
        return self.name or ''
