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
        'estimated_cost': MonetaryField(label='Perkiraan Biaya', currency='IDR'),
        'total': MonetaryField(
            label='Total', currency='IDR',
            compute='_compute_total',
            depends=['qty', 'estimated_cost'],
        ),
        'processed_qty': FloatField(label='Qty Diproses', default=0, virtual=True),
        'remaining_qty': FloatField(label='Qty Sisa', default=0, virtual=True),
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
        """Override: isi processed_qty + remaining_qty dari PurchaseOrder terkait."""
        data = super().to_record()

        from django.db.models import Sum
        from core.models.purchase.purchase_order_line import PurchaseOrderLine

        agg = PurchaseOrderLine.objects.filter(
            purchase_request_line=self,
            is_deleted=False,
            order_id__is_deleted=False,
        ).exclude(
            order_id__status='cancelled',
        ).aggregate(total=Sum('qty'))

        processed_qty = float(agg['total'] or 0)
        data['processed_qty'] = processed_qty
        data['remaining_qty'] = max(float(self.qty or 0) - processed_qty, 0)

        return data
