"""Accounting dashboard config — meta-driven blocks (versi sederhana).

Engine + renderer 100% generic (core/dashboard_api.py + components/dashboard/*);
file ini hanya konfigurasi declarative yang menyebut model accounting.
"""
from core.dashboard_api import register_dashboard

ACCOUNTING_DASHBOARD = {
    'key': 'accounting',
    'title': 'Accounting Dashboard',
    'blocks': [
        # ── KPI row ──
        {
            'key': 'total_debit',
            'title': 'Total Debit (Jurnal)',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.jurnal',
            'aggregate': {'field': 'total_debit', 'func': 'sum'},
            'date_field': 'date',
        },
        {
            'key': 'total_credit',
            'title': 'Total Credit (Jurnal)',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.jurnal',
            'aggregate': {'field': 'total_credit', 'func': 'sum'},
            'date_field': 'date',
        },
        {
            'key': 'bills_unpaid',
            'title': 'Bill Unpaid',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.vendor_bill',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'bill_date',
        },
        {
            'key': 'invoices_unpaid',
            'title': 'Invoice Unpaid',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.customer_invoice',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'invoice_date',
        },
        # ── Charts ──
        {
            'key': 'jurnal_by_type',
            'title': 'Jurnal by Type',
            'type': 'pie', 'span': 8,
            'model': 'accounting.jurnal',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'journal_type',
            'date_field': 'date',
        },
        {
            'key': 'jurnal_trend',
            'title': 'Jurnal Debit Trend (Monthly)',
            'type': 'line', 'span': 8,
            'model': 'accounting.jurnal',
            'aggregate': {'field': 'total_debit', 'func': 'sum'},
            'date_field': 'date',
        },
        {
            'key': 'bill_aging',
            'title': 'Bill Aging (by Due Date)',
            'type': 'aging', 'span': 8,
            'model': 'accounting.vendor_bill',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'due_date',
            'buckets': [
                {'key': 'overdue', 'label': 'Overdue', 'max_days': 0},
                {'key': 'd30', 'label': '0-30', 'min_days': 0, 'max_days': 31},
                {'key': 'd60', 'label': '31-60', 'min_days': 31, 'max_days': 61},
                {'key': 'd90', 'label': '61-90', 'min_days': 61, 'max_days': 91},
                {'key': 'd90p', 'label': '90+', 'min_days': 91},
            ],
        },
        # ── Grid ──
        {
            'key': 'recent_jurnals',
            'title': 'Recent Jurnals',
            'type': 'grid', 'span': 24,
            'model': 'accounting.jurnal',
            'columns': ['reference', 'date', 'journal_type', 'total_debit', 'total_credit', 'status'],
            'order_by': ['-date'],
            'date_field': 'date',
        },
    ],
}

register_dashboard('accounting', ACCOUNTING_DASHBOARD)
