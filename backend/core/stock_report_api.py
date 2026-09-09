"""Stock report endpoints — tipis, semua logika agregasi di core.stock_engine.

Endpoint:
    GET /api/stock/balance/?date=YYYY-MM-DD&location=<id>
    → { key, title, date, rows, totals }  (lihat StockEngine.stock_balance)

    GET /api/stock/card/?product=<id>&location=<id>&date_from=...&date_to=...
    → { key, title, filters, rows }  (lihat StockEngine.stock_card)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.stock_engine import StockEngine


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_balance(request):
    """Laporan Stock Balance — saldo stok per produk pada satu tanggal."""
    date_raw = request.query_params.get('date') or None
    location_raw = request.query_params.get('location') or None
    location_id = None
    if location_raw:
        try:
            location_id = int(location_raw)
        except (TypeError, ValueError):
            location_id = None
    payload = StockEngine.stock_balance(
        date=date_raw, location_id=location_id)
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_card(request):
    """Laporan Kartu Stok — detail pergerakan + saldo berjalan per produk/lokasi."""
    def _opt_int(raw):
        if not raw:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    payload = StockEngine.stock_card(
        product_id=_opt_int(request.query_params.get('product')),
        location_id=_opt_int(request.query_params.get('location')),
        date_from=request.query_params.get('date_from') or None,
        date_to=request.query_params.get('date_to') or None,
    )
    return Response(payload)
