"""Main dashboard config — gabungan SEMUA modul (meta-driven).

Engine + renderer 100% generic (core/dashboard_api.py + components/dashboard/*);
file ini hanya konfigurasi declarative yang menyebut model dari semua modul.
"""
from core.dashboard_api import register_dashboard

MAIN_DASHBOARD = {
    'key': 'main',
    'title': 'Main Dashboard',
    'blocks': [
        # ── KPI row (gabungan semua modul) ──
        {
            'key': 'total_po',
            'title': 'Total PO (Active)',
            'type': 'kpi', 'span': 4,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'total_so',
            'title': 'Total SO (Active)',
            'type': 'kpi', 'span': 4,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'filters': {'status__in': ['confirmed', 'done']},
            'date_field': 'order_date',
        },
        {
            'key': 'total_products',
            'title': 'Total Products',
            'type': 'kpi', 'span': 4,
            'model': 'inventory.product',
            'aggregate': {'field': 'id', 'func': 'count'},
        },
        {
            'key': 'total_projects',
            'title': 'Total Projects',
            'type': 'kpi', 'span': 4,
            'model': 'project.project',
            'aggregate': {'field': 'id', 'func': 'count'},
        },
        {
            'key': 'bill_unpaid',
            'title': 'Bill Unpaid',
            'type': 'kpi', 'span': 4,
            'model': 'accounting.vendor_bill',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'bill_date',
        },
        {
            'key': 'invoice_unpaid',
            'title': 'Invoice Unpaid',
            'type': 'kpi', 'span': 4,
            'model': 'accounting.customer_invoice',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'status': 'confirmed'},
            'date_field': 'invoice_date',
        },
        # ── Pie row ──
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
            'key': 'so_by_status',
            'title': 'SO by Status',
            'type': 'pie', 'span': 8,
            'model': 'sales.order',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'status',
            'date_field': 'order_date',
        },
        {
            'key': 'products_by_category',
            'title': 'Products by Category',
            'type': 'pie', 'span': 8,
            'model': 'inventory.product',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'category',
        },
        # ── Bar row ──
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
        {
            'key': 'projects_by_category',
            'title': 'Projects by Category',
            'type': 'bar', 'span': 8,
            'model': 'project.project',
            'aggregate': {'field': 'contract_value', 'func': 'sum'},
            'group_by': 'category',
        },
        # ── Trend row ──
        {
            'key': 'purchase_trend',
            'title': 'Purchase Trend (Monthly)',
            'type': 'line', 'span': 12,
            'model': 'purchase.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'date_field': 'order_date',
            'filters': {'status__in': ['confirmed', 'done']},
        },
        {
            'key': 'sales_trend',
            'title': 'Sales Trend (Monthly)',
            'type': 'line', 'span': 12,
            'model': 'sales.order',
            'aggregate': {'field': 'grand_total', 'func': 'sum'},
            'date_field': 'order_date',
            'filters': {'status__in': ['confirmed', 'done']},
        },
        # ── Grid row ──
        {
            'key': 'recent_po',
            'title': 'Recent Purchase Orders',
            'type': 'grid', 'span': 12,
            'model': 'purchase.order',
            'columns': ['reference', 'vendor', 'order_date', 'status', 'grand_total'],
            'order_by': ['-updated_at'],
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

register_dashboard('main', MAIN_DASHBOARD)
