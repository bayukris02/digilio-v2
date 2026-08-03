"""Sales dashboard config — meta-driven blocks (replikasi dari purchase).

Engine + renderer 100% generic (core/dashboard_api.py + components/dashboard/*);
file ini hanya konfigurasi declarative yang menyebut model sales.
"""
from core.dashboard_api import register_dashboard

SALES_DASHBOARD = {
    'key': 'sales',
    'title': 'Sales Dashboard',
    'blocks': [
        # ── KPI row ──
        {
            'key': 'so_total',
            'title': 'Total SO (Active)',
            'type': 'kpi', 'span': 6,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'so_open',
            'title': 'Open SO',
            'type': 'kpi', 'span': 6,
            'model': 'sales.order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'order_date',
        },
        {
            'key': 'do_waiting',
            'title': 'DO Waiting',
            'type': 'kpi', 'span': 6,
            'model': 'sales.delivery_order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'waiting'},
            'date_field': 'delivery_date',
        },
        {
            'key': 'invoice_unpaid',
            'title': 'Invoice Unpaid',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.customer_invoice',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'invoice_date',
        },
        # ── Charts row ──
        {
            'key': 'so_by_status',
            'title': 'SO by Status',
            'type': 'pie', 'span': 8,
            'model': 'sales.order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'status',
            'date_field': 'order_date',
        },
        {
            'key': 'top_sales',
            'title': 'Top Sales by Value',
            'type': 'bar', 'span': 8,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'sales',
            'limit': 5, 'sort': '-value',
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'top_customers',
            'title': 'Top Customers by Spend',
            'type': 'bar', 'span': 8,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'customer',
            'limit': 5, 'sort': '-value',
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        # ── Funnel + Aging ──
        {
            'key': 'sales_funnel',
            'title': 'Sales Funnel',
            'type': 'funnel', 'span': 8,
            'model': 'sales.order',
            'items': [
                {'label': 'SO Confirmed', 'model': 'sales.order',
                 'filters': {'status__in': ['confirmed', 'done']},
                 'date_field': 'order_date'},
                {'label': 'DO Done', 'model': 'sales.delivery_order',
                 'filters': {'status': 'done'},
                 'date_field': 'delivery_date'},
                {'label': 'Invoice Confirmed', 'model': 'accounting.customer_invoice',
                 'filters': {'status__in': ['confirmed', 'done']},
                 'date_field': 'invoice_date'},
            ],
        },
        {
            'key': 'invoice_aging',
            'title': 'Invoice Aging (by Due Date)',
            'type': 'aging', 'span': 8,
            'model': 'accounting.customer_invoice',
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
        {
            'key': 'so_trend',
            'title': 'Sales Trend (Monthly)',
            'type': 'line', 'span': 8,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'date_field': 'order_date',
            'filters': {'status__in': ['confirmed', 'done']},
        },
        # ── Summary + Grid (AG Grid, full pagination) ──
        {
            'key': 'customer_summary',
            'title': 'Per-Customer Summary',
            'type': 'summary', 'span': 12,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'customer',
            'sort': '-value',
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'recent_so',
            'title': 'Recent Sales Orders',
            'type': 'grid', 'span': 12,
            'model': 'sales.order',
            'columns': ['reference', 'customer', 'order_date', 'status', 'grand_total'],
            'order_by': ['-updated_at'],
            'date_field': 'order_date',
        },
    ],
}

register_dashboard('sales', SALES_DASHBOARD)
