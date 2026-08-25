from django.db import models
from core.fields import (
    CharField, TextField, FloatField, MonetaryField, PercentageField,
    Many2OneField,
)
from core.model_meta import BaseModel, ErpModelBase


class SalesOrderLine(BaseModel):
    _model_name = 'sales.order.line'

    _fields = {
        'order_id': Many2OneField(
            label='SO',
            relation='sales.order',
            required=True,
        ),
        'product': Many2OneField(
            label='Product',
            relation='inventory.product',
            required=True,
            autofill={'uom': 'uom', 'name': 'name', 'price': 'price'},
        ),
        'name': TextField(label='Deskripsi'),
        'qty': FloatField(label='Jumlah', default=1),
        'delivered_qty': FloatField(
            label='Qty Terkirim', default=0,
            virtual=True, hidden_statuses=['draft'],
        ),
        'in_delivery_qty': FloatField(
            label='Qty Dalam Pengiriman', default=0,
            virtual=True, hidden_statuses=['draft'],
        ),
        'remaining_qty': FloatField(
            label='Qty Sisa', default=0,
            virtual=True, hidden_statuses=['draft'],
        ),
        'billed_qty': FloatField(
            label='Qty Ditagih', default=0,
            virtual=True, hidden_statuses=['draft'],
        ),
        'remaining_bill_qty': FloatField(
            label='Qty Sisa Tagihan', default=0,
            virtual=True, hidden_statuses=['draft'],
        ),
        'uom': CharField(label='UOM', default='pcs'),
        'price': MonetaryField(label='Harga Satuan', currency='IDR'),
        'discount_percentage': PercentageField(label='Diskon (%)', default=0),
        'discount_amount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_total'),
        'global_discount_amount': MonetaryField(label='Diskon Global', currency='IDR',
            virtual=True),
        'tax_percentage': PercentageField(label='Pajak (%)', default=0),
        'tax_amount': MonetaryField(label='Pajak', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'tax_percentage']),
        'total': MonetaryField(
            label='Total', currency='IDR',
            compute='_compute_total', depends=['qty', 'price', 'discount_percentage', 'tax_percentage'],
        ),
    }

    _list_view = {
        'columns': ['product', 'name', 'qty', 'uom', 'delivered_qty',
                    'in_delivery_qty', 'remaining_qty', 'price', 'total'],
        'default_sort': ['id'],
    }

    _form_view = {
        'header': {
            'fields': ['product', 'qty', 'delivered_qty', 'in_delivery_qty',
                       'remaining_qty', 'price', 'total'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Baris Sales Order'
        verbose_name_plural = 'Baris Sales Order'

    def _compute_total(self):
        """Compute discount, tax, and total from qty/price + stored discount_amount."""
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

        # Kurangi global_discount_amount (virtual field, mungkin diset via frontend/API)
        gda = float(getattr(self, 'global_discount_amount', 0) or 0)
        self.total = round(subtotal - disc_amt - gda + tax_amt, 2)

    def to_record(self):
        """Override: tambah computed delivered_qty, in_delivery_qty,
        remaining_qty dari DO, dan billed_qty/remaining_bill_qty dari Invoice."""
        data = super().to_record()

        order_pk = getattr(self, 'order_id', None)
        if order_pk and hasattr(order_pk, 'pk'):
            product_pk = None
            if hasattr(self.product, 'pk'):
                product_pk = self.product.pk
            elif self.product:
                product_pk = self.product

            if product_pk:
                from core.models.sales.delivery_order import DeliveryOrder
                from core.models.sales.delivery_order_line import DeliveryOrderLine

                do_ids = DeliveryOrder.objects.filter(
                    sales_order=order_pk.pk if hasattr(order_pk, 'pk') else order_pk,
                    is_deleted=False,
                ).values_list('pk', flat=True)

                if do_ids:
                    # delivered_qty: hanya DO status 'done'
                    done_agg = DeliveryOrderLine.objects.filter(
                        delivery_id__pk__in=do_ids,
                        product=product_pk,
                        delivery_id__status='done',
                    ).aggregate(total=models.Sum('delivered_qty'))
                    delivered_qty = float(done_agg['total'] or 0)

                    # in_delivery_qty: DO status 'waiting'
                    in_agg = DeliveryOrderLine.objects.filter(
                        delivery_id__pk__in=do_ids,
                        product=product_pk,
                        delivery_id__status='waiting',
                    ).aggregate(total=models.Sum('delivered_qty'))
                    in_delivery_qty = float(in_agg['total'] or 0)
                else:
                    delivered_qty = 0
                    in_delivery_qty = 0

                data['delivered_qty'] = delivered_qty
                data['in_delivery_qty'] = in_delivery_qty
                data['remaining_qty'] = max(
                    float(self.qty or 0) - delivered_qty - in_delivery_qty, 0
                )

                # billed_qty: dari CustomerInvoice (non-DP)
                from core.models.accounting.customer_invoice import CustomerInvoice
                from core.models.accounting.customer_invoice_line import CustomerInvoiceLine

                inv_ids = CustomerInvoice.objects.filter(
                    sales_order=order_pk.pk if hasattr(order_pk, 'pk') else order_pk,
                    is_deleted=False,
                    is_down_payment=False,
                ).exclude(status='cancelled').values_list('pk', flat=True)

                if inv_ids:
                    billed_agg = CustomerInvoiceLine.objects.filter(
                        invoice_id__pk__in=inv_ids,
                        product=product_pk,
                    ).aggregate(total=models.Sum('qty'))
                    billed_qty = float(billed_agg['total'] or 0)
                else:
                    billed_qty = 0

                data['billed_qty'] = billed_qty
                data['remaining_bill_qty'] = max(
                    float(self.qty or 0) - billed_qty, 0
                )

                # ── global_discount_amount: alokasi proporsional per line ──
                data['global_discount_amount'] = 0
                from core.models.sales.sales_order import SalesOrder
                so_obj = SalesOrder.objects.get(
                    pk=order_pk.pk if hasattr(order_pk, 'pk') else order_pk
                )
                if getattr(so_obj, 'discount_type', None) == 'global':
                    line_total = float(self.qty or 0) * float(self.price or 0)
                    fd = so_obj._field_descriptors.get('order_lines')
                    if fd:
                        line_model_sub = ErpModelBase._model_registry.get(fd.relation)
                        if line_model_sub:
                            all_lines = line_model_sub.objects.filter(
                                **{fd.inverse_field: so_obj.pk, 'is_deleted': False}
                            )
                            raw_subtotal = sum(float(l.qty or 0) * float(l.price or 0) for l in all_lines)
                            if raw_subtotal > 0:
                                global_val = float(so_obj.global_discount or 0)
                                disc_method = so_obj.discount_method or 'percentage'
                                if disc_method == 'nominal':
                                    total_disc = global_val
                                else:
                                    total_disc = raw_subtotal * (global_val / 100)
                                data['global_discount_amount'] = round((line_total / raw_subtotal) * total_disc, 2)

        return data
