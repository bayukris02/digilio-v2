"""Stock report endpoints — tipis, semua logika agregasi di core.stock_engine.

Endpoint:
    GET /api/stock/balance/?date=YYYY-MM-DD&warehouses=1,2&product=<id>
    → { key, title, date, rows, totals }  (lihat StockEngine.stock_balance)

    GET /api/stock/card/?product=<id>&warehouses=1,2&date_from=...&date_to=...
    → { key, title, filters, rows }  (lihat StockEngine.stock_card)

Catatan: `warehouses` multi-value, kosong/absent = semua gudang.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.stock_engine import StockEngine


def _opt_int(raw):
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _warehouse_ids(raw):
    """Parse '1,2,3' → list[int]; absent/kosong → [] (semua gudang)."""
    if not raw:
        return []
    out = []
    for part in str(raw).split(','):
        try:
            out.append(int(part.strip()))
        except (TypeError, ValueError):
            continue
    return out


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_balance(request):
    """Laporan Stock Balance — saldo stok per produk pada satu tanggal."""
    payload = StockEngine.stock_balance(
        date=request.query_params.get('date') or None,
        warehouse_ids=_warehouse_ids(request.query_params.get('warehouses')),
        product_id=_opt_int(request.query_params.get('product')),
    )
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_card(request):
    """Laporan Kartu Stok — detail pergerakan + saldo berjalan per produk/lokasi."""
    payload = StockEngine.stock_card(
        product_id=_opt_int(request.query_params.get('product')),
        warehouse_ids=_warehouse_ids(request.query_params.get('warehouses')),
        date_from=request.query_params.get('date_from') or None,
        date_to=request.query_params.get('date_to') or None,
    )
    return Response(payload)


def _labels(raw):
    """Parse 'a,b' → list[str] (buang kosong)."""
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(',') if p.strip()]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_ledger(request):
    """Laporan Stock Ledger — daftar mentah pergerakan stok + total masuk/keluar."""
    payload = StockEngine.stock_ledger(
        product_id=_opt_int(request.query_params.get('product')),
        warehouse_ids=_warehouse_ids(request.query_params.get('warehouses')),
        date_from=request.query_params.get('date_from') or None,
        date_to=request.query_params.get('date_to') or None,
        source_models=_labels(request.query_params.get('sources')),
    )
    return Response(payload)
