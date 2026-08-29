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
from django.db.models import Sum

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
