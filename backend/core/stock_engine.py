"""
Stock Engine — satu-satunya file yang mengatur perhitungan stok.

Konsep:
- Stok disimpan di LOKASI (inventory.warehouse_location) di dalam warehouse.
- Stok bersifat LEDGER: on-hand TIDAK disimpan, di-compute dari row ledger.
- Setiap dokumen (DO, GR, dst) cukup "kirim data" ke engine → engine menulis
  row ledger. Model lain yang butuh angka stok tinggal baca via StockEngine.
- Row ledger bersifat immutable: revisi/cancel = soft-delete row (is_deleted=True)
  sehingga angka on-hand tetap benar tapi data historis tetap ada di DB.
- Hanya product dengan tipe_product='Stock' yang dilacak.

Cara pakai dari model (contoh delivery_order):
    from core.stock_engine import StockEngine

    # Posting saat done:
    StockEngine.post(
        document={'model': 'sales.delivery_order', 'id': self.pk,
                  'reference': self.reference, 'date': self.delivery_date},
        lines=[{'product_id': line.product_id, 'location_id': self.location_id,
                'quantity': -line.delivered_qty, 'cost': line.unit_price,
                'description': line.name, 'source_line_id': line.pk}
               for line in lines],
    )

    # Cancel:
    StockEngine.delete(document={'model': 'sales.delivery_order', 'id': self.pk})

    # Cek stok minus sebelum posting:
    warnings = StockEngine.check_negative(lines)
"""
from django.db.models import Q, Sum

from core.model_meta import ErpModelBase


class StockEngine:
    """Engine stok berbasis ledger."""

    # ── Public API ──

    @classmethod
    def post(cls, document, lines):
        """
        Tulis row ledger dari satu dokumen.

        document: dict {model, id, reference, date}
        lines: list of dict {product_id, location_id, quantity, cost, description, source_line_id}
               quantity bertanda: + masuk, - keluar.
        Skip otomatis product dengan tipe_product != 'Stock'.
        Idempotent per (model, id, source_line_id): tidak menulis duplikat.
        """
        ledger_cls = cls._ledger_cls()
        if ledger_cls is None:
            return 0

        ref = document.get('reference') or ''
        date = document.get('date')

        created = 0
        for line in lines:
            if not line.get('product_id') or not line.get('location_id'):
                continue
            if not line.get('quantity'):
                continue
            if not cls._is_stock_product(line['product_id']):
                continue

            exists = ledger_cls.objects.filter(
                source_model=document['model'],
                source_id=document['id'],
                source_line_id=line.get('source_line_id') or 0,
                is_deleted=False,
            ).exists()
            if exists:
                continue

            ledger_cls.objects.create(
                product_id=line['product_id'],
                location_id=line['location_id'],
                quantity=line['quantity'],
                source_model=document['model'],
                source_id=document['id'],
                source_line_id=line.get('source_line_id') or 0,
                source_reference=ref,
                date=date,
                unit_cost=line.get('cost'),
                description=line.get('description', ''),
            )
            created += 1
        return created

    @classmethod
    def delete(cls, document):
        """
        Batalkan dampak stok sebuah dokumen — soft-delete row ledger-nya.

        Row tetap ada di DB (is_deleted=True) sebagai history/tracking.
        Idempotent: aman dipanggil berulang (draft/waiting → tidak ada row).
        """
        ledger_cls = cls._ledger_cls()
        if ledger_cls is None:
            return 0
        return ledger_cls.objects.filter(
            source_model=document['model'],
            source_id=document['id'],
            is_deleted=False,
        ).update(is_deleted=True)

    @classmethod
    def on_hand(cls, product_id, location_id=None):
        """
        Hitung stok on-hand = SUM(quantity) dari row ledger aktif.
        Di-compute setiap dipanggil — tidak ada kolom on-hand tersimpan.
        """
        ledger_cls = cls._ledger_cls()
        if ledger_cls is None:
            return 0.0
        qs = ledger_cls.objects.filter(product_id=product_id, is_deleted=False)
        if location_id is not None:
            qs = qs.filter(location_id=location_id)
        total = qs.aggregate(total=Sum('quantity'))['total']
        return float(total or 0.0)

    @classmethod
    def check_negative(cls, lines):
        """
        Cek apakah posting qty keluar akan membuat stok minus.

        lines: list of dict {product_id, location_id, quantity(negatif)}
        Return list warning: [{product_id, product_name, location_id, available, required, deficit}]
        """
        warnings = []
        for line in lines:
            qty = float(line.get('quantity') or 0)
            if qty >= 0:
                continue
            if not line.get('product_id') or not line.get('location_id'):
                continue
            if not cls._is_stock_product(line['product_id']):
                continue
            available = cls.on_hand(line['product_id'], line['location_id'])
            required = -qty
            if available < required:
                product = cls._product_name(line['product_id'])
                location = cls._location_name(line['location_id'])
                warnings.append({
                    'product_id': line['product_id'],
                    'product_name': product,
                    'location_id': line['location_id'],
                    'location_name': location,
                    'available': available,
                    'required': required,
                    'deficit': required - available,
                })
        return warnings

    @classmethod
    def stock_balance(cls, date_from=None, date_to=None, location_id=None):
        """
        Laporan Stock Balance — agregasi row ledger aktif per produk.

        date_from/date_to: rentang periode (objek date atau string 'YYYY-MM-DD').
        - opening = saldo row dengan date < date_from (0 bila date_from None)
        - qty_in  = SUM(quantity > 0) dalam periode
        - qty_out = |SUM(quantity < 0)| dalam periode
        - closing = opening + qty_in - qty_out
        Tanpa rentang: seluruh row dianggap periode → closing = on-hand total.
        location_id opsional: batasi ke satu lokasi.

        Return: {key, title, period, rows, totals}
          rows: [{product_id, code, name, uom, opening, qty_in, qty_out, closing}]
          totals: {opening, qty_in, qty_out, closing}
        """
        from datetime import datetime, date as date_cls

        def _norm(v):
            if v is None:
                return None
            if isinstance(v, date_cls):
                return v
            try:
                return datetime.strptime(str(v)[:10], '%Y-%m-%d').date()
            except ValueError:
                return None

        ledger_cls = cls._ledger_cls()
        if ledger_cls is None:
            return cls._empty_balance(date_from, date_to)

        d_from = _norm(date_from)
        d_to = _norm(date_to)

        base = ledger_cls.objects.filter(is_deleted=False)
        if location_id is not None:
            base = base.filter(location_id=location_id)

        # opening: row sebelum periode
        opening_map = {}
        if d_from:
            agg = base.filter(date__lt=d_from).values('product_id').annotate(total=Sum('quantity'))
            opening_map = {r['product_id']: float(r['total'] or 0) for r in agg}

        # pergerakan dalam periode
        mov_qs = base
        if d_from:
            mov_qs = mov_qs.filter(date__gte=d_from)
        if d_to:
            mov_qs = mov_qs.filter(date__lte=d_to)

        in_map = {r['product_id']: float(r['total'] or 0) for r in
                  mov_qs.filter(quantity__gt=0).values('product_id').annotate(total=Sum('quantity'))}
        out_map = {r['product_id']: -float(r['total'] or 0) for r in
                   mov_qs.filter(quantity__lt=0).values('product_id').annotate(total=Sum('quantity'))}

        product_ids = set(opening_map) | set(in_map) | set(out_map)

        # meta produk (code/name/uom) sekali query
        product_cls = ErpModelBase._model_registry.get('inventory.product')
        meta = {}
        if product_cls is not None and product_ids:
            prods = product_cls.objects.filter(id__in=product_ids, is_deleted=False)
            for p in prods:
                meta[p.pk] = {
                    'code': getattr(p, 'code', None) or '',
                    'name': str(p),
                    'uom': str(getattr(p, 'uom', '') or ''),
                }

        def _round(v):
            return round(v, 3)

        rows = []
        for pid in sorted(product_ids):
            opening = opening_map.get(pid, 0.0)
            qty_in = in_map.get(pid, 0.0)
            qty_out = out_map.get(pid, 0.0)
            m = meta.get(pid, {'code': '', 'name': f'#{pid}', 'uom': ''})
            rows.append({
                'product_id': pid,
                'code': m['code'],
                'name': m['name'],
                'uom': m['uom'],
                'opening': _round(opening),
                'qty_in': _round(qty_in),
                'qty_out': _round(qty_out),
                'closing': _round(opening + qty_in - qty_out),
            })

        totals = {
            'opening': _round(sum(r['opening'] for r in rows)),
            'qty_in': _round(sum(r['qty_in'] for r in rows)),
            'qty_out': _round(sum(r['qty_out'] for r in rows)),
            'closing': _round(sum(r['closing'] for r in rows)),
        }
        return {
            'key': 'stock_balance',
            'title': 'Stock Balance',
            'period': {'date_from': str(d_from) if d_from else '',
                       'date_to': str(d_to) if d_to else ''},
            'rows': rows,
            'totals': totals,
        }

    @classmethod
    def _empty_balance(cls, date_from=None, date_to=None):
        return {
            'key': 'stock_balance',
            'title': 'Stock Balance',
            'period': {'date_from': date_from or '', 'date_to': date_to or ''},
            'rows': [],
            'totals': {'opening': 0.0, 'qty_in': 0.0, 'qty_out': 0.0, 'closing': 0.0},
        }

    # ── Helpers ──

    @classmethod
    def _ledger_cls(cls):
        return ErpModelBase._model_registry.get('inventory.stock_ledger')

    @classmethod
    def _is_stock_product(cls, product_id):
        product_cls = ErpModelBase._model_registry.get('inventory.product')
        if product_cls is None:
            return True
        try:
            product = product_cls.objects.get(pk=product_id, is_deleted=False)
        except product_cls.DoesNotExist:
            return False
        return getattr(product, 'tipe_product', 'Stock') == 'Stock'

    @classmethod
    def _product_name(cls, product_id):
        product_cls = ErpModelBase._model_registry.get('inventory.product')
        if product_cls is None:
            return str(product_id)
        try:
            return str(product_cls.objects.get(pk=product_id, is_deleted=False))
        except product_cls.DoesNotExist:
            return f'#{product_id}'

    @classmethod
    def _location_name(cls, location_id):
        loc_cls = ErpModelBase._model_registry.get('inventory.warehouse_location')
        if loc_cls is None:
            return str(location_id)
        try:
            return str(loc_cls.objects.get(pk=location_id, is_deleted=False))
        except loc_cls.DoesNotExist:
            return f'#{location_id}'
