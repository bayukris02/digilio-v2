"""Stock report endpoints — tipis, semua logika agregasi di core.stock_engine.

Endpoint:
    GET /api/stock/balance/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&location=<id>
    → { key, title, period, rows, totals }  (lihat StockEngine.stock_balance)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.stock_engine import StockEngine


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_balance(request):
    """Laporan Stock Balance dari row stock ledger (agregasi di StockEngine)."""
    date_from = request.query_params.get('date_from') or None
    date_to = request.query_params.get('date_to') or None
    location_raw = request.query_params.get('location') or None
    location_id = None
    if location_raw:
        try:
            location_id = int(location_raw)
        except (TypeError, ValueError):
            location_id = None
    payload = StockEngine.stock_balance(
        date_from=date_from, date_to=date_to, location_id=location_id)
    return Response(payload)
