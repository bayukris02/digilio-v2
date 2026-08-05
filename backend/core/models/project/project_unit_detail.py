from core.fields import CharField, Many2OneField
from core.model_meta import BaseModel


class ProjectUnitDetail(BaseModel):
    """Unit Detail pada Project — breakdown unit individual per tipe.

    Satu baris = satu unit fisik (mis. Tipe 36/72 → Unit 01, Unit 02).
    """

    _model_name = 'project.project_unit_detail'

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
        ),
        'unit_id': Many2OneField(
            label='Tipe Unit',
            relation='project.unit',
            required=True,
            help_text='Pilih tipe unit dari master Unit',
        ),
        'name': CharField(
            label='Nama Unit',
            required=True,
            help_text='Contoh: Unit 01, Blok A1',
        ),
    }

    _list_view = {
        'columns': ['name', 'unit_id'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'unit_id'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Unit Detail'
        verbose_name_plural = 'Unit Details'

    def __str__(self):
        return self.name or ''
