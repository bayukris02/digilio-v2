"""Multi Satuan produk — daftar satuan alternatif + konversi ke satuan utama.

Baris **satuan utama** TIDAK disimpan di tabel ini: nilainya turunan dari field
`Satuan` (uom) di header produk, dan ditampilkan sebagai baris pertama oleh
`Product.to_record()`. Tabel ini hanya menyimpan satuan tambahan.
"""
from django.db import models
from core.fields import (
    CharField, FloatField, SelectionField, BooleanField, Many2OneField,
)
from core.model_meta import BaseModel

SIFAT_BESAR = 'besar'
SIFAT_KECIL = 'kecil'
KETERANGAN_BASE = 'Satuan acuan konversi'


class ProductUnit(BaseModel):
    _model_name = 'inventory.product_unit'

    _fields = {
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
        ),
        'uom': Many2OneField(
            label='Nama Satuan',
            relation='inventory.uom',
            required=True,
        ),
        'sifat': SelectionField(
            label='Sifat Satuan',
            required=True,
            options=[
                (SIFAT_BESAR, 'Lebih besar dari satuan utama'),
                (SIFAT_KECIL, 'Lebih kecil dari satuan utama'),
            ],
        ),
        'konversi': FloatField(label='Konversi', default=1, required=True),
        # Baris satuan utama (baris 1 tab Multi Satuan) = baris TERSIMPAN dengan
        # is_base = True — nilainya mengikuti field Satuan di header produk.
        # Inilah sumber tunggal satuan produk (mis. kolom Satuan di PR), jadi
        # baris ini punya PK dan bisa dirujuk many2one.
        'is_base': BooleanField(
            label='Satuan Utama', default=False, chatter_show=False,
        ),
        'keterangan': CharField(label='Keterangan', compute='_compute_keterangan'),
    }

    _list_view = {
        'columns': ['product', 'uom', 'sifat', 'konversi', 'keterangan'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'uom', 'sifat', 'konversi', 'is_base', 'keterangan'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Multi Satuan'
        verbose_name_plural = 'Multi Satuan'

    # ── Helper teks keterangan (dipakai juga oleh Product) ──

    @staticmethod
    def resolve_uom(value):
        """Instance inventory.uom dari nilai apa pun (instance / id / dict {id}/{value})."""
        if value is None:
            return None
        if hasattr(value, 'pk') and hasattr(value, '_meta'):
            return value
        pk = value.get('id') or value.get('value') if isinstance(value, dict) else value
        if not pk:
            return None
        from core.model_meta import ErpModelBase
        uom_cls = ErpModelBase._model_registry.get('inventory.uom')
        if uom_cls is None:
            return None
        return uom_cls.objects.filter(pk=pk, is_deleted=False).first()

    @classmethod
    def uom_label(cls, uom):
        """Label satuan untuk keterangan: kode (fallback nama) — mis. 'box', 'PCS'."""
        uom = cls.resolve_uom(uom)
        if uom is None:
            return ''
        return getattr(uom, 'code', None) or getattr(uom, 'name', None) or ''

    @classmethod
    def uom_display(cls, uom):
        """Nama tampil satuan untuk kolom Nama Satuan — HANYA nama (tanpa prefix
        kode). Mengikuti `_display_name` model satuan bila dideklarasikan."""
        uom = cls.resolve_uom(uom)
        if uom is None:
            return ''
        field = getattr(uom, '_display_name', None) or 'name'
        return getattr(uom, field, None) or getattr(uom, 'name', None) or str(uom)

    @classmethod
    def build_keterangan(cls, base_uom, uom, sifat, konversi):
        """Teks keterangan otomatis.

        Contoh: box + 'besar' + 10 → 'box 10x lebih besar dari PCS'.
        """
        if sifat not in (SIFAT_BESAR, SIFAT_KECIL):
            return ''
        label = cls.uom_label(uom)
        base = cls.uom_label(base_uom)
        if not label or not base:
            return ''
        arah = 'lebih besar' if sifat == SIFAT_BESAR else 'lebih kecil'
        try:
            faktor = float(konversi or 0)
        except (TypeError, ValueError):
            faktor = 0
        return f'{label} {faktor:g}x {arah} dari {base}'

    # ── Computed ──

    def _compute_keterangan(self):
        """Keterangan turunan: satuan + sifat + konversi vs satuan utama produk.

        Baris satuan utama (is_base) → keterangan tetap 'Satuan acuan konversi'.
        """
        if self.is_base:
            self.keterangan = KETERANGAN_BASE
            return
        self.keterangan = self.build_keterangan(
            getattr(self.product, 'uom', None) if self.product_id else None,
            self.uom, self.sifat, self.konversi,
        )

    def save(self, *args, **kwargs):
        """Baris satuan utama: konversi 1, satuan mengikuti header produk, dan
        hanya boleh ADA SATU baris is_base aktif per produk (duplikat → terhapus).
        """
        if self.is_base:
            self.konversi = 1
            if not self.uom_id and self.product_id:
                self.uom_id = getattr(self.product, 'uom_id', None)
        super().save(*args, **kwargs)

        if self.is_base:
            dups = ProductUnit.objects.filter(
                product_id=self.product_id, is_base=True, is_deleted=False,
            ).exclude(pk=self.pk)
            for dup in dups:
                dup.is_deleted = True
                dup.save()

    def to_record(self):
        data = super().to_record()
        # Nama tampil baris multi satuan = nama satuannya (dipakai label
        # many2one ke `inventory.product_unit`, mis. kolom Satuan di PR).
        label = self.uom_display(getattr(self, 'uom', None))
        data['name'] = label
        if label:
            data['display_name'] = label
        # Kolom "Nama Satuan" cukup nama satuan saja — buang prefix kode
        # (mis. "[PCS] PCS" → "PCS").
        uom_val = data.get('uom')
        if label and isinstance(uom_val, dict):
            data['uom'] = {**uom_val, 'name': label}
        return data

    def __str__(self):
        """Label default: nama satuan (dipakai saat record ini jadi nilai
        many2one di model lain, mis. Satuan pada baris Permintaan Pembelian)."""
        return self.uom_display(getattr(self, 'uom', None)) or (f'#{self.pk}' if self.pk else '')
