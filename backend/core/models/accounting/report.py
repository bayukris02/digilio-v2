"""Report finansial config — meta-driven (Laba Rugi, Neraca, dst).

File ini SATU-SATUNYA yang menyebut nama model / tipe akun; engine
core/report_api.py 100% generic dan membaca semuanya dari config ini.
"""
from core.report_api import register_report

PROFIT_LOSS_REPORT = {
    'key': 'profit_loss',
    'title': 'Laporan Laba Rugi',
    # ── Sumber data ──
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    # ── Mapping akun ──
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    # Saldo normal per tipe akun (standar akuntansi)
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'leaves_only': True,  # akun header (punya child) tidak ditampilkan
    # ── Struktur ──
    'sections': [
        {
            'key': 'revenue',
            'title': 'Pendapatan',
            'account_types': ['revenue'],
        },
        {
            'key': 'expense',
            'title': 'Beban',
            'account_types': ['expense'],
        },
    ],
    'totals': [
        {'key': 'net_income', 'label': 'LABA BERSIH', 'formula': 'revenue - expense'},
    ],
}

register_report('profit_loss', PROFIT_LOSS_REPORT)
