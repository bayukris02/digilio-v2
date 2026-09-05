from core.fields import (
    CharField, TextField, MonetaryField, FloatField, SelectionField, One2ManyField,
)
from core.model_meta import BaseModel


class Unit(BaseModel):
    """Daftar luaran (output) fisik maupun non-fisik yang dihasilkan dari proyek."""

    _model_name = 'project.unit'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Unit Produk',
            required=True,
            help_text='Otomatis dari Luas Bangunan / Luas Tanah (mis. 40/62)',
            compute='_compute_name',
            depends=['luas_bangunan', 'luas_tanah'],
            editable_statuses=[],
        ),
        'jenis_bangunan': SelectionField(
            label='Jenis Bangunan',
            options=[('lantai_1', 'Lantai 1'), ('lantai_2', 'Lantai 2')],
            required=False,
        ),
        'luas_tanah': FloatField(
            label='Luas Tanah (m²)',
        ),
        'luas_bangunan': FloatField(
            label='Luas Bangunan (m²)',
        ),
        'base_price': MonetaryField(
            label='Harga Jual Dasar',
            currency='IDR',
        ),
        'specifications': TextField(label='Spesifikasi'),
        'quality_standard': TextField(
            label='Standar Kualitas (Checkout List)',
            help_text='Checklist standar kualitas luaran',
        ),
        'unit_progress_lines': One2ManyField(
            label='Tahapan',
            relation='project.unit_progress',
            inverse_field='unit_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'jenis_bangunan', 'luas_tanah', 'luas_bangunan', 'base_price'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'jenis_bangunan', 'luas_tanah', 'luas_bangunan', 'base_price'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['specifications', 'quality_standard'],
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'unit_progress_lines',
                'label': 'Tahapan',
                'relation': 'unit_progress_lines',
                'columns': ['name'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Unit'
        verbose_name_plural = 'Unit'

    def __str__(self):
        return self.name or ''

    # ── Computed ──

    def _fmt(self, val):
        """Format luas tanpa desimal jika bilangan bulat (40.0 → '40')."""
        if val is None:
            return ''
        num = float(val)
        return str(int(num)) if num == int(num) else str(num)

    def _compute_name(self):
        """Unit Produk = '{Luas Bangunan}/{Luas Tanah}' (mis. 40/62).

        Hanya menimpa saat kedua luas terisi — data lama yang luasnya kosong
        tidak diubah ketika record di-save ulang.
        """
        lb = getattr(self, 'luas_bangunan', None)
        lt = getattr(self, 'luas_tanah', None)
        if lb not in (None, '') and lt not in (None, ''):
            try:
                self.name = f"{self._fmt(lb)}/{self._fmt(lt)}"
            except (TypeError, ValueError):
                pass
        # Hindari NULL saat create tanpa luas (name NOT NULL di DB)
        if self.name is None:
            self.name = ''
