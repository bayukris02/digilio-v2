from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField,
    Many2OneField,
)
from core.model_meta import BaseModel


class PurchaseRequestLine(BaseModel):
    _model_name = 'purchase.request.line'

    _fields = {
        'request_id': Many2OneField(
            label='Permintaan Pembelian',
            relation='purchase.request',
            required=True,
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'description': 'name'},
        ),
        'description': TextField(label='Deskripsi'),
        'uom': Many2OneField(
            label='Satuan',
            relation='inventory.product_unit',
            required=False,
            allow_duplicate=True,
            domain={'product': 'product'},
            compute='_compute_uom',
            depends=['product'],
            editable_computed=True,  # tetap bisa dipilih user (compute hanya autofill)
            help_text='Satuan diambil dari daftar Multi Satuan pada produk yang dipilih',
        ),
        'qty': FloatField(label='Jumlah', default=1),
        'estimated_cost': MonetaryField(label='Est. Harga', currency='IDR'),
        'total': MonetaryField(
            label='Total', currency='IDR',
            compute='_compute_total',
            depends=['qty', 'estimated_cost'],
        ),
        'processed_qty': FloatField(label='Qty Diproses', default=0, virtual=True),
        'remaining_qty': FloatField(label='Qty Belum Diproses', default=0, virtual=True),
        # Cerminan kolom "Jumlah" (qty) untuk tab Produk Status — nilainya sama
        # dengan qty baris ini, hanya beda label kolom.
        'request_qty': FloatField(label='Request Qty', default=0, virtual=True, editable_statuses=[]),
        'draft_po_qty': FloatField(label='Draft PO Qty', default=0, virtual=True, editable_statuses=[]),
        'confirmed_po_qty': FloatField(label='Konfirm PO Qty', default=0, virtual=True, editable_statuses=[]),
        'received_qty': FloatField(label='Qty Diterima', default=0, virtual=True, editable_statuses=[]),
    }

    _list_view = {
        'columns': ['product', 'uom', 'description', 'qty', 'estimated_cost', 'total'],
        'default_sort': ['id'],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Permintaan Pembelian'
        verbose_name_plural = 'Baris Permintaan Pembelian'

    def _compute_total(self):
        qty = float(self.qty or 0)
        cost = float(self.estimated_cost or 0)
        self.total = round(qty * cost, 2)

    def _compute_uom(self):
        """Satuan mengikuti produk terpilih — sumber: baris Multi Satuan produk.

        Dipicu compute endpoint saat `product` diubah di notebook (juga saat
        save). Pilihan user DIPERTAHANKAN selama satuannya masih milik produk
        yang sama; diganti hanya kalau produk berganti / satuan belum diisi.
        Produk tanpa baris Multi Satuan → satuan dikosongkan.
        """
        from core.models.inventory.product_unit import ProductUnit

        product_id = self.product_id

        # Satuan terpilih masih milik produk yang sama → pertahankan
        if self.uom_id:
            current = ProductUnit.objects.filter(pk=self.uom_id, is_deleted=False).first()
            if current is not None and (product_id is None or current.product_id == product_id):
                return

        if not product_id:
            self.uom_id = None
            return

        qs = ProductUnit.objects.filter(product_id=product_id, is_deleted=False).order_by('id')
        base_uom_id = getattr(self.product, 'uom_id', None)

        # Autofill HARUS mengikuti field Satuan di master produk: pakai baris
        # Multi Satuan yang satuannya = Satuan produk. Kalau satuan utama itu
        # belum terdaftar di tab Multi Satuan → biarkan kosong (user pilih
        # sendiri dari daftar Multi Satuan).
        target = qs.filter(uom_id=base_uom_id).first() if base_uom_id else None
        self.uom_id = target.pk if target is not None else None

    def to_record(self):
        """Override: isi processed_qty, remaining_qty + breakdown qty PO (draft/confirmed) & qty diterima dari GR."""
        data = super().to_record()

        from django.db.models import Sum, Q
        from core.models.purchase.purchase_order_line import PurchaseOrderLine

        # Semua PO line yang terhubung ke PR line ini (non-cancelled)
        po_lines = PurchaseOrderLine.objects.filter(
            purchase_request_line=self,
            is_deleted=False,
            order_id__is_deleted=False,
        ).exclude(
            order_id__status='cancelled',
        )

        agg = po_lines.aggregate(
            total=Sum('qty'),
            draft=Sum('qty', filter=Q(order_id__status='draft')),
            confirmed=Sum('qty', filter=Q(order_id__status='confirmed')),
        )

        processed_qty = float(agg['total'] or 0)
        data['processed_qty'] = processed_qty
        data['remaining_qty'] = max(float(self.qty or 0) - processed_qty, 0)
        # Request Qty = kolom "Jumlah" (qty) — dipakai di tab Produk Status
        data['request_qty'] = float(self.qty or 0)
        data['draft_po_qty'] = float(agg['draft'] or 0)
        data['confirmed_po_qty'] = float(agg['confirmed'] or 0)

        # Qty Diterima: GR status 'done' dari semua PO terkait PR line ini
        po_ids = list(po_lines.values_list('order_id', flat=True).distinct())
        if po_ids:
            from core.models.purchase.goods_receipt import GoodsReceipt
            from core.models.purchase.goods_receipt_line import GoodsReceiptLine

            gr_ids = GoodsReceipt.objects.filter(
                purchase_order_id__in=po_ids,
                is_deleted=False,
            ).values_list('pk', flat=True)

            recv_qs = GoodsReceiptLine.objects.filter(
                receipt_id__pk__in=gr_ids,
                receipt_id__status='done',
                is_deleted=False,
            )
            product_pk = self.product.pk if hasattr(self.product, 'pk') else self.product
            if product_pk:
                recv_qs = recv_qs.filter(product=product_pk)

            data['received_qty'] = float(
                recv_qs.aggregate(total=Sum('received_qty'))['total'] or 0
            )
        else:
            data['received_qty'] = 0

        return data
