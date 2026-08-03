"""Purchase dashboard config — meta-driven blocks.

Satu-satunya file yang menyebut nama model (wilayah file modul, BUKAN core).
Block engine + renderer frontend semuanya generic (core/dashboard_api.py +
components/dashboard/*) — modul lain cukup menulis config serupa.
"""
from core.dashboard_api import register_dashboard

PURCHASE_DASHBOARD = {
    'key': 'purchase',
    'title': 'Purchase Dashboard',
    'blocks': [
        # ── KPI row ──
        {
            'key': 'po_total',
            'title': 'Total PO (Active)',
            'type': 'kpi', 'span': 6,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'po_open',
            'title': 'Open PO',
            'type': 'kpi', 'span': 6,
            'model': 'purchase.order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'order_date',
        },
        {
            'key': 'gr_waiting',
            'title': 'GR Waiting',
            'type': 'kpi', 'span': 6,
            'model': 'purchase.goods_receipt',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'waiting'},
            'date_field': 'receipt_date',
        },
        {
            'key': 'bill_unpaid',
            'title': 'Bill Unpaid',
            'type': 'kpi', 'span': 6,
            'model': 'accounting.vendor_bill',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'bill_date',
        },
        # ── Charts row ──
        {
            'key': 'po_by_status',
            'title': 'PO by Status',
            'type': 'pie', 'span': 8,
            'model': 'purchase.order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'status',
            'date_field': 'order_date',
        },
        {
            'key': 'po_by_category',
            'title': 'PO by Category (Value)',
            'type': 'bar', 'span': 8,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'category',
            'limit': 6, 'sort': '-value',
            'date_field': 'order_date',
        },
        {
            'key': 'top_vendors',
            'title': 'Top Vendors by Spend',
            'type': 'bar', 'span': 8,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'vendor',
            'limit': 5, 'sort': '-value',
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        # ── Funnel + Aging ──
        {
            'key': 'purchase_funnel',
            'title': 'Purchase Funnel',
            'type': 'funnel', 'span': 8,
            'model': 'purchase.order',
            'items': [
                {'label': 'PO Confirmed', 'model': 'purchase.order',
                 'filters': {'status__in': ['confirmed', 'done']},
                 'date_field': 'order_date'},
                {'label': 'GR Done', 'model': 'purchase.goods_receipt',
                 'filters': {'status': 'done'},
                 'date_field': 'receipt_date'},
                {'label': 'Bill Confirmed', 'model': 'accounting.vendor_bill',
                 'filters': {'status': 'confirmed'},
                 'date_field': 'bill_date'},
            ],
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
        {
            'key': 'po_trend',
            'title': 'Purchase Trend (Monthly)',
            'type': 'line', 'span': 8,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'date_field': 'order_date',
            'filters': {'status__in': ['confirmed', 'done']},
        },
        # ── Summary + Grid (AG Grid, full pagination) ──
        {
            'key': 'vendor_summary',
            'title': 'Per-Vendor Summary',
            'type': 'summary', 'span': 12,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'group_by': 'vendor',
            'sort': '-value',
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'recent_po',
            'title': 'Recent Purchase Orders',
            'type': 'grid', 'span': 12,
            'model': 'purchase.order',
            'columns': ['reference', 'vendor', 'order_date', 'status', 'grand_total'],
            'order_by': ['-updated_at'],
            'date_field': 'order_date',
        },
    ],
}

register_dashboard('purchase', PURCHASE_DASHBOARD)
