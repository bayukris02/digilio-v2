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

# ─────────────────────────────────────────────────────────────
# 1. Neraca (Balance Sheet) — posisi s/d tanggal (pilih range, tanpa date_from
#    = seluruh riwayat posted). Aset = Liabilitas + Ekuitas (SELISIH harus 0).
# ─────────────────────────────────────────────────────────────
BALANCE_SHEET_REPORT = {
    'key': 'balance_sheet',
    'title': 'Laporan Neraca',
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'leaves_only': True,
    'sections': [
        {'key': 'aset', 'title': 'ASET', 'account_types': ['asset']},
        {'key': 'liabilitas', 'title': 'LIABILITAS', 'account_types': ['liability']},
        {'key': 'ekuitas', 'title': 'EKUITAS', 'account_types': ['equity']},
    ],
    'totals': [
        {'key': 'total_aset', 'label': 'TOTAL ASET', 'formula': 'aset'},
        {'key': 'total_liab_ekuitas', 'label': 'TOTAL LIABILITAS + EKUITAS', 'formula': 'liabilitas + ekuitas'},
        {'key': 'selisih', 'label': 'SELISIH (HARUS 0)', 'formula': 'aset - liabilitas - ekuitas'},
    ],
}
register_report('balance_sheet', BALANCE_SHEET_REPORT)

# ─────────────────────────────────────────────────────────────
# 2. Neraca Saldo (Trial Balance) — semua akun, kolom Debit | Kredit.
#    TOTAL DEBIT harus sama dengan TOTAL KREDIT.
# ─────────────────────────────────────────────────────────────
TRIAL_BALANCE_REPORT = {
    'key': 'trial_balance',
    'title': 'Neraca Saldo',
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'leaves_only': True,
    'sides': True,
    'sections': [
        {
            'key': 'akun',
            'title': 'SEMUA AKUN',
            'account_types': ['asset', 'liability', 'equity', 'revenue', 'expense'],
        },
    ],
    'sides_totals': [
        {'key': 'total_debit', 'label': 'TOTAL DEBIT', 'side': 'debit'},
        {'key': 'total_kredit', 'label': 'TOTAL KREDIT', 'side': 'credit'},
    ],
    'totals': [
        {'key': 'selisih', 'label': 'SELISIH DEBIT - KREDIT (HARUS 0)', 'formula': 'akun_debit - akun_credit'},
    ],
}
register_report('trial_balance', TRIAL_BALANCE_REPORT)

# ─────────────────────────────────────────────────────────────
# 3. Buku Besar (General Ledger) — ringkasan per akun per tipe,
#    kolom Debit | Kredit | Saldo.
# ─────────────────────────────────────────────────────────────
GENERAL_LEDGER_REPORT = {
    'key': 'general_ledger',
    'title': 'Buku Besar',
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'leaves_only': True,
    'sides': True,
    'balance_col': True,
    'sections': [
        {'key': 'aset', 'title': 'ASET', 'account_types': ['asset']},
        {'key': 'liabilitas', 'title': 'LIABILITAS', 'account_types': ['liability']},
        {'key': 'ekuitas', 'title': 'EKUITAS', 'account_types': ['equity']},
        {'key': 'pendapatan', 'title': 'PENDAPATAN', 'account_types': ['revenue']},
        {'key': 'beban', 'title': 'BEBAN', 'account_types': ['expense']},
    ],
    'sides_totals': [
        {'key': 'total_debit', 'label': 'TOTAL DEBIT', 'side': 'debit'},
        {'key': 'total_kredit', 'label': 'TOTAL KREDIT', 'side': 'credit'},
    ],
}
register_report('general_ledger', GENERAL_LEDGER_REPORT)

# ─────────────────────────────────────────────────────────────
# 4. Cashflow — arus kas masuk/keluar per akun kas & bank.
#    Versi sederhana: tanpa klasifikasi aktivitas; daftar akun kas/bank
#    ditentukan via `account_codes` (sesuaikan dengan COA instalasi).
# ─────────────────────────────────────────────────────────────
CASH_FLOW_REPORT = {
    'key': 'cash_flow',
    'title': 'Laporan Arus Kas',
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'sides': True,
    'sections': [
        {
            'key': 'arus_kas',
            'title': 'ARUS KAS (KAS & BANK)',
            'account_types': ['asset'],
            'account_codes': ['001', '1-1101', '1-1102'],
        },
    ],
    'sides_totals': [
        {'key': 'total_masuk', 'label': 'TOTAL ARUS MASUK (DEBIT)', 'side': 'debit'},
        {'key': 'total_keluar', 'label': 'TOTAL ARUS KELUAR (KREDIT)', 'side': 'credit'},
    ],
    'totals': [
        {'key': 'net', 'label': 'SELISIH ARUS KAS (MASUK - KELUAR)', 'formula': 'arus_kas_debit - arus_kas_credit'},
    ],
}
register_report('cash_flow', CASH_FLOW_REPORT)

# ─────────────────────────────────────────────────────────────
# 5. Perubahan Modal (Equity Changes) — ekuitas + laba rugi berjalan.
# ─────────────────────────────────────────────────────────────
EQUITY_CHANGES_REPORT = {
    'key': 'equity_changes',
    'title': 'Laporan Perubahan Modal',
    'line_model': 'accounting.jurnal_line',
    'account_model': 'accounting.chart_of_account',
    'account_field': 'account',
    'debit_field': 'debit',
    'credit_field': 'credit',
    'status_field': 'jurnal_id__status',
    'date_field': 'jurnal_id__date',
    'status': 'posted',
    'account_code_field': 'code',
    'account_name_field': 'name',
    'account_type_field': 'type',
    'account_parent_field': 'parent',
    'normal_balance': {
        'asset': 'debit',
        'expense': 'debit',
        'liability': 'credit',
        'equity': 'credit',
        'revenue': 'credit',
    },
    'leaves_only': True,
    'sections': [
        {'key': 'ekuitas', 'title': 'EKUITAS', 'account_types': ['equity']},
        {'key': 'pendapatan', 'title': 'PENDAPATAN', 'account_types': ['revenue']},
        {'key': 'beban', 'title': 'BEBAN', 'account_types': ['expense']},
    ],
    'totals': [
        {'key': 'laba_berjalan', 'label': 'LABA (RUGI) BERJALAN', 'formula': 'pendapatan - beban'},
        {'key': 'total_ekuitas_akhir', 'label': 'TOTAL EKUITAS AKHIR', 'formula': 'ekuitas + pendapatan - beban'},
    ],
}
register_report('equity_changes', EQUITY_CHANGES_REPORT)
