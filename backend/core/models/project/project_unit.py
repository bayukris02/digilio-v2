from core.fields import (
    IntegerField, Many2OneField, PercentageField, FloatField,
    SelectionField, MonetaryField,
)
from core.model_meta import BaseModel


class ProjectUnit(BaseModel):
    """Unit pada Project — pilihan diambil dari master project.unit.

    Baris tab \"Unit Tersedia\": pilih Unit → luas/jenis terisi otomatis dari
    master, lalu Harga Jual Dasar dihitung dari harga per m² di header Project.
    """

    _model_name = 'project.project_unit'

    _fields = {
        'project_id': Many2OneField(
            label='Project',
            relation='project.project',
            required=True,
        ),
        'unit_id': Many2OneField(
            label='Unit',
            relation='project.unit',
            required=True,
            help_text='Pilih unit dari master Unit',
        ),
        'luas_tanah': FloatField(
            label='Luas Tanah (m²)',
            editable_statuses=[],
            compute='_compute_from_unit',
            depends=['unit_id'],
            help_text='Otomatis dari master Unit',
        ),
        'luas_bangunan': FloatField(
            label='Luas Bangunan (m²)',
            editable_statuses=[],
            compute='_compute_from_unit',
            depends=['unit_id'],
            help_text='Otomatis dari master Unit',
        ),
        'jenis_bangunan': SelectionField(
            label='Jenis Bangunan',
            options=[('lantai_1', 'Lantai 1'), ('lantai_2', 'Lantai 2')],
            editable_statuses=[],
            compute='_compute_from_unit',
            depends=['unit_id'],
            help_text='Otomatis dari master Unit',
        ),
        'harga_jual_dasar': MonetaryField(
            label='Harga Jual Dasar',
            currency='IDR',
            compute='_compute_harga_jual_dasar',
            depends=['luas_tanah', 'luas_bangunan', 'jenis_bangunan'],
            editable_statuses=[],
            help_text='Harga Tanah/m² × Luas Tanah + Harga Bangunan/m² × Luas Bangunan',
        ),
        'qty_available': IntegerField(
            label='Unit Tersedia',
            default=0,
            help_text='Jumlah unit yang tersedia untuk dijual',
        ),
        'qty_sold': IntegerField(
            label='Unit Terjual',
            default=0,
            help_text='Jumlah unit yang sudah terjual',
        ),
        'sold_percentage': PercentageField(
            label='% Terjual',
            default=0,
            progress=True,
            compute='_compute_sold',
            depends=['qty_available', 'qty_sold'],
            help_text='Persentase terjual dari unit tersedia (otomatis)',
        ),
    }

    _list_view = {
        'columns': ['unit_id', 'luas_tanah', 'luas_bangunan', 'jenis_bangunan',
                    'harga_jual_dasar', 'qty_available', 'qty_sold', 'sold_percentage'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['unit_id', 'luas_tanah', 'luas_bangunan', 'jenis_bangunan',
                       'harga_jual_dasar', 'qty_available', 'qty_sold', 'sold_percentage'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Unit Proyek'
        verbose_name_plural = 'Unit Proyek'

    def _compute_sold(self):
        """% terjual = qty_sold / qty_available × 100 (clamp 0–100)."""
        available = float(self.qty_available or 0)
        sold = float(self.qty_sold or 0)
        if available > 0:
            self.sold_percentage = round(min(100.0, sold / available * 100), 2)
        else:
            self.sold_percentage = 0

    def _compute_from_unit(self):
        """Salin Luas Tanah, Luas Bangunan & Jenis Bangunan dari master Unit.

        Dipicu compute endpoint saat unit_id diubah di notebook (baris belum
        tentu punya pk), dan saat save. Tidak menghapus nilai bila unit kosong.
        """
        unit = getattr(self, 'unit_id', None)
        if unit is None or not getattr(unit, 'pk', None):
            return
        self.luas_tanah = unit.luas_tanah
        self.luas_bangunan = unit.luas_bangunan
        self.jenis_bangunan = unit.jenis_bangunan

    def _compute_harga_jual_dasar(self):
        """Harga Jual Dasar = Harga Tanah/m² × Luas Tanah
        + Harga Bangunan/m² (L1/L2 sesuai jenis) × Luas Bangunan.

        Harga per m² diambil dari header Project (project_id). Baris tanpa
        project atau tanpa luas → nilai dibiarkan (tidak dihitung).
        """
        project = getattr(self, 'project_id', None)
        if project is None or not getattr(project, 'pk', None):
            return
        lt = float(self.luas_tanah or 0)
        lb = float(self.luas_bangunan or 0)
        if lt <= 0 and lb <= 0:
            return
        ht = float(project.harga_tanah_m2 or 0)
        if self.jenis_bangunan == 'lantai_2':
            hb = float(project.harga_bangunan_l2_m2 or 0)
        else:
            hb = float(project.harga_bangunan_l1_m2 or 0)
        self.harga_jual_dasar = round(ht * lt + hb * lb, 2)

    def __str__(self):
        return str(self.unit_id) if self.unit_id else ''
