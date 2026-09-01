from datetime import date, timedelta

from core.fields import (
    CharField, DateField, IntegerField, Many2OneField, MonetaryField, One2ManyField,
)
from core.model_meta import BaseModel


class Asset(BaseModel):
    """Registrasi Aset Tetap — nilai perolehan, masa penyusutan, dan jadwal depresiasi linear bulanan."""

    _model_name = 'accounting.asset'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Aset',
            required=True,
            help_text='Misal: Excavator, Komputer, Kendaraan Operasional',
        ),
        'code': CharField(
            label='Kode Aset',
            help_text='Kode internal aset, misal: AST-001',
        ),
        'location': CharField(
            label='Lokasi Aset',
        ),
        'acquisition_date': DateField(
            label='Tanggal Perolehan',
        ),
        'acquisition_cost': MonetaryField(
            label='Nilai Perolehan',
            currency='IDR',
        ),
        'useful_life_months': IntegerField(
            label='Masa Penyusutan (Bulan)',
            help_text='Jumlah bulan penyusutan linear',
        ),
        'first_depreciation_date': DateField(
            label='Tanggal Pertama Depresiasi',
            help_text='Bulan pertama depresiasi dimulai',
        ),
        'accumulated_depreciation_account': Many2OneField(
            label='Akun Akumulasi Penyusutan',
            relation='accounting.chart_of_account',
            help_text='Akun COA untuk akumulasi penyusutan (neraca)',
        ),
        'depreciation_expense_account': Many2OneField(
            label='Akun Beban Penyusutan',
            relation='accounting.chart_of_account',
            help_text='Akun COA untuk beban penyusutan (laba rugi)',
        ),
        'depreciation_lines': One2ManyField(
            label='Depresiasi',
            relation='accounting.asset_depreciation_line',
            inverse_field='asset_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'code', 'location', 'acquisition_date', 'acquisition_cost', 'useful_life_months'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'code', 'location', 'acquisition_date', 'acquisition_cost', 'useful_life_months', 'first_depreciation_date'],
                },
                {
                    'key': 'accounting',
                    'label': 'Akunting Setup',
                    'fields': ['accumulated_depreciation_account', 'depreciation_expense_account'],
                },
            ],
            'actions': [
                {
                    'label': 'Hitung Depresiasi',
                    'icon': 'CalculatorOutlined',
                    'color': 'primary',
                    'action': 'hitung_depresiasi',
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'depreciation_lines',
                'label': 'Depresiasi',
                'relation': 'depreciation_lines',
                'columns': ['date', 'asset_value', 'depreciation', 'residual_value'],
                'read_only': True,
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Aset'
        verbose_name_plural = 'Aset'

    def __str__(self):
        return self.name or ''

    @staticmethod
    def _add_months(d, n):
        """Tambahkan n bulan ke date d (tanggal disesuaikan ke akhir bulan bila perlu)."""
        month_idx = d.month - 1 + n
        year = d.year + month_idx // 12
        month = month_idx % 12 + 1
        last_day = (date(year, month % 12 + 1, 1) - timedelta(days=1)).day
        return date(year, month, min(d.day, last_day))

    def _action_hitung_depresiasi(self, data=None):
        """Generate jadwal depresiasi linear bulanan.

        N baris = Masa Penyusutan (bulan), mulai dari Tanggal Pertama Depresiasi.
        - nilai_asset  = nilai buku awal periode (Nilai Perolehan - akumulasi s.d. bulan lalu)
        - depresiasi   = Nilai Perolehan / Masa (baris terakhir menyesuaikan agar sisa = 0)
        - sisa_nilai   = nilai_asset - depresiasi
        Baris lama dihapus (soft delete) lalu digenerate ulang.
        """
        from core.models.accounting.asset_depreciation_line import AssetDepreciationLine

        cost = float(self.acquisition_cost or 0)
        months = int(self.useful_life_months or 0)
        start = self.first_depreciation_date

        if cost <= 0:
            return {'error': 'Nilai Perolehan harus lebih dari 0.'}
        if months <= 0:
            return {'error': 'Masa Penyusutan harus lebih dari 0.'}
        if not start:
            return {'error': 'Tanggal Pertama Depresiasi wajib diisi.'}
        if isinstance(start, str):
            start = date.fromisoformat(str(start)[:10])

        monthly = round(cost / months, 2)

        # Hapus baris lama (soft delete) — lalu generate ulang
        AssetDepreciationLine.objects.filter(
            asset_id=self, is_deleted=False
        ).update(is_deleted=True)

        created = 0
        d = start
        for i in range(1, months + 1):
            nilai = round(cost - monthly * (i - 1), 2)
            dep = round(nilai, 2) if i == months else monthly
            sisa = round(nilai - dep, 2)
            AssetDepreciationLine.objects.create(
                asset_id=self,
                date=d,
                asset_value=nilai,
                depreciation=dep,
                residual_value=sisa,
            )
            created += 1
            d = self._add_months(d, 1)

        return {
            '_action_type': 'refresh',
            'message': f'Depresiasi dihitung: {created} baris.',
        }
