from datetime import date

from core.fields import (
    CharField, DateField, MonetaryField, SelectionField, TextField, Many2OneField,
)
from core.model_meta import BaseModel


class UnitDetailProgress(BaseModel):
    """Progress per unit detail (unit di dalam project)."""

    _model_name = 'project.unit_detail_progress'
    _display_name = 'name'

    _fields = {
        'unit_detail_id': Many2OneField(
            label='Unit Detail',
            relation='project.project_unit_detail',
            required=True,
        ),
        'name': CharField(
            label='Tahap',
            required=True,
            help_text='Misal: Termin 1, Termin 2, Finishing',
        ),
        'progress': SelectionField(
            label='Progress',
            options=[
                ('perencanaan', 'Perencanaan'),
                ('dalam_proses', 'Dalam Proses'),
                ('selesai', 'Selesai'),
            ],
            colors={
                'perencanaan': 'blue',
                'dalam_proses': 'orange',
                'selesai': 'green',
            },
            default='perencanaan',
        ),
        'date': DateField(
            label='Target Selesai',
        ),
        'date_done': DateField(
            label='Tanggal Selesai',
        ),
        'selisih': CharField(
            label='Selisih',
            compute='_compute_selisih',
            depends=['date', 'date_done'],
        ),
        'budget': MonetaryField(
            label='Budget',
            currency='IDR',
        ),
        'realisasi_budget': MonetaryField(
            label='Realisasi Budget',
            currency='IDR',
        ),
        'selisih_budget': CharField(
            label='Selisih Budget',
            compute='_compute_selisih_budget',
            depends=['budget', 'realisasi_budget'],
        ),
        'mandor': CharField(
            label='Mandor/Pemborong',
        ),
        'catatan': TextField(
            label='Catatan',
        ),
    }

    _list_view = {
        'columns': ['name', 'progress', 'date', 'date_done', 'selisih', 'budget', 'realisasi_budget', 'selisih_budget', 'mandor', 'catatan'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'progress', 'date', 'date_done', 'selisih', 'budget', 'realisasi_budget', 'selisih_budget', 'mandor', 'catatan'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Progress Unit'
        verbose_name_plural = 'Progress Unit'

    def __str__(self):
        return self.name or ''

    @staticmethod
    def _parse_date(value):
        if value is None or value == '':
            return None
        if hasattr(value, 'strftime'):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _format_idr(value):
        return f'{abs(value):,.0f}'.replace(',', '.')

    def _compute_selisih(self):
        """Selisih = komparasi Tanggal Selesai vs Target Selesai.

        - selesai sebelum target → 'lebih awal N hari'
        - selesai setelah target  → 'telat N hari'
        - sama                    → 'tepat waktu'
        """
        target = self._parse_date(self.date)
        done = self._parse_date(self.date_done)
        if not target or not done:
            self.selisih = ''
            return
        delta = (done - target).days
        if delta == 0:
            self.selisih = 'tepat waktu'
        elif delta < 0:
            self.selisih = f'lebih awal {abs(delta)} hari'
        else:
            self.selisih = f'telat {delta} hari'

    def _compute_selisih_budget(self):
        """Selisih Budget = komparasi Realisasi vs Budget.

        - realisasi > budget → 'lebih dari budget N'
        - realisasi < budget → 'budget sisa N'
        - sama               → 'sesuai budget'
        """
        budget = float(self.budget or 0)
        realisasi = float(self.realisasi_budget or 0)
        if not budget and not realisasi:
            self.selisih_budget = ''
            return
        diff = realisasi - budget
        if diff == 0:
            self.selisih_budget = 'sesuai budget'
        elif diff > 0:
            self.selisih_budget = f'lebih dari budget {self._format_idr(diff)}'
        else:
            self.selisih_budget = f'budget sisa {self._format_idr(diff)}'
