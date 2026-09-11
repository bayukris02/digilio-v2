from django.db import models
from core.fields import (
    CharField, TextField, BooleanField, MonetaryField,
    SelectionField, FloatField, Many2OneField,
)
from core.model_meta import BaseModel


class Product(BaseModel):
    _model_name = 'inventory.product'
    _display_name = 'code'

    _fields = {
        'name': CharField(label='Nama Produk', required=True),
        # SKU: dihitung backend (compute) — otomatis <prefix kategori>-<nomor urut>
        # bila kategori auto generate, selain itu kode manual apa adanya.
        'code': CharField(label='SKU / Kode', compute='_compute_code', depends=['category']),
        'description': TextField(label='Deskripsi'),
        'category': Many2OneField(
            label='Kategori',
            relation='inventory.product_category',
            required=True,
            # Virtual flag di form: dipakai field_config_rules (readonly SKU)
            autofill={'category_auto_generate': 'auto_generate'},
        ),
        # Frontend-only: true bila kategori terpilih auto generate kode.
        'category_auto_generate': BooleanField(
            label='Auto Generate', virtual=True, chatter_show=False,
        ),
        'tipe_product': SelectionField(
            label='Tipe Produk',
            options=[('Stock', 'Stock'), ('Non Stock', 'Non Stock')],
            default='Stock',
        ),
        'price': MonetaryField(label='Harga Jual', currency='IDR'),
        'cost': MonetaryField(label='Harga Beli', currency='IDR'),
        'uom': Many2OneField(
            label='Satuan',
            relation='inventory.uom',
            required=True,
        ),
        'weight': FloatField(label='Berat (kg)'),
        'is_active': BooleanField(label='Aktif', default=True),
    }

    _list_view = {
        'columns': ['code', 'name', 'category', 'tipe_product', 'price', 'uom', 'is_active'],
        'filters': ['category', 'tipe_product', 'is_active'],
        'group_by': ['category'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'code', 'category', 'tipe_product', 'price', 'cost', 'uom', 'weight', 'is_active'],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'details',
                'label': 'Detail',
                'fields': ['description'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'

    @classmethod
    def get_model_config(cls):
        config = super().get_model_config()
        # -- Field config rules (generik, dibaca frontend) --
        config['field_config_rules'] = {
            # Pilih Kategori → minta SKU terhitung dari backend (compute API)
            'category': {'compute_fields': ['code']},
            # Kategori auto generate → SKU readonly (terisi <prefix>-001)
            'code': {'readonly_when': {'category_auto_generate': True}},
        }
        return config

    def _next_auto_code(self, category, prefix):
        """Nomor urut berikutnya untuk kategori (min 3 digit → 001; >999 → 1000)."""
        codes = self.__class__.objects.filter(
            category=category, code__startswith=f'{prefix}-',
        ).values_list('code', flat=True)
        last = 0
        for c in codes:
            suffix = (c or '')[len(prefix) + 1:]
            if suffix.isdigit():
                last = max(last, int(suffix))
        return f'{prefix}-{last + 1:03d}'

    def _compute_code(self):
        """SKU otomatis <prefix kategori>-<nomor urut> bila kategori auto generate.

        Kode yang sudah ber-prefix sama dibiarkan (tidak di-generate ulang),
        sehingga edit produk tidak mengubah SKU yang sudah terbit.
        """
        from django.core.exceptions import ObjectDoesNotExist
        try:
            category = self.category
        except ObjectDoesNotExist:
            return
        if category is None or not getattr(category, 'auto_generate', False):
            return
        prefix = (getattr(category, 'code_prefix', '') or '').strip()
        if not prefix:
            return
        if (self.code or '').startswith(f'{prefix}-'):
            return
        self.code = self._next_auto_code(category, prefix)

    def __str__(self):
        return self.name or ''
