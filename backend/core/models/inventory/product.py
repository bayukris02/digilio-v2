from django.core.exceptions import ObjectDoesNotExist
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
        # unik=True → satu kode hanya boleh dipakai 1 produk (kosong = NULL).
        'code': CharField(
            label='SKU / Kode', unique=True,
            compute='_compute_code', depends=['category'],
        ),
        'description': TextField(label='Deskripsi'),
        'category': Many2OneField(
            label='Kategori',
            relation='inventory.product_category',
            required=True,
        ),
        # Frontend-only: true bila kategori terpilih auto generate kode.
        # Computed → ikut pada GET (form edit langsung readonly tanpa race)
        # dan pada compute API (saat user ganti kategori).
        'category_auto_generate': BooleanField(
            label='Auto Generate', virtual=True, chatter_show=False,
            compute='_compute_category_auto_generate',
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
            # Ganti Kategori → minta SKU + flag auto generate ke compute API.
            # with_record: sertakan id record → backend membaca kode TERSIMPAN,
            # jadi pindah kategori lalu balik lagi TIDAK mengubah SKU.
            'category': {
                'compute_fields': ['code', 'category_auto_generate'],
                'with_record': True,
            },
            # Kategori auto generate → SKU readonly (terisi <prefix>-001)
            'code': {'readonly_when': {'category_auto_generate': True}},
        }
        return config

    def _next_auto_code(self, prefix):
        """Nomor SKU berikutnya untuk prefix ini — GLOBAL lintas kategori
        (min 3 digit → 001; >999 → 1000), selalu memilih nomor yang belum dipakai."""
        codes = self.__class__.objects.filter(
            code__startswith=f'{prefix}-',
        ).values_list('code', flat=True)
        last = 0
        for c in codes:
            suffix = (c or '')[len(prefix) + 1:]
            if suffix.isdigit():
                last = max(last, int(suffix))
        n = last + 1
        while self.__class__.objects.filter(code=f'{prefix}-{n:03d}').exists():
            n += 1
        return f'{prefix}-{n:03d}'

    def _resolve_category(self):
        """Kategori terkait (None bila kosong/tidak valid)."""
        try:
            return self.category
        except ObjectDoesNotExist:
            return None

    def _stored_code(self):
        """Kode tersimpan di DB untuk produk ini ('' bila belum ada)."""
        if not self.pk:
            return ''
        return type(self).objects.filter(pk=self.pk).values_list('code', flat=True).first() or ''

    def _compute_code(self):
        """SKU otomatis <prefix kategori>-<nomor urut> bila kategori auto generate.

        Aturan "tidak berubah": kode yang sudah ada untuk prefix kategori ini
        dipertahankan — kode tersimpan di DB lebih dulu (kategori awal produk),
        baru kode dari form (mis. produk baru). Hanya di-generate ulang bila
        kode lama tidak ber-prefix kategori yang dipilih.
        """
        category = self._resolve_category()
        if category is None or not getattr(category, 'auto_generate', False):
            return
        prefix = (getattr(category, 'code_prefix', '') or '').strip()
        if not prefix:
            return
        marker = f'{prefix}-'
        stored = self._stored_code()
        if stored.startswith(marker):
            self.code = stored
            return
        if (self.code or '').startswith(marker):
            return
        self.code = self._next_auto_code(prefix)

    def _compute_category_auto_generate(self):
        """Flag form: kategori terpilih auto generate kode? (true/false)."""
        category = self._resolve_category()
        self.category_auto_generate = bool(
            category is not None and getattr(category, 'auto_generate', False)
        )

    def save(self, *args, **kwargs):
        self._run_compute()  # hitung SKU lebih dulu (bila kategori auto generate)
        # SKU kosong disimpan sebagai NULL agar constraint unik hanya berlaku
        # untuk kode yang benar-benar terisi ('' tidak boleh dobel).
        if self.code is not None and not str(self.code).strip():
            self.code = None
        # Guard unik (case-insensitive) — pesan jelas sebelum constraint DB
        if self.code:
            dup = self.__class__.objects.filter(code__iexact=self.code)
            if self.pk:
                dup = dup.exclude(pk=self.pk)
            if dup.exists():
                raise ValueError(f'Kode produk "{self.code}" sudah dipakai produk lain.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or ''
