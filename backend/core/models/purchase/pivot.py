"""Config pivot pembelian — agregasi PO + PO line (AG Grid pivot mode).

Row group: Vendor → Produk. Pivot column: Bulan (dari Tanggal Pesanan).
Values: Qty & Total (sum). Semua status PO ikut (draft/confirmed/paid).
"""
from core.pivot_api import register_pivot

register_pivot('purchase', {
    'key': 'purchase',
    'title': 'Pivot Pembelian',
    'line_model': 'purchase.order.line',
    'header_model': 'purchase.order',
    'parent_field': 'order_id',
    'date_field': 'order_date',
    'row_groups': [
        {'field': 'vendor_name', 'attr': 'vendor', 'source': 'header', 'label': 'Vendor'},
        {'field': 'product_name', 'attr': 'product', 'source': 'line', 'label': 'Produk'},
    ],
    'pivot_cols': [
        {'field': 'order_month', 'source': 'month', 'label': 'Bulan'},
    ],
    'values': [
        {'field': 'qty', 'source': 'line', 'label': 'Qty', 'agg': 'sum'},
        {'field': 'total', 'source': 'line', 'label': 'Total', 'agg': 'sum'},
    ],
})
