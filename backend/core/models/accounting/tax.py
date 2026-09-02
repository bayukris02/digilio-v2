"""
Tax (master pajak) — dipilih many2many di baris dokumen (SO/PO/Faktur/Tagihan).
Rate dalam persen; tax_amount dihitung backend = Σ rate × (subtotal − diskon).
"""
from django.db import models
from core.fields import (
    CharField, FloatField, TextField, BooleanField,
)
from core.model_meta import BaseModel


class Tax(BaseModel):
    """Pajak — tarif yang bisa dipilih (bisa lebih dari satu per baris)."""

    _model_name = 'accounting.tax'
    _display_name = None  # fallback __str__ → '[PPN] Pajak Pertambahan Nilai (11%)'

    _fields = {
        'name': CharField(
            label='Nama Pajak',
            required=True,
            help_text='Contoh: PPN, PPh 23',
        ),
        'rate': FloatField(
            label='Tarif (%)',
            required=True,
            default=0,
            help_text='Persentase tarif pajak, mis. 11 untuk PPN 11%',
        ),
        'description': TextField(label='Deskripsi'),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['name', 'rate', 'is_active'],
        'filters': ['is_active'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'rate', 'description', 'is_active'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Pajak'
        verbose_name_plural = 'Pajak'

    def __str__(self):
        rate = float(self.rate or 0)
        label = f'{self.name} ({rate:g}%)' if rate else f'{self.name}'
        return label


def _norm_tax_ids(value):
    """Normalisasi nilai 'taxes' dari payload dict / list id / objek → [id, ...]."""
    if value is None:
        return []
    out = []
    for v in value if isinstance(value, (list, tuple)) else [value]:
        if isinstance(v, dict):
            out.append(v.get('id') or v.get('pk') or v.get('value'))
        elif hasattr(v, 'pk'):
            out.append(v.pk)
        else:
            out.append(v)
    # Hanya id numerik — buang ''/None/bukan angka (guard payload kosong).
    clean = []
    for x in out:
        if x is None:
            continue
        try:
            clean.append(int(float(x)))
        except (TypeError, ValueError):
            continue
    return clean


def taxes_total_rate(value):
    """Total tarif (%) dari pilihan pajak (terima [id], [{id,name}], objek, atau instance)."""
    ids = _norm_tax_ids(value)
    if not ids:
        return 0.0
    from core.models.accounting.tax import Tax
    return sum(float(t.rate or 0) for t in Tax.objects.filter(pk__in=ids, is_active=True))
