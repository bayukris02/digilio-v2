"""Generic meta-driven dashboard engine.

Dashboard = collection of declarative blocks. Each block describes its data
source (model, aggregate, group_by, date_field, filters) and rendering type
(kpi, pie, bar, line, funnel, aging, grid, summary). This file must stay 100%
generic — no model names, no per-module branches.

Module configs register via register_dashboard(key, config) — see
core/models/purchase/dashboard.py for the purchase example.

Endpoint:
  GET /api/dashboards/{key}/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&page_size_{key}=N
  → { key, title, blocks: [{...config, data}], fields: {model: field_configs} }

Grid/summary blocks support client-side AG Grid pagination: pass page_size_{key}=0
to return ALL rows (dashboard payload is fetched once, AG Grid paginates locally —
same pattern as ModelListPage).
"""
from datetime import date, timedelta

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.model_meta import ErpModelBase

DASHBOARD_REGISTRY = {}


def register_dashboard(key, config):
    """Register a dashboard config under a unique key (e.g. 'purchase')."""
    DASHBOARD_REGISTRY[key] = config


# ─── Generic block engine ─────────────────────────────────────────────

def _get_model(model_name):
    return ErpModelBase._model_registry.get(model_name)


def _agg_expr(agg):
    """Build Django aggregate expression from block.aggregate config."""
    agg = agg or {}
    field = agg.get('field', 'id')
    func = agg.get('func', 'count')
    if func == 'sum':
        return {'value': Sum(field)}
    if func == 'avg':
        return {'value': Avg(field)}
    return {'value': Count('id')}


def _apply_date_filter(qs, block, date_from, date_to):
    """Global date range filter — hanya block yang punya date_field."""
    df = block.get('date_field')
    if not df:
        return qs
    if date_from:
        qs = qs.filter(**{f'{df}__gte': date_from})
    if date_to:
        qs = qs.filter(**{f'{df}__lte': date_to})
    return qs


def _group_key(model_cls, group_by):
    """ORM lookup untuk group_by — many2one pakai <field>__name."""
    fd = model_cls._field_descriptors.get(group_by)
    if fd and getattr(fd, 'field_type', None) == 'many2one':
        return f'{group_by}__name'
    return group_by


def _serialize(obj, columns):
    """Lightweight serialization — hanya kolom yang diminta block."""
    data = {'id': obj.pk}
    for fname in columns:
        val = getattr(obj, fname, None)
        fd = obj._field_descriptors.get(fname)
        if fd and hasattr(fd, 'to_representation'):
            val = fd.to_representation(val)
        data[fname] = val
    return data


def _run_block(block, date_from=None, date_to=None, page=1, page_size=10):
    model_cls = _get_model(block['model'])
    if not model_cls:
        return {'error': f"Model {block['model']} not found"}

    qs = model_cls.objects.filter(is_deleted=False)
    for f, v in (block.get('filters') or {}).items():
        qs = qs.filter(**{f: v})
    qs = _apply_date_filter(qs, block, date_from, date_to)

    if block.get('order_by'):
        qs = qs.order_by(*block['order_by'])

    agg = block.get('aggregate') or {'field': 'id', 'func': 'count'}
    btype = block.get('type')

    # ── KPI: scalar + monthly series (sparkline) ──
    if btype == 'kpi':
        value = qs.aggregate(**_agg_expr(agg))['value'] or 0
        series = []
        if block.get('date_field'):
            srows = list(
                qs.annotate(month=TruncMonth(block['date_field']))
                .values('month')
                .annotate(**_agg_expr(agg))
                .order_by('month')
            )
            series = [
                {'label': s['month'].strftime('%Y-%m') if s['month'] else '',
                 'value': s['value'] or 0}
                for s in srows
            ]
        return {'value': value, 'series': series}

    # ── Pie / Bar: group by field ──
    if btype in ('pie', 'bar'):
        gb = block['group_by']
        key = _group_key(model_cls, gb)
        rows = list(
            qs.values(key).annotate(**_agg_expr(agg)).order_by(block.get('sort', '-value'))
        )
        rows = [
            {'label': (r[key] if r[key] is not None else '(empty)'), 'value': r['value'] or 0}
            for r in rows
        ]
        if block.get('limit'):
            rows = rows[:block['limit']]
        return {'rows': rows}

    # ── Line: time series by month ──
    if btype == 'line':
        rows = list(
            qs.annotate(month=TruncMonth(block['date_field']))
            .values('month')
            .annotate(**_agg_expr(agg))
            .order_by('month')
        )
        rows = [
            {'label': r['month'].strftime('%Y-%m') if r['month'] else '',
             'value': r['value'] or 0}
            for r in rows
        ]
        return {'rows': rows}

    # ── Funnel: count per item (multi-model stage comparison) ──
    if btype == 'funnel':
        rows = []
        for item in block.get('items', []):
            m = _get_model(item['model'])
            if not m:
                continue
            iqs = m.objects.filter(is_deleted=False)
            for f, v in (item.get('filters') or {}).items():
                iqs = iqs.filter(**{f: v})
            iqs = _apply_date_filter(iqs, item, date_from, date_to)
            value = iqs.aggregate(**_agg_expr(item.get('aggregate') or agg))['value'] or 0
            rows.append({'label': item.get('label', item['model']), 'value': value})
        return {'rows': rows}

    # ── Aging: buckets relatif terhadap hari ini ──
    if btype == 'aging':
        today = date.today()
        df = block['date_field']
        rows = []
        for b in block.get('buckets', []):
            iqs = qs
            if b.get('max_days') is not None:
                iqs = iqs.filter(**{f'{df}__lt': today + timedelta(days=b['max_days'])})
            if b.get('min_days') is not None:
                iqs = iqs.filter(**{f'{df}__gte': today + timedelta(days=b['min_days'])})
            value = iqs.aggregate(**_agg_expr(agg))['value'] or 0
            rows.append({'label': b.get('label', b.get('key', '')), 'value': value})
        return {'rows': rows}

    # ── Summary: grouped aggregate (label + count + value) ──
    if btype == 'summary':
        gb = block['group_by']
        key = _group_key(model_cls, gb)
        grouped = (
            qs.values(key)
            .annotate(count=Count('id'), value=Sum(agg.get('field')) if agg.get('func') == 'sum' else Count('id'))
            .order_by(block.get('sort', '-value'))
        )
        total = grouped.count()
        if page_size == 0:
            rows = list(grouped)
        else:
            offset = (page - 1) * page_size
            rows = list(grouped[offset:offset + page_size])
        rows = [
            {'label': (r[key] if r[key] is not None else '(empty)'),
             'count': r['count'], 'value': r['value'] or 0}
            for r in rows
        ]
        return {'count': total, 'rows': rows, 'page': page, 'page_size': page_size}

    # ── Grid: raw records (full pagination via page_size=0 → semua) ──
    if btype == 'grid':
        columns = block.get('columns') or getattr(model_cls, '_list_view', {}).get('columns', [])
        total = qs.count()
        if page_size == 0:
            objs = list(qs)
        else:
            offset = (page - 1) * page_size
            objs = list(qs[offset:offset + page_size])
        results = [_serialize(o, columns) for o in objs]
        return {'count': total, 'rows': results, 'page': page, 'page_size': page_size}

    return {'error': f'Unknown block type {btype}'}


# ─── Endpoint ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request, key):
    """Return dashboard config + computed data for all blocks.

    Query params:
      date_from / date_to     → global date filter (block harus punya date_field)
      page_{key} / page_size_{key} → pagination per grid/summary block
                                     (page_size_{key}=0 → semua rows)
    """
    config = DASHBOARD_REGISTRY.get(key)
    if not config:
        return Response({'error': f'Dashboard "{key}" not found'}, status=404)

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    blocks = []
    fields = {}
    for block in config.get('blocks', []):
        bkey = block.get('key', '')
        page = int(request.query_params.get(f'page_{bkey}', 1))
        page_size = int(request.query_params.get(f'page_size_{bkey}', block.get('page_size', 10)))

        result = _run_block(block, date_from=date_from, date_to=date_to,
                            page=page, page_size=page_size)
        blocks.append({**block, 'data': result})

        # Sertakan field config semua model yang dipakai (label & warna)
        model_names = [block.get('model', '')]
        if block.get('type') == 'funnel':
            model_names += [i.get('model', '') for i in block.get('items', [])]
        for mn in model_names:
            m = _get_model(mn)
            if m and mn not in fields:
                fields[mn] = {k: fd.to_config() for k, fd in m._field_descriptors.items()}

    return Response({
        'key': key,
        'title': config.get('title', key),
        'blocks': blocks,
        'fields': fields,
    })
