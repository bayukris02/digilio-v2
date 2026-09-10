"""Tax report endpoint — tipis, logika agregasi di core.tax_report_engine.

Endpoint:
    GET /api/tax/report/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
                        &modules=sales.order,accounting.vendor_bill
                        &taxes=1,2&include_draft=1
    → { key, title, period, modules, rows, totals }
      (lihat TaxReportEngine.tax_report)

Catatan: `modules`/`taxes` multi-value (dipisah koma); kosong = semua.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.tax_report_engine import TaxReportEngine


def _csv(raw):
    if not raw:
        return None
    return [p.strip() for p in str(raw).split(',') if p.strip()]


def _int_list(raw):
    if not raw:
        return None
    out = []
    for part in str(raw).split(','):
        try:
            out.append(int(part.strip()))
        except (TypeError, ValueError):
            continue
    return out or None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tax_report(request):
    """Report Pajak — rekap pajak per tag dari baris dokumen lintas modul."""
    include_draft = str(request.query_params.get('include_draft', '1')).lower() not in ('0', 'false', 'no')
    payload = TaxReportEngine.tax_report(
        date_from=request.query_params.get('date_from') or None,
        date_to=request.query_params.get('date_to') or None,
        module_keys=_csv(request.query_params.get('modules')),
        tax_ids=_int_list(request.query_params.get('taxes')),
        include_draft=include_draft,
    )
    return Response(payload)
