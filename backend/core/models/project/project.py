from core.fields import (
    CharField, DateField, MonetaryField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class Project(BaseModel):
    """Inisiasi dan pencatatan data dasar proyek baru."""

    _model_name = 'project.project'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Proyek', required=True),
        'category': Many2OneField(
            label='Kategori',
            relation='project.project_category',
            required=False,
            help_text='Kategori proyek dari master Project Categories',
        ),
        'date_start': DateField(label='Tanggal Mulai'),
        'date_end': DateField(label='Tanggal Selesai'),
        'project_manager': Many2OneField(
            label='Manajer Proyek (PM)',
            relation='settings.user',
            required=False,
        ),
        'contract_value': MonetaryField(
            label='Nilai Kontrak',
            currency='IDR',
        ),
        'client': Many2OneField(
            label='Client / Owner',
            relation='sales.customer',
            required=False,
        ),
        'location': CharField(label='Lokasi'),
        'executing_entity': Many2OneField(
            label='Entitas Pelaksana',
            relation='settings.company',
            required=False,
        ),
        'lines': One2ManyField(
            label='Project Lines',
            relation='project.project_line',
            inverse_field='project_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'category', 'client', 'project_manager', 'date_start', 'date_end', 'contract_value', 'location'],
        'filters': ['category'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'category', 'date_start', 'date_end'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['project_manager', 'contract_value', 'client', 'location', 'executing_entity'],
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Project Milestones',
                'relation': 'lines',
                'columns': ['milestone_id'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return self.name or ''
