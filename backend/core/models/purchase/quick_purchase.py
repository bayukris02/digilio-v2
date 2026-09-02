from django.db import models
from core.fields import (
    CharField, TextField, DateField, FloatField, MonetaryField,
    SelectionField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase
from core.models.accounting.tax import taxes_total_rate


class QuickPurchase(BaseModel):
    """Pembelian cepat — 1 dokumen menyelesaikan PO → GR → Bill → Payment."""

    _model_name = 'purchase.quick_purchase'
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
                'model': 'purchase.goods_receipt',
                'label': 'Penerimaan Barang',
                'icon': 'InboxOutlined',
                'source_field_in_child': 'quick_purchase',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'vendor': 'vendor',
                },
            },
            {
                'model': 'accounting.vendor_bill',
                'label': 'Tagihan',
                'icon': 'FileTextOutlined',
                'source_field_in_child': 'quick_purchase',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'vendor': 'vendor',
                },
            },
            {
                'model': 'accounting.vendor_payment',
                'label': 'Pembayaran',
                'icon': 'DollarOutlined',
                'source_field_in_child': 'quick_purchase',
                'state_conditions': {
                    'allowed_parent_states': ['done'],
                },
                'mapping': {
                    'vendor': 'vendor',
                },
            },
        ],
    }

    _fields = {
        'sequence_id': Many2OneField(
            label='Tipe Dokumen',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen Quick Purchase',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
            autofill={'address': 'address', 'code': 'code', 'bill_method': 'bill_method'},
        ),
        'address': TextField(label='Alamat Vendor', virtual=True),
        'code': TextField(label='Kode Vendor', virtual=True),
        'order_date': DateField(label='Tanggal Pembelian'),
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
            compute='_compute_summary', depends=['quick_purchase_lines']),
        'discount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_summary', depends=['quick_purchase_lines', 'discount_type', 'discount_method', 'global_discount']),
        'tax': MonetaryField(label='Pajak', currency='IDR',
            compute='_compute_summary', depends=['quick_purchase_lines']),
        'grand_total': MonetaryField(label='Total', currency='IDR',
            compute='_compute_summary', depends=['quick_purchase_lines', 'discount_type', 'discount_method', 'global_discount']),

        'quick_purchase_lines': One2ManyField(
            label='Baris Pembelian',
            relation='purchase.quick_purchase.line',
            inverse_field='quick_purchase_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'vendor', 'order_date', 'status', 'grand_total'],
        'filters': ['status', 'vendor', 'order_date'],
        'group_by': ['status', 'vendor'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'vendor', 'code', 'address',
                               'order_date', 'payment_method', 'payment_date', 'sequence_id',
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
                {'label': 'Penerimaan Barang', 'model': 'purchase.goods_receipt', 'icon': 'InboxOutlined'},
                {'label': 'Tagihan', 'model': 'accounting.vendor_bill', 'icon': 'FileTextOutlined'},
                {'label': 'Pembayaran', 'model': 'accounting.vendor_payment', 'icon': 'DollarOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Pembelian',
                'relation': 'quick_purchase_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'taxes', 'tax_amount', 'total'],
                'summary': {
                    'columns': {'qty': 'sum', 'discount_amount': 'sum', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'tax'],
                    'compute_deps': ['discount_type', 'discount_method', 'global_discount'],
                    'grand_total': 'grand_total',
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Quick Purchase'
        verbose_name_plural = 'Quick Purchases'

    # ── Guards ──

    def _guard_confirm(self):
        """Wajib pilih sequence sebelum konfirmasi."""
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

        # Validasi minimal 1 line
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        fd = self._field_descriptors.get('quick_purchase_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Baris Pembelian sebelum konfirmasi.')

    # ── Effects ──

    def _effect_confirm(self):
        """Selesaikan seluruh flow dalam 1 transaction:
        GoodsReceipt (done) → VendorBill (confirmed, langsung paid) → VendorPayment (done, alloc penuh).
        """
        from django.db import transaction
        from core.sequence_engine import SequenceEngine
        from core.models.settings.sequence import Sequence
        from core.models.purchase.goods_receipt import GoodsReceipt
        from core.models.purchase.goods_receipt_line import GoodsReceiptLine
        from core.models.accounting.vendor_bill import VendorBill
        from core.models.accounting.vendor_bill_line import VendorBillLine
        from core.models.accounting.vendor_payment import VendorPayment
        from core.models.accounting.vendor_payment_line import VendorPaymentLine

        def _next_ref(model_ref):
            """Ambil active sequence + next reference, atau (None, None)."""
            seq = Sequence.objects.filter(
                model_ref=model_ref, active=True, is_deleted=False
            ).first()
            if not seq:
                return None, None
            return seq, SequenceEngine.next_by_id(seq.pk)

        # Ambil lines
        fd = self._field_descriptors.get('quick_purchase_lines')
        line_model = ErpModelBase._model_registry.get(fd.relation) if fd else None
        lines = list(line_model.objects.filter(
            **{fd.inverse_field: self.pk, 'is_deleted': False}
        )) if line_model else []

        with transaction.atomic():
            # ── 1. Goods Receipt (done) ──
            gr_seq, gr_ref = _next_ref('purchase.goods_receipt')
            gr = GoodsReceipt.objects.create(
                quick_purchase=self,
                status='done',
                receipt_date=self.order_date,
                sequence_id=gr_seq,
                reference=gr_ref or f'GR-QP-{self.pk}',
            )
            for line in lines:
                GoodsReceiptLine.objects.create(
                    receipt_id=gr,
                    product=line.product,
                    name=line.name,
                    received_qty=float(line.qty or 0),
                    unit_price=line.price,
                )

            # ── 2. Vendor Bill (confirmed, full qty) ──
            bill_seq, bill_ref = _next_ref('accounting.vendor_bill')
            bill = VendorBill.objects.create(
                quick_purchase=self,
                vendor=self.vendor,
                status='confirmed',
                bill_date=self.order_date,
                due_date=self.payment_date,
                sequence_id=bill_seq,
                reference=bill_ref or f'B-QP-{self.pk}',
            )
            for line in lines:
                bill_line = VendorBillLine.objects.create(
                    bill_id=bill,
                    product=line.product,
                    name=line.name,
                    qty=float(line.qty or 0),
                    price=line.price,
                    discount_percentage=line.discount_percentage,
                    taxes_id=getattr(line, 'taxes_id', None),
                )
            bill._compute_summary()
            bill.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

            # ── 3. Vendor Payment (done, alloc penuh = grand_total bill) ──
            pay_seq, pay_ref = _next_ref('accounting.vendor_payment')
            total_amount = float(bill.grand_total or 0)
            pay = VendorPayment.objects.create(
                quick_purchase=self,
                vendor=self.vendor,
                status='done',
                payment_date=self.payment_date or self.order_date,
                payment_method=self.payment_method,
                payment_ref=f'QP-{self.pk}',
                currency='IDR',
                total_amount=total_amount,
                sequence_id=pay_seq,
                reference=pay_ref or f'P-QP-{self.pk}',
            )
            VendorPaymentLine.objects.create(
                payment_id=pay,
                bill_id=bill,
                paid_amount=total_amount,
            )
            pay._run_compute()
            pay.save(update_fields=['total_allocation', 'remaining_amount'])

            # ── 4. Tandai bill lunas ──
            bill.paid_amount = total_amount
            bill._compute_payment_summary()
            bill.save(update_fields=['paid_amount', 'due_amount', 'payment_status'])

            # ── 5. Reference quick purchase ──
            if (self.reference or '').startswith('Draft#'):
                qp_seq, qp_ref = _next_ref('purchase.quick_purchase')
                if qp_ref:
                    self.reference = qp_ref

    # ── Computed Fields ──

    def _compute_summary(self):
        """Compute subtotal, discount, tax, and grand_total from lines.

        Single formula untuk per-product dan global discount (pola PO):
          subtotal    = sum(qty × price)
          discount    = sum(discount_amount per line)
          tax         = sum(tax_amount per line)
          grand_total = subtotal - discount + tax
        """
        lines_data = getattr(self, '_tmp_one2many', {}).get('quick_purchase_lines', [])

        if not lines_data and self.pk:
            fd = self._field_descriptors.get('quick_purchase_lines')
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

            disc_pct = float(line.get('discount_percentage', 0) or 0)
            if disc_pct > 0:
                disc_amt = subtotal * (disc_pct / 100)
            else:
                disc_amt = float(line.get('discount_amount', 0) or 0)

            computed_lines.append({
                '_key': line.get('_key'),
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
            'quick_purchase_lines': [
                {k: cl[k] for k in ('_key', 'discount_amount', 'discount_percentage', 'tax_amount', 'total')}
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
            model_ref='purchase.quick_purchase', active=True, is_deleted=False
        ).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk

        # Kolom diskon konsisten dengan PO
        config['column_config_rules'] = {
            'quick_purchase_lines': {
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
