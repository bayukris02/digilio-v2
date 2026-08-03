"""Inventory dashboard config — meta-driven blocks (versi sederhana).

Engine + renderer 100% generic (core/dashboard_api.py + components/dashboard/*);
file ini hanya konfigurasi declarative yang menyebut model inventory.
"""
from core.dashboard_api import register_dashboard

INVENTORY_DASHBOARD = {
    'key': 'inventory',
    'title': 'Inventory Dashboard',
    'blocks': [
        # ── KPI row ──
        {
            'key': 'total_products',
            'title': 'Total Products',
            'type': 'kpi', 'span': 6,
            'model': 'inventory.product',
            'aggregate': {'field': 'id', 'func': 'count'},
        },
        {
            'key': 'active_products',
            'title': 'Active Products',
            'type': 'kpi', 'span': 6,
            'model': 'inventory.product',
            'aggregate': {'field': 'id', 'func': 'count'},
            'filters': {'is_active': True},
        },
        {
            'key': 'stock_value',
            'title': 'Stock Value (Sales Price)',
            'type': 'kpi', 'span': 6,
            'model': 'inventory.product',
            'aggregate': {'field': 'price', 'func': 'sum'},
        },
        {
            'key': 'total_cost',
            'title': 'Total Cost',
            'type': 'kpi', 'span': 6,
            'model': 'inventory.product',
            'aggregate': {'field': 'cost', 'func': 'sum'},
        },
        # ── Charts ──
        {
            'key': 'products_by_category',
            'title': 'Products by Category',
            'type': 'pie', 'span': 12,
            'model': 'inventory.product',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'category',
        },
        {
            'key': 'top_products',
            'title': 'Top Products by Price',
            'type': 'bar', 'span': 12,
            'model': 'inventory.product',
            'aggregate': {'field': 'price', 'func': 'sum'},
            'group_by': 'name',
            'limit': 5, 'sort': '-value',
        },
        # ── Grid ──
        {
            'key': 'recent_products',
            'title': 'Products',
            'type': 'grid', 'span': 24,
            'model': 'inventory.product',
            'columns': ['code', 'name', 'category', 'price', 'cost', 'is_active'],
            'order_by': ['-updated_at'],
        },
    ],
}

register_dashboard('inventory', INVENTORY_DASHBOARD)
