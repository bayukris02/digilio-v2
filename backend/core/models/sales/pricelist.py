from django.db import models
from core.fields import (
    CharField, DateField, One2ManyField,
)
from core.model_meta import BaseModel


class SalesPricelist(BaseModel):
    """Daftar harga jual (master) — tanpa lock ke customer.

    Satu master berisi periode aktif (start/end date) dan baris harga
    (product + min/max qty + fix price). Dipakai sebagai acuan harga jual
    umum; integrasi ke dokumen penjualan menyusul.
    """

    _model_name = 'sales.pricelist'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Pricelist',
            required=True,
            help_text='Contoh: Retail Pricelist, Grosir Pricelist',
        ),
        'start_date': DateField(
            label='Periode Mulai',
            required=False,
            help_text='Kosongkan jika berlaku sejak awal',
        ),
        'end_date': DateField(
            label='Periode Selesai',
            required=False,
            help_text='Kosongkan jika aktif terus (tanpa batas akhir)',
        ),
        'pricelist_lines': One2ManyField(
            label='Baris Harga',
            relation='sales.pricelist.line',
            inverse_field='pricelist_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'start_date', 'end_date'],
        'filters': ['name'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'start_date', 'end_date'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'color': 'green', 'action': 'print'},
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Harga',
                'relation': 'pricelist_lines',
                'columns': ['product', 'uom', 'min_qty', 'max_qty', 'fix_price'],
                'summary': {
                    'columns': {'fix_price': 'sum'},
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Sales Pricelist'
        verbose_name_plural = 'Sales Pricelists'

    def __str__(self):
        return str(getattr(self, 'name', '') or '')
