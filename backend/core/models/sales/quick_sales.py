from django.db import models
from core.fields import (
    CharField, TextField, DateField, FloatField, MonetaryField,
    SelectionField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase
from core.models.accounting.tax import taxes_total_rate


class QuickSales(BaseModel):
    """Penjualan cepat — 1 dokumen menyelesaikan SO → DO → Invoice → Payment."""

    _model_name = 'sales.quick_sales'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Done', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'done',
            'label': 'Konfirmasi & Selesai',
            'icon': 'CheckCircleOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'cancel',
            'from': ['draft'],
            'to': 'cancelled',
            'label': 'Batal',
            'icon': 'StopOutlined',
        },
    ]

    # ── Document Flow ──
    _document_flow = {
        'children': [
            {
                'model': 'sales.delivery_order',
                'label': 'Pengiriman Barang',
                'icon': 'InboxOutlined',
                'source_field_in_child': 'quick_sales',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'customer': 'customer',
                },
            },
            {
                'model': 'accounting.customer_invoice',
                'label': 'Faktur',
                'icon': 'FileTextOutlined',
                'source_field_in_child': 'quick_sales',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'customer': 'customer',
                },
            },
            {
                'model': 'accounting.customer_receipt',
                'label': 'Pembayaran',
                'icon': 'DollarOutlined',
                'source_field_in_child': 'quick_sales',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'customer': 'customer',
                },
            },
        ],
    }

    _fields = {
        'sequence_id': Many2OneField(
            label='Tipe Dokumen',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen Quick Sales',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
        ),
        'pricelist': Many2OneField(
            label='Pricelist',
            relation='sales.pricelist',
            required=False,
            help_text='Pilih pricelist untuk autofill harga jual sesuai rentang qty',
        ),
        'address': TextField(label='Alamat Customer', virtual=True),
        'code': TextField(label='Kode Customer', virtual=True),
        'order_date': DateField(label='Tanggal Penjualan'),
        'payment_method': Many2OneField(
            label='Metode Pembayaran',
            relation='accounting.payment_method',
            required=True,
        ),
        'payment_date': DateField(label='Tanggal Bayar'),
        'notes': TextField(label='Catatan', chatter_show=False),
        # ── Summary fields ──
        'discount_type': SelectionField(
            label='Tipe Diskon',
            options=[('per_product', 'Per Produk'), ('global', 'Diskon Global')],
            default='per_product',
            onchange={'global_discount': 0},
            line_onchange={'discount_amount': 0, 'discount_percentage': 0},
        ),
        'discount_method': SelectionField(
            label='Metode Diskon',
            options=[('percentage', 'Diskon (%)'), ('nominal', 'Diskon (Rp)')],
            default='percentage',
            onchange={'global_discount': 0},
            line_onchange={'discount_amount': 0, 'discount_percentage': 0},
        ),
        'global_discount': FloatField(label='Diskon Global', default=0,
            compute='_compute_summary'),
        'subtotal': MonetaryField(label='Subtotal', currency='IDR',
            compute='_compute_summary', depends=['quick_sales_lines']),
        'discount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_summary', depends=['quick_sales_lines', 'discount_type', 'discount_method', 'global_discount']),
        'tax': MonetaryField(label='Pajak', currency='IDR',
            compute='_compute_summary', depends=['quick_sales_lines']),
        'grand_total': MonetaryField(label='Total', currency='IDR',
            compute='_compute_summary', depends=['quick_sales_lines', 'discount_type', 'discount_method', 'global_discount']),

        'quick_sales_lines': One2ManyField(
            label='Baris Penjualan',
            relation='sales.quick_sales.line',
            inverse_field='quick_sales_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'customer', 'order_date', 'status', 'grand_total'],
        'filters': ['status', 'customer', 'order_date'],
        'group_by': ['status', 'customer'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'customer', 'code', 'address',
                               'order_date', 'payment_method', 'payment_date', 'sequence_id', 'pricelist',
                               'discount_type', 'discount_method', 'global_discount'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'actions': [
                {'label': 'Cetak', 'color': 'green', 'action': 'print'},
                {'label': 'Konfirmasi & Selesai', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {'label': 'Batal', 'color': 'red', 'action': 'cancel', 'states': ['draft']},
            ],
            'smart_buttons': [
                {'label': 'Pengiriman Barang', 'model': 'sales.delivery_order', 'icon': 'InboxOutlined'},
                {'label': 'Faktur', 'model': 'accounting.customer_invoice', 'icon': 'FileTextOutlined'},
                {'label': 'Pembayaran', 'model': 'accounting.customer_receipt', 'icon': 'DollarOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Penjualan',
                'relation': 'quick_sales_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'taxes', 'tax_amount', 'total'],
                'summary': {
                    'columns': {'qty': 'sum', 'discount_amount': 'sum', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'tax'],
                    'compute_deps': ['discount_type', 'discount_method', 'global_discount', 'pricelist'],
                    'grand_total': 'grand_total',
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Quick Sales'
        verbose_name_plural = 'Quick Sales'

    # ── Guards ──

    def _guard_confirm(self):
        """Wajib pilih sequence sebelum konfirmasi."""
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

        # Validasi minimal 1 line
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('quick_sales_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Penjualan sebelum konfirmasi.')

    # ── Effects ──

    def _effect_confirm(self):
        """Selesaikan seluruh flow dalam 1 transaction:
        DeliveryOrder (done) → CustomerInvoice (confirmed, langsung paid) → CustomerReceipt (done, alloc penuh).
        """
        from django.db import transaction
        from core.sequence_engine import SequenceEngine
        from core.models.settings.sequence import Sequence
        from core.models.sales.delivery_order import DeliveryOrder
        from core.models.sales.delivery_order_line import DeliveryOrderLine
        from core.models.accounting.customer_invoice import CustomerInvoice
        from core.models.accounting.customer_invoice_line import CustomerInvoiceLine
        from core.models.accounting.customer_receipt import CustomerReceipt
        from core.models.accounting.customer_receipt_line import CustomerReceiptLine

        def _next_ref(model_ref):
            """Ambil active sequence + next reference, atau (None, None)."""
            seq = Sequence.objects.filter(
                model_ref=model_ref, active=True, is_deleted=False
            ).first()
            if not seq:
                return None, None
            return seq, SequenceEngine.next_by_id(seq.pk)

        # Ambil lines
        fd = self._field_descriptors.get('quick_sales_lines')
        line_model = ErpModelBase._model_registry.get(fd.relation) if fd else None
        lines = list(line_model.objects.filter(
            **{fd.inverse_field: self.pk, 'is_deleted': False}
        )) if line_model else []

        with transaction.atomic():
            # ── 1. Delivery Order (done) ──
            do_seq, do_ref = _next_ref('sales.delivery_order')
            do = DeliveryOrder.objects.create(
                quick_sales=self,
                status='done',
                delivery_date=self.order_date,
                sequence_id=do_seq,
                reference=do_ref or f'DO-QS-{self.pk}',
            )
            for line in lines:
                DeliveryOrderLine.objects.create(
                    delivery_id=do,
                    product=line.product,
                    name=line.name,
                    delivered_qty=float(line.qty or 0),
                    unit_price=line.price,
                )

            # ── 2. Customer Invoice (confirmed, full qty) ──
            inv_seq, inv_ref = _next_ref('accounting.customer_invoice')
            invoice = CustomerInvoice.objects.create(
                quick_sales=self,
                customer=self.customer,
                status='confirmed',
                invoice_date=self.order_date,
                due_date=self.payment_date,
                sequence_id=inv_seq,
                reference=inv_ref or f'INV-QS-{self.pk}',
            )
            for line in lines:
                inv_line = CustomerInvoiceLine.objects.create(
                    invoice_id=invoice,
                    product=line.product,
                    name=line.name,
                    qty=float(line.qty or 0),
                    price=line.price,
                    discount_percentage=line.discount_percentage,
                    taxes_id=getattr(line, 'taxes_id', None),
                )
            invoice._compute_summary()
            invoice.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

            # ── 3. Customer Receipt (done, alloc penuh = grand_total invoice) ──
            rcv_seq, rcv_ref = _next_ref('accounting.customer_receipt')
            total_amount = float(invoice.grand_total or 0)
            receipt = CustomerReceipt.objects.create(
                quick_sales=self,
                customer=self.customer,
                status='done',
                payment_date=self.payment_date or self.order_date,
                payment_method=self.payment_method,
                payment_ref=f'QS-{self.pk}',
                currency='IDR',
                total_amount=total_amount,
                sequence_id=rcv_seq,
                reference=rcv_ref or f'RCV-QS-{self.pk}',
            )
            CustomerReceiptLine.objects.create(
                receipt_id=receipt,
                invoice_id=invoice,
                received_amount=total_amount,
            )
            receipt._run_compute()
            receipt.save(update_fields=['total_allocation', 'remaining_amount'])

            # ── 4. Tandai invoice lunas ──
            invoice.paid_amount = total_amount
            invoice._compute_payment_summary()
            invoice.save(update_fields=['paid_amount', 'due_amount', 'payment_status'])

            # ── 5. Reference quick sales ──
            if (self.reference or '').startswith('Draft#'):
                qs_seq, qs_ref = _next_ref('sales.quick_sales')
                if qs_ref:
                    self.reference = qs_ref

    # ── Computed Fields ──

    def _compute_summary(self):
        """Compute subtotal, discount, tax, and grand_total from lines.

        Single formula untuk per-product dan global discount (pola PO):
          subtotal    = sum(qty × price)
          discount    = sum(discount_amount per line)
          tax         = sum(tax_amount per line)
          grand_total = subtotal - discount + tax
        """
        lines_data = getattr(self, '_tmp_one2many', {}).get('quick_sales_lines', [])

        if not lines_data and self.pk:
            fd = self._field_descriptors.get('quick_sales_lines')
            if fd:
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    db_lines = child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    )
                    for line in db_lines:
                        lines_data.append({
                            'qty': float(getattr(line, 'qty', 0) or 0),
                            'price': float(getattr(line, 'price', 0) or 0),
                            'product': line.product,
                            'discount_percentage': float(getattr(line, 'discount_percentage', 0) or 0),
                            'discount_amount': float(getattr(line, 'discount_amount', 0) or 0),
                            'tax_pct': taxes_total_rate(getattr(line, 'taxes_id', None)),
                        })

        # ── Recompute per-line values dari raw data ──
        computed_lines = []
        for line in lines_data:
            qty = float(line.get('qty', 0) or 0)
            price = float(line.get('price', 0) or 0)
            subtotal = qty * price

            # Product id (payload: {id}; DB: objek; else raw)
            prod = line.get('product')
            if isinstance(prod, dict):
                product_id = prod.get('id')
            elif hasattr(prod, 'pk'):
                product_id = prod.pk
            else:
                product_id = prod

            disc_pct = float(line.get('discount_percentage', 0) or 0)
            if disc_pct > 0:
                disc_amt = subtotal * (disc_pct / 100)
            else:
                disc_amt = float(line.get('discount_amount', 0) or 0)

            computed_lines.append({
                '_key': line.get('_key'),
                'qty': qty,
                'price': price,
                'product_id': product_id,
                'subtotal_raw': subtotal,
                'discount_amount': round(disc_amt, 2),
                'discount_percentage': disc_pct,
                'tax_pct': float(line.get('tax_pct', 0) or 0) or taxes_total_rate(line.get('taxes')),
                'tax_amount': 0,
                'total': 0,
            })

        discount_type = getattr(self, 'discount_type', 'per_product') or 'per_product'

        # ── Global: prorata header discount ke discount_amount tiap line ──
        if discount_type == 'global':
            global_val = float(getattr(self, 'global_discount', 0) or 0)
            disc_method = getattr(self, 'discount_method', 'percentage') or 'percentage'
            raw_all = sum(cl['subtotal_raw'] for cl in computed_lines)

            if disc_method == 'nominal':
                total_disc = global_val
            else:
                total_disc = raw_all * (global_val / 100) if raw_all > 0 else 0

            for cl in computed_lines:
                cl['discount_percentage'] = 0
                if raw_all > 0:
                    cl['discount_amount'] = round((cl['subtotal_raw'] / raw_all) * total_disc, 2)
                else:
                    cl['discount_amount'] = 0

        # ── Per-product: bersihkan stale values ──
        if discount_type == 'per_product':
            self.global_discount = 0
            disc_method = getattr(self, 'discount_method', 'percentage') or 'percentage'
            if disc_method == 'percentage':
                for cl in computed_lines:
                    if cl['discount_percentage'] == 0:
                        cl['discount_amount'] = 0
            else:  # nominal
                for cl in computed_lines:
                    cl['discount_percentage'] = 0

        # ── Sales Pricelist: autofill harga ──
        # Cocok: pricelist terpilih + product sama, qty dalam rentang
        # [min_qty, max_qty] (max kosong = tanpa batas), dan Tanggal Penjualan
        # dalam periode aktif pricelist (start..end; end kosong = aktif terus).
        # Dipakai baris dengan min_qty TERBESAR yang cocok (harga bertingkat).
        # Harga otomatis diisi hanya jika price masih harga default product.
        pricelist_id = getattr(self, 'pricelist_id', None)
        if not pricelist_id and getattr(self, 'pricelist', None):
            pricelist_id = self.pricelist.pk if hasattr(self.pricelist, 'pk') else self.pricelist
        order_date = getattr(self, 'order_date', None)
        if pricelist_id and order_date:
            from django.db.models import Q as ModelQ
            from core.models.sales.pricelist_line import SalesPricelistLine
            from core.models.inventory.product import Product
            for cl in computed_lines:
                pid = cl.get('product_id')
                qty = cl['qty']
                if not pid or qty <= 0:
                    continue
                entry = SalesPricelistLine.objects.filter(
                    pricelist_id=pricelist_id,
                    product=pid,
                    min_qty__lte=qty,
                    is_deleted=False,
                ).filter(
                    ModelQ(max_qty__isnull=True) | ModelQ(max_qty__gte=qty),
                ).filter(
                    ModelQ(pricelist_id__start_date__isnull=True) | ModelQ(pricelist_id__start_date__lte=order_date),
                    ModelQ(pricelist_id__end_date__isnull=True) | ModelQ(pricelist_id__end_date__gte=order_date),
                ).order_by('-min_qty').first()
                if not entry:
                    continue
                pl_price = float(entry.fix_price or 0)
                # Autofill price hanya jika masih harga default product
                current_price = cl.get('price')
                try:
                    default_price = float(Product.objects.get(pk=pid).price or 0)
                except Product.DoesNotExist:
                    default_price = None
                if current_price is None or (
                    default_price is not None
                    and abs(float(current_price or 0) - default_price) < 0.01
                ):
                    cl['price'] = pl_price
                    cl['subtotal_raw'] = round(qty * pl_price, 2)

        # ── Recompute tax & total (1 formula) ──
        for cl in computed_lines:
            taxable = cl['subtotal_raw'] - cl['discount_amount']
            tax_pct = cl['tax_pct']
            tax_amt = round(taxable * (tax_pct / 100), 2)
            cl['tax_amount'] = tax_amt
            cl['total'] = round(cl['subtotal_raw'] - cl['discount_amount'] + tax_amt, 2)

        # ── Summary ──
        subtotal = sum(cl['subtotal_raw'] for cl in computed_lines)
        discount_total = sum(cl['discount_amount'] for cl in computed_lines)
        tax_total = sum(cl['tax_amount'] for cl in computed_lines)
        grand_total = sum(cl['total'] for cl in computed_lines)

        self.subtotal = subtotal
        self.discount = discount_total
        self.tax = tax_total
        self.grand_total = grand_total

        # ── Store per-line computed values untuk response API ──
        self._computed_o2m_lines = {
            'quick_sales_lines': [
                {k: cl[k] for k in ('_key', 'discount_amount', 'discount_percentage', 'tax_amount', 'total', 'price')}
                for cl in computed_lines
                if cl.get('_key')
            ],
        }

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(
            model_ref='sales.quick_sales', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk

        # Kolom diskon konsisten dengan PO
        config['column_config_rules'] = {
            'quick_sales_lines': {
                'discount_percentage': {
                    'hide_when': {'discount_method': 'nominal', 'discount_type': 'global'},
                },
                'discount_amount': {
                    'readonly_when': {'discount_type': 'global'},
                    'editable_when': {'discount_method': 'nominal'},
                },
            },
        }
        config['field_config_rules'] = {
            'global_discount': {
                'hide_when': {'discount_type': 'per_product'},
                'field_props': {
                    'max': {
                        'depends_on': 'discount_method',
                        'percentage': 100,
                        'nominal': None,
                    },
                    'currency': {
                        'depends_on': 'discount_method',
                        'percentage': '%',
                        'nominal': 'IDR',
                    },
                },
            },
        }
        return config
