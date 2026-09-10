"""Tax report engine — rekap pajak dari tag `taxes` di baris dokumen.

Mengagregasi seluruh baris dokumen ber-pajak (Sales Order, Purchase Order,
Faktur, Tagihan, Quick Sales, Quick Purchase) per tag pajak:
DPP (dasar pengenaan) + nilai pajak + jumlah transaksi, lengkap dengan
rincian per modul.

Sumber data (model baris + pemetaan parent/date/status/reference) hanya
didefinisikan di TAX_SOURCES. Logika agregasi 100% generik:
    dasar = qty × price − discount_amount   (kolom tersimpan)
lalu core.models.accounting.tax.line_tax_parts() memisah include/exclude
(include → DPP = dasar/(1+rate), tidak menambah total).
"""
from django.db.models import Q

from core.model_meta import ErpModelBase
from core.models.accounting.tax import line_tax_parts

# ── Sumber data: satu-satunya bagian yang menyebut nama model ──
# parent/date_field/status_field/reference_field = field pada model HEADER
# yang diakses lewat prefix `parent__` pada model baris.
TAX_SOURCES = [
    {
        'key': 'sales.order',
        'label': 'Sales Order',
        'short': 'SO',
        'line_model': 'sales.order.line',
        'parent': 'order_id',
        'date_field': 'order_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
    {
        'key': 'purchase.order',
        'label': 'Purchase Order',
        'short': 'PO',
        'line_model': 'purchase.order.line',
        'parent': 'order_id',
        'date_field': 'order_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
    {
        'key': 'accounting.customer_invoice',
        'label': 'Faktur',
        'short': 'Faktur',
        'line_model': 'accounting.customer_invoice_line',
        'parent': 'invoice_id',
        'date_field': 'invoice_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
    {
        'key': 'accounting.vendor_bill',
        'label': 'Tagihan',
        'short': 'Tagihan',
        'line_model': 'accounting.vendor_bill_line',
        'parent': 'bill_id',
        'date_field': 'bill_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
    {
        'key': 'sales.quick_sales',
        'label': 'Quick Sales',
        'short': 'Quick SO',
        'line_model': 'sales.quick_sales.line',
        'parent': 'quick_sales_id',
        'date_field': 'order_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
    {
        'key': 'purchase.quick_purchase',
        'label': 'Quick Purchase',
        'short': 'Quick PO',
        'line_model': 'purchase.quick_purchase.line',
        'parent': 'quick_purchase_id',
        'date_field': 'order_date',
        'status_field': 'status',
        'reference_field': 'reference',
    },
]

META = {s['key']: s for s in TAX_SOURCES}


def _resolve(model_name):
    return ErpModelBase._model_registry.get(model_name)


def _blank():
    return {'dpp': 0.0, 'tax_amount': 0.0, 'count': 0}


def _acc(bucket, dpp, tax):
    bucket['dpp'] += dpp
    bucket['tax_amount'] += tax
    bucket['count'] += 1


class TaxReportEngine:
    """Agregasi pajak dari baris dokumen lintas modul."""

    @staticmethod
    def tax_report(date_from=None, date_to=None, module_keys=None,
                   tax_ids=None, include_draft=True, search=None):
        """Rekap pajak per tag → { modules, rows, totals }.

        module_keys : batasi ke modul tertentu (key TAX_SOURCES); None = semua.
        tax_ids     : batasi ke tag pajak tertentu; None = semua.
        include_draft: True = ikutkan dokumen draft (hanya `cancelled` dibuang).
        """
        from core.models.accounting.tax import Tax

        active_modules = [
            s for s in TAX_SOURCES
            if not module_keys or s['key'] in module_keys
        ]

        tax_filter = None
        if tax_ids:
            try:
                tax_filter = [int(t) for t in tax_ids]
            except (TypeError, ValueError):
                tax_filter = None

        # Akumulator per tax_id → {dpp, tax_amount, count, by_module{}}
        agg = {}
        undated_count = 0

        for src in active_modules:
            line_model = _resolve(src['line_model'])
            if not line_model:
                continue
            prefix = src['parent']
            date_field = f'{prefix}__{src["date_field"]}'
            status_field = f'{prefix}__{src["status_field"]}'
            qs = line_model.objects.filter(
                is_deleted=False,
                **{f'{prefix}__is_deleted': False},
            )
            # Default: draft ikut dihitung; bila include_draft=False hanya
            # dokumen terkonfirmasi. `cancelled` selalu dibuang.
            if include_draft:
                qs = qs.exclude(**{status_field: 'cancelled'})
            else:
                qs = qs.filter(**{f'{status_field}__in': ['confirmed', 'done', 'paid']})
            qs = qs.exclude(taxes_id__isnull=True)
            if tax_filter is not None:
                qs = qs.filter(taxes_id__in=tax_filter)

            # Rentang tanggal: dokumen TANPA tanggal (kolom date NULL) tetap
            # ikut dihitung — kalau dibuang, transaksi ber-pajak bisa hilang
            # diam-diam dari laporan. Jumlahnya dilaporkan sebagai `undated_count`.
            if date_from or date_to:
                rng = Q()
                if date_from:
                    rng &= Q(**{f'{date_field}__gte': date_from})
                if date_to:
                    rng &= Q(**{f'{date_field}__lte': date_to})
                null_q = Q(**{f'{date_field}__isnull': True})
                undated_count += qs.filter(null_q).count()
                qs = qs.filter(rng | null_q)

            for line in qs.only('pk', 'qty', 'price', 'discount_amount', 'taxes_id', 'tax_amount').iterator():
                raw = getattr(line, 'taxes_id_id', None)
                if raw is None:
                    rel = getattr(line, 'taxes_id', None)
                    raw = getattr(rel, 'pk', rel)
                if raw is None:
                    continue
                try:
                    tax_id = int(raw)
                except (TypeError, ValueError):
                    continue
                base = (float(line.qty or 0) * float(line.price or 0)
                        - float(getattr(line, 'discount_amount', 0) or 0))
                inc, exc, net_base = line_tax_parts(base, tax_id)
                dpp = net_base
                tax_amt = inc + exc

                entry = agg.get(tax_id)
                if entry is None:
                    entry = {'dpp': 0.0, 'tax_amount': 0.0, 'count': 0, 'by_module': {}}
                    agg[tax_id] = entry
                _acc(entry, dpp, tax_amt)
                mod = entry['by_module'].setdefault(src['key'], _blank())
                _acc(mod, dpp, tax_amt)

        # ── Susun baris per tag pajak (lengkap dengan meta master pajak) ──
        tax_objs = {t.pk: t for t in Tax.objects.filter(pk__in=list(agg.keys()))}
        rows = []
        for tax_id, entry in agg.items():
            tax = tax_objs.get(tax_id)
            if tax is None:
                continue
            rows.append({
                'tax_id': tax_id,
                'name': str(getattr(tax, 'name', '') or ''),
                'rate': float(getattr(tax, 'rate', 0) or 0),
                'is_include': bool(getattr(tax, 'is_include', False)),
                'dpp': round(entry['dpp'], 2),
                'tax_amount': round(entry['tax_amount'], 2),
                'count': entry['count'],
                'by_module': {
                    k: {
                        'dpp': round(v['dpp'], 2),
                        'tax_amount': round(v['tax_amount'], 2),
                        'count': v['count'],
                    }
                    for k, v in entry['by_module'].items()
                },
            })

        if search:
            needle = str(search).lower()
            rows = [r for r in rows if needle in r['name'].lower()]

        rows.sort(key=lambda r: (-r['tax_amount'], (r['name'] or '').lower()))

        totals = {'dpp': 0.0, 'tax_amount': 0.0, 'count': 0, 'by_module': {}}
        for r in rows:
            totals['dpp'] += r['dpp']
            totals['tax_amount'] += r['tax_amount']
            totals['count'] += r['count']
            for k, v in r['by_module'].items():
                tm = totals['by_module'].setdefault(k, _blank())
                tm['dpp'] += v['dpp']
                tm['tax_amount'] += v['tax_amount']
                tm['count'] += v['count']
        totals['dpp'] = round(totals['dpp'], 2)
        totals['tax_amount'] = round(totals['tax_amount'], 2)
        for k, v in totals['by_module'].items():
            v['dpp'] = round(v['dpp'], 2)
            v['tax_amount'] = round(v['tax_amount'], 2)

        return {
            'key': 'tax_report',
            'title': 'Report Pajak',
            'period': {'date_from': date_from or '', 'date_to': date_to or ''},
            'include_draft': bool(include_draft),
            'undated_count': undated_count,
            'modules': [
                {'key': s['key'], 'label': s['label'], 'short': s['short']}
                for s in active_modules
            ],
            'rows': rows,
            'totals': totals,
        }
