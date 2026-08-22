from core.fields import Many2OneField, PercentageField
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
        'progress': PercentageField(
            label='Progress (%)',
            default=0,
            progress=True,
            help_text='Progress pengerjaan milestone (0–100%)',
        ),
    }

    _list_view = {
        'columns': ['milestone_id', 'progress'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['milestone_id', 'progress'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Proyek'
        verbose_name_plural = 'Baris Proyek'

    def __str__(self):
        return str(self.milestone_id) if self.milestone_id else ''
