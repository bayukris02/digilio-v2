from core.fields import CharField, Many2OneField
from core.model_meta import BaseModel


class UnitProgress(BaseModel):
    """Tahapan (master) per Tipe Unit — dipakai sebagai template baris Progress/Budget Detail Unit."""

    _model_name = 'project.unit_progress'
    _display_name = 'name'

    _fields = {
        'unit_id': Many2OneField(
            label='Unit',
            relation='project.unit',
            required=True,
        ),
        'name': CharField(
            label='Tahapan',
            required=True,
            help_text='Misal: Pondasi, Struktur, Finishing',
        ),
    }

    _list_view = {
        'columns': ['unit_id', 'name'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['unit_id', 'name'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Tahapan Unit'
        verbose_name_plural = 'Tahapan Unit'

    def __str__(self):
        return self.name or ''
