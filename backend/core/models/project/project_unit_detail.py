from core.fields import CharField, Many2OneField, MonetaryField, One2ManyField
from core.model_meta import BaseModel


class ProjectUnitDetail(BaseModel):
    """Unit Detail pada Project — breakdown unit individual per tipe.

    Satu baris = satu unit fisik (mis. Tipe 36/72 → Unit 01, Unit 02).
    Data dibuat otomatis dari wizard Input Penjualan — read-only (tanpa CRUD manual).
    """

    _model_name = 'project.project_unit_detail'
    _allow_create = False  # data dibuat otomatis dari wizard Input Penjualan — Create manual diblokir

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
            editable_statuses=[],
        ),
        'unit_id': Many2OneField(
            label='Tipe Unit',
            relation='project.unit',
            required=True,
            allow_duplicate=True,
            help_text='Pilih tipe unit dari master Unit',
            editable_statuses=[],
        ),
        'customer': Many2OneField(
            label='Nama Customer',
            relation='sales.customer',
            required=True,
            editable_statuses=[],
            help_text='Customer pembeli unit ini (dari master Customer)',
        ),
        'selling_price': MonetaryField(
            label='Harga Jual',
            currency='IDR',
            editable_statuses=[],
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
            editable_statuses=[],
        ),
        'invoices': One2ManyField(
            label='Faktur',
            relation='accounting.customer_invoice',
            inverse_field='unit_detail',
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
        'columns': ['project_id', 'customer', 'unit_id', 'selling_price', 'est_cost', 'est_margin'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['project_id', 'customer', 'unit_id', 'selling_price', 'est_cost', 'est_margin'],
            'smart_buttons': [
                {'label': 'Faktur', 'model': 'accounting.customer_invoice', 'icon': 'FileTextOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'payments',
                'label': 'Pembayaran',
                'relation': 'payments',
                'columns': ['name', 'payment_method', 'payment_ref', 'amount', 'payment_date'],
                'read_only': True,
            },
            {
                'key': 'progress_lines',
                'label': 'Progress',
                'relation': 'progress_lines',
                'columns': ['name', 'progress', 'date', 'date_done', 'selisih'],
            },
            {
                'key': 'budget_lines',
                'label': 'Budget',
                'relation': 'progress_lines',
                'columns': ['name', 'budget', 'realisasi_budget', 'selisih_budget', 'mandor', 'catatan'],
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
        return str(self.customer) if self.customer else ''
