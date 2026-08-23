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
        'qty': FloatField(label='Jumlah', default=1),
        'estimated_cost': MonetaryField(label='Est. Harga', currency='IDR'),
        'total': MonetaryField(
            label='Total', currency='IDR',
            compute='_compute_total',
            depends=['qty', 'estimated_cost'],
        ),
        'processed_qty': FloatField(label='Qty Diproses', default=0, virtual=True),
        'remaining_qty': FloatField(label='Qty Sisa', default=0, virtual=True),
        'draft_po_qty': FloatField(label='Draft PO Qty', default=0, virtual=True, editable_statuses=[]),
        'confirmed_po_qty': FloatField(label='Konfirm PO Qty', default=0, virtual=True, editable_statuses=[]),
        'received_qty': FloatField(label='Qty Diterima', default=0, virtual=True, editable_statuses=[]),
    }

    _list_view = {
        'columns': ['product', 'description', 'qty', 'estimated_cost', 'total'],
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
