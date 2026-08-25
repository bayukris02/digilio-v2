"""Generic meta-driven pivot engine (AG Grid enterprise pivot mode).

Pivot = denormalisasi baris line + header model → rowData flat, plus column
defs (rowGroup / pivot / aggFunc) untuk AG Grid pivot. Engine 100% generic —
semua sumber data (line_model, header_model, parent_field, fields) dibaca
dari config per modul (lihat core/models/purchase/pivot.py).

Endpoint:
    GET /api/pivots/{key}/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    → { key, title, columns: [{field,label,rowGroup?,pivot?,aggFunc?}], rowData: [...] }
"""
from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.model_meta import ErpModelBase

PIVOT_REGISTRY = {}


def register_pivot(key, config):
    """Register config pivot di bawah key unik (mis. 'purchase')."""
    PIVOT_REGISTRY[key] = config


def _get_model(model_name):
    return ErpModelBase._model_registry.get(model_name)


def _month_key(value):
    """Tanggal → 'YYYY-MM' (bulan utk pivot column)."""
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').strftime('%Y-%m')
        except ValueError:
            return value[:7]
    return value.strftime('%Y-%m')


def _flat_name(value):
    """Nilai many2one (objek) → nama tampilan; selain itu dibiarkan."""
    if value is None:
        return ''
    if hasattr(value, 'pk'):
        return str(value)
    return value


def _num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _build_pivot(config, date_from, date_to):
    line_model = _get_model(config['line_model'])
    header_model = _get_model(config['header_model'])
    if not line_model or not header_model:
        return None, 'Pivot config model not found'

    parent_field = config['parent_field']
    date_field = config['date_field']

    # 1. Header ids — filter rentang tanggal via date_field header
    hqs = header_model.objects.filter(is_deleted=False)
    for f, v in (config.get('header_filters') or {}).items():
        hqs = hqs.filter(**{f: v})
    if date_from:
        hqs = hqs.filter(**{f'{date_field}__gte': date_from})
    if date_to:
        hqs = hqs.filter(**{f'{date_field}__lte': date_to})
    header_ids = list(hqs.values_list('id', flat=True))
    if not header_ids:
        return {'key': config['key'], 'title': config.get('title', config['key']),
                'columns': [], 'rowData': []}, None

    # 2. Line records milik header tsb
    lqs = line_model.objects.filter(is_deleted=False, **{f'{parent_field}_id__in': header_ids})
    for f, v in (config.get('filters') or {}).items():
        lqs = lqs.filter(**{f: v})
    lines = list(lqs.select_related(parent_field))

    row_groups = config.get('row_groups', [])
    pivot_cols = config.get('pivot_cols', [])
    values = config.get('values', [])

    def resolve(obj, field, source, attr=None):
        key = attr or field
        if source == 'line':
            return getattr(obj, key, None)
        if source == 'header':
            header = getattr(obj, parent_field, None)
            return getattr(header, key, None) if header else None
        if source == 'month':  # derive bulan dari date_field header
            header = getattr(obj, parent_field, None)
            return _month_key(getattr(header, date_field, None)) if header else ''
        return None

    # 3. Denormalisasi per baris line
    rows = []
    for line in lines:
        row = {'id': line.pk}
        for g in row_groups:
            row[g['field']] = _flat_name(resolve(line, g['field'], g.get('source', 'line'), g.get('attr')))
        for c in pivot_cols:
            row[c['field']] = resolve(line, c['field'], c.get('source', 'line'), c.get('attr'))
        for v in values:
            row[v['field']] = _num(resolve(line, v['field'], v.get('source', 'line'), v.get('attr')))
        rows.append(row)

    # 4. Column defs utk AG Grid pivot
    columns = []
    for g in row_groups:
        columns.append({'field': g['field'], 'label': g.get('label', g['field']),
                        'enableRowGroup': True, 'rowGroup': True})
    for c in pivot_cols:
        columns.append({'field': c['field'], 'label': c.get('label', c['field']),
                        'enablePivot': True, 'pivot': True})
    for v in values:
        columns.append({'field': v['field'], 'label': v.get('label', v['field']),
                        'enableValue': True, 'aggFunc': v.get('agg', 'sum')})

    return {'key': config['key'], 'title': config.get('title', config['key']),
            'columns': columns, 'rowData': rows}, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pivot_data(request, key):
    """GET /api/pivots/{key}/?date_from=&date_to= → data pivot."""
    config = PIVOT_REGISTRY.get(key)
    if not config:
        return Response({'error': f'Pivot "{key}" not found'}, status=404)

    date_from = request.query_params.get('date_from') or None
    date_to = request.query_params.get('date_to') or None

    payload, error = _build_pivot(config, date_from, date_to)
    if error:
        return Response({'error': error}, status=400)
    return Response(payload)
