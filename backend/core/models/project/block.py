from core.fields import CharField, Many2OneField
from core.model_meta import BaseModel


class Block(BaseModel):
    """Blok pada Project — pengelompokan unit (mis. Blok A, Blok B)."""

    _model_name = 'project.block'
    _display_name = 'name'

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
        ),
        'name': CharField(
            label='Nama Blok',
            required=True,
            help_text='Nama blok / kelompok unit pada proyek',
        ),
    }

    _list_view = {
        'columns': ['project_id', 'name'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['project_id', 'name'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Blok'
        verbose_name_plural = 'Blok'

    def __str__(self):
        return self.name or ''
