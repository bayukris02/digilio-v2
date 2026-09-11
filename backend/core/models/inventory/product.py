from django.core.exceptions import ObjectDoesNotExist, ValidationError
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
        # HPP (Harga Pokok): Manual → diisi user; kategori dengan Perhitungan
        # HPP = Otomatis (AVCO) → milik mesin (0 saat baru pindah ke AVCO,
        # berikutnya diisi Proses Pembelian/Stock Adjustment).
        'cost': MonetaryField(
            label='HPP (Harga Pokok)', currency='IDR',
            compute='_compute_cost', depends=['category'],
        ),
        # Frontend-only: true bila kategori terpilih pakai Perhitungan HPP
        # Otomatis (AVCO) → field HPP jadi readonly.
        'category_cost_method': CharField(
            label='Perhitungan HPP Kategori', virtual=True, chatter_show=False,
            compute='_compute_category_cost_method',
        ),
        # Frontend-only: true bila produk sudah punya mutasi stok (row ledger
        # aktif). Dipakai rule generik: Kategori/Satuan/Tipe Produk terkunci.
        'has_stock_movement': BooleanField(
            label='Ada Mutasi Stok', virtual=True, chatter_show=False,
            compute='_compute_has_stock_movement',
        ),
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
            'fields': ['name', 'code', 'category', 'tipe_product', 'price',
                       'cost', 'uom', 'weight', 'is_active'],
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
            # readonly_when: sudah ada mutasi stok → Kategori terkunci.
            'category': {
                'compute_fields': ['code', 'category_auto_generate', 'category_cost_method'],
                'with_record': True,
                'readonly_when': {'has_stock_movement': True},
            },
            # Kategori auto generate → SKU readonly (terisi <prefix>-001)
            'code': {'readonly_when': {'category_auto_generate': True}},
            # Sudah ada mutasi stok → Satuan & Tipe Produk terkunci.
            'uom': {'readonly_when': {'has_stock_movement': True}},
            'tipe_product': {'readonly_when': {'has_stock_movement': True}},
            # HPP readonly bila kategori pakai AVCO (milik mesin) atau Non-Stock.
            'cost': {'readonly_when': {'category_cost_method': 'avco', 'tipe_product': 'Non Stock'}},
        }
        return config

    # ── Guard: field yang terkunci setelah ada mutasi stok ──
    _LOCKED_AFTER_MOVEMENT = (
        ('category_id', 'Kategori'),
        ('uom_id', 'Satuan'),
        ('tipe_product', 'Tipe Produk'),
    )

    def _stored_values(self):
        """Snapshot nilai tersimpan di DB (None untuk record baru).

        `category_cost_method` = Perhitungan HPP kategori TERSIMPAN — dipakai
        mendeteksi perpindahan kategori ke/dari AVCO.
        """
        if not self.pk:
            return None
        row = type(self).objects.filter(pk=self.pk).values(
            'code', 'cost', 'category_id', 'uom_id', 'tipe_product',
        ).first()
        if row:
            cat_cls = type(self)._meta.get_field('category').related_model
            prev = cat_cls.objects.filter(pk=row['category_id']).values('cost_method').first()
            row['category_cost_method'] = (prev or {}).get('cost_method')
        return row

    def _has_stock_movement(self):
        """True bila produk sudah punya row ledger stok aktif (mutasi apa pun)."""
        if not self.pk:
            return False
        try:
            from core.stock_engine import StockEngine
            ledger_cls = StockEngine._ledger_cls()
        except Exception:
            ledger_cls = None
        if ledger_cls is None:
            return False
        return ledger_cls.objects.filter(product_id=self.pk, is_deleted=False).exists()

    def _compute_has_stock_movement(self):
        self.has_stock_movement = self._has_stock_movement()

    def _check_locked_after_movement(self, stored):
        """Tolak perubahan Kategori/Satuan/Tipe Produk bila sudah ada mutasi stok."""
        if not stored or not self._has_stock_movement():
            return
        for key, label in self._LOCKED_AFTER_MOVEMENT:
            old = stored.get(key)
            new = getattr(self, key, None)
            if hasattr(new, 'pk'):
                new = new.pk
            if old != new:
                raise ValidationError(
                    f'{label} tidak dapat diubah karena produk sudah memiliki mutasi stok.'
                )

    def _apply_cost_method(self, stored):
        """HPP otomatis (AVCO) = milik mesin: reset ke 0 saat produk baru
        masuk kategori AVCO, setelah itu nilainya diisi oleh proses
        pembelian/penyesuaian stok (average cost)."""
        if self._category_cost_method() != 'avco':
            return
        if stored is None or stored.get('category_cost_method') != 'avco':
            self.cost = 0

    def _compute_cost(self):
        """HPP: Manual → nilai dari user dibiarkan apa adanya; AVCO → milik
        mesin (0 saat baru berpindah ke kategori AVCO, selain itu dipertahankan
        supaya nilai hasil Proses Pembelian/Stock Adjustment tidak hilang)."""
        if self._category_cost_method() != 'avco':
            return
        self._apply_cost_method(self._stored_values())

    def _compute_category_cost_method(self):
        """Flag form: Perhitungan HPP kategori terpilih (manual/avco)."""
        self.category_cost_method = self._category_cost_method()

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

    def _category_cost_method(self):
        """Perhitungan HPP kategori terpilih: 'manual' / 'avco'."""
        category = self._resolve_category()
        return (getattr(category, 'cost_method', None) or 'manual')

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
        # Snapshot nilai DB sebelum ditimpa payload (record baru → None)
        stored = self._stored_values()
        # Guard: Kategori/Satuan/Tipe Produk terkunci setelah ada mutasi stok
        self._check_locked_after_movement(stored)
        self._run_compute()  # SKU (kategori auto generate) + HPP (kategori AVCO)
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
