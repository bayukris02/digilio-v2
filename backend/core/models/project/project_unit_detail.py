from core.fields import CharField, Many2OneField, MonetaryField, One2ManyField
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
            allow_duplicate=True,
            help_text='Pilih tipe unit dari master Unit',
        ),
        'name': CharField(
            label='Nama Unit',
            required=True,
            help_text='Contoh: Unit 01, Blok A1',
        ),
        'selling_price': MonetaryField(
            label='Harga Jual',
            currency='IDR',
        ),
        'est_cost': MonetaryField(
            label='Est. Biaya Konstruksi',
            currency='IDR',
        ),
        'est_margin': MonetaryField(
            label='Est. Margin',
            currency='IDR',
            compute='_compute_margin',
            depends=['selling_price', 'est_cost'],
        ),
        'payments': One2ManyField(
            label='Pembayaran',
            relation='project.unit_detail_payment',
            inverse_field='unit_detail_id',
        ),
        'progress_lines': One2ManyField(
            label='Progress',
            relation='project.unit_detail_progress',
            inverse_field='unit_detail_id',
        ),
    }

    _list_view = {
        'columns': ['project_id', 'name', 'unit_id', 'selling_price', 'est_cost', 'est_margin'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['project_id', 'name', 'unit_id', 'selling_price', 'est_cost', 'est_margin'],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'payments',
                'label': 'Pembayaran',
                'relation': 'payments',
                'columns': ['name', 'amount', 'payment_date'],
            },
            {
                'key': 'progress_lines',
                'label': 'Progress',
                'relation': 'progress_lines',
                'columns': ['name', 'progress', 'date'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Detail Unit'
        verbose_name_plural = 'Detail Unit'

    def _compute_margin(self):
        """Est. Margin = Harga Jual - Est. Biaya Konstruksi."""
        selling_price = float(self.selling_price or 0)
        est_cost = float(self.est_cost or 0)
        self.est_margin = round(selling_price - est_cost, 2)

    def __str__(self):
        return self.name or ''
