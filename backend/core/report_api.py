"""Generic meta-driven financial report engine (Laba Rugi, Neraca, dst).

Report = config declarative + agregasi baris jurnal (jurnal status=posted).
Engine 100% generic — TIDAK menyebut nama model; semua sumber data
(line_model, account_model, fields) dibaca dari config per report
(lihat core/models/accounting/report.py). Saldo akun mengikuti normal
balance tipe akun (debit/credit) dari config.

Endpoint:
    GET /api/reports/{key}/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    → { key, title, period, sections: [{key,title,rows:[{code,name,amount}],subtotal}],
        totals: [{key,label,amount}] }
"""
import re

from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

REPORT_REGISTRY = {}


def register_report(key, config):
    """Register config report di bawah key unik (mis. 'profit_loss')."""
    REPORT_REGISTRY[key] = config


def _resolve_model(model_name):
    from core.model_meta import ErpModelBase
    return ErpModelBase._model_registry.get(model_name)


def _eval_formula(expr, subtotals):
    """Evaluasi formula sederhana 'section_key + section_key - ...'."""
    tokens = [t.strip() for t in re.split(r'\s*([+-])\s*', expr) if t.strip()]
    total = 0
    sign = 1
    for tok in tokens:
        if tok in ('+', '-'):
            sign = 1 if tok == '+' else -1
        elif tok in subtotals:
            total += sign * float(subtotals.get(tok, 0) or 0)
        else:
            raise ValueError(f'Unknown section key in formula: {tok}')
    return total


def _build_report(config, date_from, date_to):
    """Hitung struktur report dari config + data jurnal."""
    line_model = _resolve_model(config['line_model'])
    account_model = _resolve_model(config['account_model'])
    if not line_model or not account_model:
        return None, 'Report config model not found'

    account_field = config['account_field']
    account_type_field = config['account_type_field']
    account_parent_field = config['account_parent_field']
    status_field = config['status_field']
    date_field = config['date_field']
    normal_balance = config.get('normal_balance', {})
    leaves_only_default = config.get('leaves_only', True)
    sides = config.get('sides', False)
    balance_col = config.get('balance_col', False)

    # 1. Meta semua akun COA + deteksi parent
    accounts = list(account_model.objects.filter(is_deleted=False))
    account_meta = {}
    parent_ids = set()
    for acc in accounts:
        parent = getattr(acc, account_parent_field, None)
        parent_id = parent.pk if parent else None
        account_meta[acc.pk] = {
            'code': str(getattr(acc, config['account_code_field'], '') or ''),
            'name': str(getattr(acc, config['account_name_field'], '') or ''),
            'type': getattr(acc, account_type_field, None),
            'parent_id': parent_id,
        }
        if parent_id:
            parent_ids.add(parent_id)

    # 2. Agregasi debit/credit per akun dari baris jurnal (posted + rentang)
    qs = line_model.objects.filter(is_deleted=False, **{status_field: config['status']})
    if date_from:
        qs = qs.filter(**{f'{date_field}__gte': date_from})
    if date_to:
        qs = qs.filter(**{f'{date_field}__lte': date_to})
    agg = qs.values(f'{account_field}_id').annotate(
        total_debit=Sum(config['debit_field']),
        total_credit=Sum(config['credit_field']),
    )
    balances = {row[f'{account_field}_id']: row for row in agg}

    # 3. Bangun sections (rows akun + subtotal)
    sections = []
    subtotals = {}
    for section in config.get('sections', []):
        account_types = section.get('account_types', [])
        account_codes = section.get('account_codes')  # optional: filter kode akun persis
        leaves_only = section.get('leaves_only', leaves_only_default)
        rows = []
        for acc_id, meta in account_meta.items():
            if meta['type'] not in account_types:
                continue
            if account_codes is not None and meta['code'] not in account_codes:
                continue
            if leaves_only and acc_id in parent_ids:
                continue  # akun header (punya child) tidak ditampilkan
            row = balances.get(acc_id)
            total_debit = float(row['total_debit'] or 0) if row else 0
            total_credit = float(row['total_credit'] or 0) if row else 0
            normal = normal_balance.get(meta['type'], 'debit')
            balance = (total_debit - total_credit) if normal == 'debit' else (total_credit - total_debit)
            if abs(balance) < 0.005:
                balance = 0.0
            entry = {'code': meta['code'], 'name': meta['name'], 'amount': round(balance, 2)}
            if sides:
                # Kolom sisi debit/kredit mentah (untuk Neraca Saldo, Buku Besar, Arus Kas)
                entry['debit'] = round(total_debit, 2)
                entry['credit'] = round(total_credit, 2)
            rows.append(entry)
        rows.sort(key=lambda r: r['code'])
        subtotal = round(sum(r['amount'] for r in rows), 2)
        section_out = {
            'key': section['key'],
            'title': section['title'],
            'rows': rows,
            'subtotal': subtotal,
        }
        if sides:
            debit_subtotal = round(sum(r['debit'] for r in rows), 2)
            credit_subtotal = round(sum(r['credit'] for r in rows), 2)
            section_out['debit_subtotal'] = debit_subtotal
            section_out['credit_subtotal'] = credit_subtotal
            # Token formula (mis. 'arus_kas_debit') agar totals bisa memakai sisi
            subtotals[f"{section['key']}_debit"] = debit_subtotal
            subtotals[f"{section['key']}_credit"] = credit_subtotal
        subtotals[section['key']] = subtotal
        sections.append(section_out)

    # 4. Totals: (a) total sisi debit/kredit global (opsional), (b) formula dari subtotal
    totals = []
    for st in config.get('sides_totals', []):
        side = st.get('side', 'debit')
        amount = round(sum(s.get(f'{side}_subtotal', 0) for s in sections), 2)
        totals.append({'key': st['key'], 'label': st['label'], 'amount': amount})
    for t in config.get('totals', []):
        try:
            amount = round(_eval_formula(t['formula'], subtotals), 2)
        except ValueError as exc:
            amount = 0
            totals.append({'key': t['key'], 'label': t['label'], 'amount': amount, 'error': str(exc)})
            continue
        totals.append({'key': t['key'], 'label': t['label'], 'amount': amount})

    payload = {
        'key': config['key'],
        'title': config['title'],
        'period': {'date_from': date_from or '', 'date_to': date_to or ''},
        'sections': sections,
        'totals': totals,
    }
    if sides:
        payload['show_sides'] = True
    if balance_col:
        payload['show_balance_col'] = True
    return payload, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_data(request, key):
    """GET /api/reports/{key}/?date_from=&date_to= → data report."""
    config = REPORT_REGISTRY.get(key)
    if not config:
        return Response({'error': f'Report "{key}" not found'}, status=404)

    date_from = request.query_params.get('date_from') or None
    date_to = request.query_params.get('date_to') or None

    payload, error = _build_report(config, date_from, date_to)
    if error:
        return Response({'error': error}, status=400)
    return Response(payload)
