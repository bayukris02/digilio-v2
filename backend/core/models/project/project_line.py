from core.fields import Many2OneField
from core.model_meta import BaseModel


class ProjectLine(BaseModel):
    """Line milestone pada Project — pilihan diambil dari master project.milestone."""

    _model_name = 'project.project_line'

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
        ),
        'milestone_id': Many2OneField(
            label='Milestone',
            relation='project.milestone',
            required=True,
            help_text='Pilih milestone dari master Milestone',
        ),
    }

    _list_view = {
        'columns': ['milestone_id'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['milestone_id'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project Line'
        verbose_name_plural = 'Project Lines'

    def __str__(self):
        return str(self.milestone_id) if self.milestone_id else ''
