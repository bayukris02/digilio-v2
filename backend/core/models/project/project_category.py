from core.fields import CharField
from core.model_meta import BaseModel


class ProjectCategory(BaseModel):
    """Master kategori proyek (acuan untuk field category pada project.project)."""

    _model_name = 'project.project_category'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Kategori',
            required=True,
            help_text='Misal: Konstruksi, Infrastruktur, Interior, Renovasi, Lainnya',
        ),
        'code': CharField(label='Kode Kategori'),
    }

    _list_view = {
        'columns': ['code', 'name'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'code'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project Category'
        verbose_name_plural = 'Project Categories'

    def __str__(self):
        return self.name or ''
