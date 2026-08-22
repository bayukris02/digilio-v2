from core.fields import IntegerField, Many2OneField, PercentageField
from core.model_meta import BaseModel


class ProjectUnit(BaseModel):
    """Unit pada Project — pilihan diambil dari master project.unit."""

    _model_name = 'project.project_unit'

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
        ),
        'unit_id': Many2OneField(
            label='Unit',
            relation='project.unit',
            required=True,
            help_text='Pilih unit dari master Unit',
        ),
        'qty_available': IntegerField(
            label='Unit Tersedia',
            default=0,
            help_text='Jumlah unit yang tersedia untuk dijual',
        ),
        'qty_sold': IntegerField(
            label='Unit Terjual',
            default=0,
            help_text='Jumlah unit yang sudah terjual',
        ),
        'sold_percentage': PercentageField(
            label='% Terjual',
            default=0,
            progress=True,
            compute='_compute_sold',
            depends=['qty_available', 'qty_sold'],
            help_text='Persentase terjual dari unit tersedia (otomatis)',
        ),
    }

    _list_view = {
        'columns': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Unit Proyek'
        verbose_name_plural = 'Unit Proyek'

    def _compute_sold(self):
        """% terjual = qty_sold / qty_available × 100 (clamp 0–100)."""
        available = float(self.qty_available or 0)
        sold = float(self.qty_sold or 0)
        if available > 0:
            self.sold_percentage = round(min(100.0, sold / available * 100), 2)
        else:
            self.sold_percentage = 0

    def __str__(self):
        return str(self.unit_id) if self.unit_id else ''
