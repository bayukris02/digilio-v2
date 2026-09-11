import re

from core.fields import BooleanField, CharField
from core.model_meta import BaseModel


class ProductCategory(BaseModel):
    _model_name = 'inventory.product_category'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Kategori', required=True),
        # Kode kategori 3 karakter — terisi otomatis dari nama, tetap bisa diubah user
        'code': CharField(
            label='Kode Kategori', required=True, max_length=3,
            compute='_compute_code', depends=['name'],
        ),
        # Auto generate kode produk: prefix jadi awalan SKU produk (mis. ELEK-001)
        'auto_generate': BooleanField(label='Auto Generate Kode'),
        'code_prefix': CharField(
            label='Prefix Kode', max_length=7,
            help_text='Maksimal 7 karakter, contoh: ATK',
        ),
    }

    _list_view = {
        'columns': ['code', 'name', 'auto_generate'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'code', 'auto_generate', 'code_prefix'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategori'

    def __str__(self):
        return self.name or ''

    @staticmethod
    def _code_from_name(name):
        """Kode 3 karakter gabungan kata dari nama kategori.

        - 1 kata   : 3 huruf pertama          → 'Elektronik'   → ELE
        - 2 kata   : 2 huruf kata-1 + 1 kata-2 → 'Oli Gardan'   → OLG
        - ≥3 kata  : inisial 3 kata pertama    → 'Alat Tulis Kantor' → ATK
        Nama pendek diulang huruf terakhirnya agar tetap 3 karakter ('AC' → ACC).
        """
        words = [w for w in re.split(r'[^0-9A-Za-z]+', (name or '').upper()) if w]
        if not words:
            return ''
        if len(words) >= 3:
            code = ''.join(w[0] for w in words[:3])
        elif len(words) == 2:
            first, second = words
            code = f'{first[:2]}{second[0]}' if len(first) >= 2 else f'{first}{second[:2]}'
        else:
            code = words[0][:3]
        while len(code) < 3:
            code += code[-1]
        return code[:3]

    @classmethod
    def _unique_code(cls, base, exclude_pk=None):
        """Kode unik: bila sudah dipakai kategori lain, ganti karakter terakhir
        dengan angka 1–9 (mis. OLG → OL1)."""
        if not base:
            return base

        def taken(code):
            qs = ProductCategory.objects.filter(code__iexact=code, is_deleted=False)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)
            return qs.exists()

        if not taken(base):
            return base
        for i in range(1, 10):
            candidate = f'{base[:2]}{i}'
            if not taken(candidate):
                return candidate
        return base  # biar guard di save() yang menolak dengan pesan jelas

    def _compute_code(self):
        """Isi kode dari nama bila masih kosong (nilai yang sudah ada tidak ditimpa)."""
        if (self.code or '').strip():
            return
        self.code = self._unique_code(self._code_from_name(self.name), self.pk)

    def save(self, *args, **kwargs):
        self._run_compute()  # kode dari nama (bila belum ada)
        code = (self.code or '').strip()
        if not code:
            raise ValueError('Kode Kategori wajib diisi.')
        if len(code) != 3:
            raise ValueError('Kode Kategori harus 3 karakter.')
        if self.auto_generate and not (self.code_prefix or '').strip():
            raise ValueError('Prefix Kode wajib diisi bila Auto Generate aktif.')
        # Guard: kode kategori tidak boleh sama (case-insensitive, antar kategori aktif)
        dup = ProductCategory.objects.filter(code__iexact=code, is_deleted=False)
        if self.pk:
            dup = dup.exclude(pk=self.pk)
        if dup.exists():
            raise ValueError(f'Kode Kategori "{code}" sudah dipakai kategori lain.')
        super().save(*args, **kwargs)

    @classmethod
    def get_model_config(cls):
        config = super().get_model_config()
        # -- Field config rules (generik, dibaca frontend) --
        config['field_config_rules'] = {
            # Ketik Nama Kategori → Kode dihitung ulang dari nama (field `code`
            # dibuang dari payload supaya backend derive fresh), tapi tidak
            # menimpa kode yang sudah diketik manual user (keep_manual).
            'name': {
                'compute_fields': [
                    {'field': 'code', 'refresh': True, 'keep_manual': True},
                ],
            },
            # Prefix hanya relevan saat auto generate aktif → tampil & wajib
            'code_prefix': {
                'hide_when': {'auto_generate': False},
                'field_props': {
                    'required': {
                        'depends_on': 'auto_generate',
                        'true': True,
                        'false': False,
                    },
                },
            },
        }
        return config
