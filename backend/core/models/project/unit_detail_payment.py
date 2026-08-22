from core.fields import (
    CharField, DateField, MonetaryField, Many2OneField,
)
from core.model_meta import BaseModel


class UnitDetailPayment(BaseModel):
    """Pembayaran per unit detail (unit di dalam project)."""

    _model_name = 'project.unit_detail_payment'
    _display_name = 'name'

    _fields = {
        'unit_detail_id': Many2OneField(
            label='Unit Detail',
            relation='project.project_unit_detail',
            required=True,
        ),
        'name': CharField(
            label='Pembayaran',
            required=True,
            help_text='Misal: DP, Termin 1, Termin 2, Pelunasan',
        ),
        'amount': MonetaryField(
            label='Jumlah',
            currency='IDR',
        ),
        'payment_date': DateField(
            label='Tanggal',
        ),
    }

    _list_view = {
        'columns': ['name', 'amount', 'payment_date'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'amount', 'payment_date'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Pembayaran Unit'
        verbose_name_plural = 'Pembayaran Unit'

    def __str__(self):
        return self.name or ''
