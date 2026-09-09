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

    # Label sumber pergerakan utk laporan (key = source_model di stock ledger)
    SOURCE_LABELS = {
        'purchase.goods_receipt': 'Penerimaan (GR)',
        'sales.delivery_order': 'Pengiriman (DO)',
        'inventory.stock_in': 'Transfer Masuk',
        'inventory.stock_out': 'Transfer Keluar',
        'inventory.stock_adjustment': 'Penyesuaian',
    }

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
    def stock_balance(cls, date=None, location_id=None):
        """
        Laporan Stock Balance — saldo stok per produk pada SATU tanggal.

        date: objek date / string 'YYYY-MM-DD' (None = tanpa batas tanggal,
        artinya seluruh row aktif = saldo terkini).
        Saldo = SUM(quantity) row ledger aktif dengan date <= tanggal tsb
        (soft-delete tidak dihitung). location_id None = semua lokasi.

        Return: {key, title, date, rows, totals}
          rows: [{product_id, code, name, uom, qty}]
          totals: {qty}
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
        empty = {
            'key': 'stock_balance', 'title': 'Stock Balance',
            'date': str(_norm(date) or ''), 'rows': [],
            'totals': {'qty': 0.0},
        }
        if ledger_cls is None:
            return empty

        d = _norm(date)
        base = ledger_cls.objects.filter(is_deleted=False)
        if location_id is not None:
            base = base.filter(location_id=location_id)
        if d is not None:
            base = base.filter(date__lte=d)

        qty_map = {r['product_id']: float(r['total'] or 0) for r in
                   base.values('product_id').annotate(total=Sum('quantity'))}
        if not qty_map:
            return empty

        product_cls = ErpModelBase._model_registry.get('inventory.product')
        meta = {}
        if product_cls is not None:
            prods = product_cls.objects.filter(id__in=set(qty_map), is_deleted=False)
            for p in prods:
                meta[p.pk] = {
                    'code': getattr(p, 'code', None) or '',
                    'name': str(p),
                    'uom': str(getattr(p, 'uom', '') or ''),
                }

        rows = []
        for pid, qty in qty_map.items():
            m = meta.get(pid, {'code': '', 'name': f'#{pid}', 'uom': ''})
            rows.append({
                'product_id': pid,
                'code': m['code'],
                'name': m['name'],
                'uom': m['uom'],
                'qty': round(qty, 3),
            })
        rows.sort(key=lambda r: (r['code'] or r['name']).lower())

        return {
            'key': 'stock_balance',
            'title': 'Stock Balance',
            'date': str(d) if d else '',
            'rows': rows,
            'totals': {'qty': round(sum(r['qty'] for r in rows), 3)},
        }

    @classmethod
    def stock_card(cls, product_id=None, location_id=None, date_from=None, date_to=None):
        """
        Laporan Kartu Stok — detail pergerakan per (produk, lokasi) dari row
        stock ledger aktif, lengkap dengan saldo berjalan.

        date_from/date_to: batas periode tampil. Saldo berjalan tetap dihitung
        dari seluruh row aktif (termasuk sebelum date_from) sehingga angka
        saldo = stok nyata setelah pergerakan tsb.

        Return: {key, title, filters, rows}
          rows urut per (produk, lokasi):
            - kind 'opening'  : baris Saldo Awal (saldo tepat sebelum date_from)
            - kind 'movement' : satu row per pergerakan (GR/DO/transfer/penyesuaian)
            - kind 'closing'  : baris Saldo Akhir (saldo setelah periode)
          Field umum: product_id/code/name/uom, location_id/location_name,
          date, source_label, reference, description, qty_in, qty_out, balance.
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

        def _row_base(pid, lid, pm, loc_name):
            return {
                'product_id': pid,
                'code': pm['code'],
                'name': pm['name'],
                'uom': pm['uom'],
                'location_id': lid,
                'location_name': loc_name,
            }

        filters = {
            'product_id': product_id,
            'location_id': location_id,
            'date_from': str(_norm(date_from) or ''),
            'date_to': str(_norm(date_to) or ''),
        }
        ledger_cls = cls._ledger_cls()
        empty = {'key': 'stock_card', 'title': 'Stock Card',
                 'filters': filters, 'rows': []}
        if ledger_cls is None:
            return empty

        d_from = _norm(date_from)
        d_to = _norm(date_to)

        qs = ledger_cls.objects.filter(is_deleted=False)
        if product_id is not None:
            qs = qs.filter(product_id=product_id)
        if location_id is not None:
            qs = qs.filter(location_id=location_id)
        if d_to is not None:
            qs = qs.filter(date__lte=d_to)

        events = list(qs.values(
            'id', 'product_id', 'location_id', 'date', 'quantity',
            'source_model', 'source_reference', 'description'))
        if not events:
            return empty

        # meta produk + lokasi sekali query
        product_cls = ErpModelBase._model_registry.get('inventory.product')
        pids = {e['product_id'] for e in events}
        pmeta = {}
        if product_cls is not None:
            for p in product_cls.objects.filter(id__in=pids, is_deleted=False):
                pmeta[p.pk] = {
                    'code': getattr(p, 'code', None) or '',
                    'name': str(p),
                    'uom': str(getattr(p, 'uom', '') or ''),
                }
        loc_cls = ErpModelBase._model_registry.get('inventory.warehouse_location')
        lids = {e['location_id'] for e in events}
        lmeta = {}
        if loc_cls is not None:
            for loc in loc_cls.objects.filter(id__in=lids, is_deleted=False):
                lmeta[loc.pk] = str(loc)

        # kelompokkan per (produk, lokasi), urut tanggal + id
        groups = {}
        for e in events:
            groups.setdefault((e['product_id'], e['location_id']), []).append(e)
        for gkey in groups:
            groups[gkey].sort(key=lambda e: (e['date'] or date_cls(1900, 1, 1), e.get('id') or 0))

        def _gkey_sort(gkey):
            pid, lid = gkey
            pm = pmeta.get(pid, {'code': '', 'name': f'#{pid}', 'uom': ''})
            return ((pm['code'] or pm['name']).lower(),
                    lmeta.get(lid, f'#{lid}').lower())

        rows = []
        for gkey in sorted(groups, key=_gkey_sort):
            pid, lid = gkey
            pm = pmeta.get(pid, {'code': '', 'name': f'#{pid}', 'uom': ''})
            loc_name = lmeta.get(lid, f'#{lid}')

            prefix = []
            shown = []
            for e in groups[gkey]:
                if d_from is not None and (e['date'] or date_cls(1900, 1, 1)) < d_from:
                    prefix.append(e)
                else:
                    shown.append(e)

            opening = sum(float(e['quantity'] or 0) for e in prefix)

            if not shown:
                # Tidak ada pergerakan dalam periode — tampilkan baris saldo
                # saja bila produk spesifik dipilih (hindari noise di mode semua).
                if product_id is None:
                    continue
                base = _row_base(pid, lid, pm, loc_name)
                rows.append({**base, 'kind': 'opening', 'date': str(d_from) if d_from else '',
                             'source_label': '', 'reference': 'Saldo Awal',
                             'description': '', 'qty_in': None, 'qty_out': None,
                             'balance': round(opening, 3)})
                rows.append({**base, 'kind': 'closing', 'date': str(d_to) if d_to else '',
                             'source_label': '', 'reference': 'Saldo Akhir',
                             'description': '', 'qty_in': None, 'qty_out': None,
                             'balance': round(opening, 3)})
                continue

            base = _row_base(pid, lid, pm, loc_name)
            rows.append({**base, 'kind': 'opening', 'date': str(d_from) if d_from else '',
                         'source_label': '', 'reference': 'Saldo Awal',
                         'description': '', 'qty_in': None, 'qty_out': None,
                         'balance': round(opening, 3)})

            running = opening
            for e in shown:
                qty = float(e['quantity'] or 0)
                running += qty
                model = e['source_model'] or ''
                rows.append({
                    **base, 'kind': 'movement',
                    'date': str(e['date']) if e['date'] else '',
                    'source_label': cls.SOURCE_LABELS.get(model, model),
                    'reference': e['source_reference'] or '',
                    'description': e['description'] or '',
                    'qty_in': round(qty, 3) if qty > 0 else None,
                    'qty_out': round(-qty, 3) if qty < 0 else None,
                    'balance': round(running, 3),
                })

            rows.append({**base, 'kind': 'closing', 'date': str(d_to) if d_to else '',
                         'source_label': '', 'reference': 'Saldo Akhir',
                         'description': '', 'qty_in': None, 'qty_out': None,
                         'balance': round(running, 3)})

        return {'key': 'stock_card', 'title': 'Stock Card',
                'filters': filters, 'rows': rows}

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
