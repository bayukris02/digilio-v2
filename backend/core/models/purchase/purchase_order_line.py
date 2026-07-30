from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField, PercentageField,
    Many2OneField,
)
from core.model_meta import BaseModel, ErpModelBase


class PurchaseOrderLine(BaseModel):
    _model_name = 'purchase.order.line'

    _fields = {
        'order_id': Many2OneField(
            label='Purchase Order',
            relation='purchase.order',
            required=True,
        ),
        'purchase_request_line': Many2OneField(
            label='Purchase Request Line',
            relation='purchase.request.line',
            required=False,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'price'},
        ),
        'name': TextField(label='Description'),
        'qty': FloatField(label='Quantity', default=1),
        'done_qty': FloatField(label='Done Qty', default=0, virtual=True, hidden_statuses=['draft']),
        'in_receipt_qty': FloatField(label='In Receipt Qty', default=0, virtual=True, hidden_statuses=['draft']),
        'remaining_qty': FloatField(label='Remaining Qty', default=0, virtual=True, hidden_statuses=['draft']),
        'billed_qty': FloatField(label='Billed Qty', default=0, virtual=True, hidden_statuses=['draft']),
        'remaining_bill_qty': FloatField(label='Remaining Bill Qty', default=0, virtual=True, hidden_statuses=['draft']),
        'uom': CharField(label='UOM', default='pcs'),
        'price': MonetaryField(label='Unit Price', currency='IDR'),
        'discount_percentage': PercentageField(label='Disc (%)', default=0),
        'discount_amount': MonetaryField(label='Discount', currency='IDR',
            compute='_compute_total'),
        'tax_percentage': PercentageField(label='Tax (%)', default=0),
        'tax_amount': MonetaryField(label='Tax', currency='IDR', compute='_compute_total', depends=['qty', 'price', 'discount_amount', 'tax_percentage']),
        'total': MonetaryField(label='Total', currency='IDR', compute='_compute_total', depends=['qty', 'price', 'discount_amount', 'tax_amount']),
    }

    _list_view = {
        'columns': ['product', 'name', 'qty', 'uom', 'done_qty', 'in_receipt_qty', 'remaining_qty', 'price', 'discount_percentage', 'discount_amount', 'tax_percentage', 'tax_amount', 'total'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'qty', 'done_qty', 'in_receipt_qty', 'remaining_qty', 'price', 'total'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Order Line'
        verbose_name_plural = 'Purchase Order Lines'

    def _compute_total(self):
        """Compute discount, tax, and total from stored discount_amount."""
        qty = float(self.qty or 0)
        price = float(self.price or 0)
        subtotal = qty * price

        # Hitung discount: jika ada %, override stored discount_amount
        disc_pct = float(getattr(self, 'discount_percentage', 0) or 0)
        if disc_pct > 0:
            disc_amt = subtotal * (disc_pct / 100)
        else:
            disc_amt = float(self.discount_amount or 0)

        taxable = subtotal - disc_amt

        tax_pct = float(getattr(self, 'tax_percentage', 0) or 0)
        tax_amt = taxable * (tax_pct / 100)

        self.discount_amount = round(disc_amt, 2)
        self.tax_amount = round(tax_amt, 2)
        self.total = round(subtotal - disc_amt + tax_amt, 2)

    def to_record(self):
        """Override: tambah computed done_qty, in_receipt_qty & remaining_qty dari GR."""
        from django.db import models
        data = super().to_record()

        order_pk = getattr(self, 'order_id', None)
        if order_pk and hasattr(order_pk, 'pk'):
            product_pk = None
            if hasattr(self.product, 'pk'):
                product_pk = self.product.pk
            elif self.product:
                product_pk = self.product

            if product_pk:
                from core.models.purchase.goods_receipt import GoodsReceipt
                from core.models.purchase.goods_receipt_line import GoodsReceiptLine

                gr_ids = GoodsReceipt.objects.filter(
                    purchase_order=order_pk.pk if hasattr(order_pk, 'pk') else order_pk,
                    is_deleted=False,
                ).values_list('pk', flat=True)

                if gr_ids:
                    # done_qty: hanya GR status 'done' (barang beneran diterima)
                    done_agg = GoodsReceiptLine.objects.filter(
                        receipt_id__pk__in=gr_ids,
                        product=product_pk,
                        receipt_id__status='done',
                    ).aggregate(total=models.Sum('received_qty'))
                    done_qty = float(done_agg['total'] or 0)

                    # in_receipt_qty: GR status 'waiting' aja (yang masih menunggu proses)
                    in_agg = GoodsReceiptLine.objects.filter(
                        receipt_id__pk__in=gr_ids,
                        product=product_pk,
                        receipt_id__status='waiting',
                    ).aggregate(total=models.Sum('received_qty'))
                    in_receipt_qty = float(in_agg['total'] or 0)
                else:
                    done_qty = 0
                    in_receipt_qty = 0

                data['done_qty'] = done_qty
                data['in_receipt_qty'] = in_receipt_qty
                data['remaining_qty'] = max(float(self.qty or 0) - done_qty - in_receipt_qty, 0)

                # billed_qty: dari VendorBill (non-DP)
                from core.models.accounting.vendor_bill import VendorBill
                from core.models.accounting.vendor_bill_line import VendorBillLine

                bill_ids = VendorBill.objects.filter(
                    purchase_order=order_pk.pk if hasattr(order_pk, 'pk') else order_pk,
                    is_deleted=False,
                    is_down_payment=False,
                ).exclude(status='cancelled').values_list('pk', flat=True)

                if bill_ids:
                    billed_agg = VendorBillLine.objects.filter(
                        bill_id__pk__in=bill_ids,
                        product=product_pk,
                    ).aggregate(total=models.Sum('qty'))
                    billed_qty = float(billed_agg['total'] or 0)
                else:
                    billed_qty = 0

                data['billed_qty'] = billed_qty

                # ── remaining_bill_qty: tergantung bill_method ──
                from core.models.purchase.purchase_order import PurchaseOrder
                po_obj = PurchaseOrder.objects.select_related('vendor').get(
                    pk=order_pk.pk if hasattr(order_pk, 'pk') else order_pk
                )
                po_bm = po_obj.bill_method
                vendor_bm = po_obj.vendor.bill_method if po_obj.vendor else None
                bill_method = po_bm if po_bm is not None else (vendor_bm or 'on_order')
                if bill_method == 'on_receipt':
                    data['remaining_bill_qty'] = max(min(float(self.qty or 0), done_qty) - billed_qty, 0)
                else:
                    data['remaining_bill_qty'] = max(float(self.qty or 0) - billed_qty, 0)

                # ── Di global mode, override discount_amount dengan prorata ──
                if getattr(po_obj, 'discount_type', None) == 'global':
                    line_total_raw = float(self.qty or 0) * float(self.price or 0)
                    fd = po_obj._field_descriptors.get('order_lines')
                    if fd:
                        line_model_sub = ErpModelBase._model_registry.get(fd.relation)
                        if line_model_sub:
                            all_lines = line_model_sub.objects.filter(
                                **{fd.inverse_field: po_obj.pk, 'is_deleted': False}
                            )
                            raw_subtotal = sum(float(l.qty or 0) * float(l.price or 0) for l in all_lines)
                            if raw_subtotal > 0:
                                global_val = float(po_obj.global_discount or 0)
                                disc_method = po_obj.discount_method or 'percentage'
                                if disc_method == 'nominal':
                                    total_disc = global_val
                                else:
                                    total_disc = raw_subtotal * (global_val / 100)
                                prorated = round((line_total_raw / raw_subtotal) * total_disc, 2)

                                # Recompute discount_amount, tax_amount, total dgn prorata
                                orig_disc = data.get('discount_amount', 0) or 0
                                data['discount_amount'] = prorated
                                data['tax_amount'] = round((line_total_raw - prorated) * (float(getattr(self, 'tax_percentage', 0) or 0) / 100), 2)
                                data['total'] = round(line_total_raw - prorated + (data['tax_amount'] or 0), 2)

        return data
