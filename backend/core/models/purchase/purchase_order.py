from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField, PercentageField,
    SelectionField, BooleanField, IntegerField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase
from core.models.purchase.goods_receipt import GoodsReceipt
from core.models.purchase.goods_receipt_line import GoodsReceiptLine


class PurchaseOrder(BaseModel):
    _model_name = 'purchase.order'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
        'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Done', 'color': 'success'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'confirmed',
            'label': 'Confirm',
            'icon': 'CheckOutlined',
            'guard': '_guard_confirm',
            'effect': '_effect_confirm',
        },
        {
            'name': 'mark_done',
            'from': ['confirmed'],
            'to': 'done',
            'label': 'Mark Done',
            'icon': 'CheckCircleOutlined',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
            'guard': '_guard_cancel',
        },
    ]

    # ── Document Flow ──
    _document_flow = {
        'children': [
            {
                'model': 'purchase.goods_receipt',
                'label': 'Goods Receipt',
                'icon': 'InboxOutlined',
                'source_field_in_child': 'purchase_order',
                'state_conditions': {
                    'allowed_parent_states': ['confirmed', 'done'],
                    'blocked_child_states_for_parent_cancel': ['draft', 'waiting', 'done'],
                },
                'mapping': {
                    'purchase_order': 'id',
                },
                'constraints': {
                    'max_per_parent': 0,
                    'unique_per_parent': False,
                },
            },
            {
                'model': 'accounting.vendor_bill',
                'label': 'Tagihan',
                'icon': 'FileTextOutlined',
                'source_field_in_child': 'purchase_order',
                'state_conditions': {
                    'allowed_parent_states': ['confirmed', 'done'],
                    'blocked_child_states_for_parent_cancel': ['draft', 'confirmed', 'done'],
                },
                'mapping': {
                    'vendor': 'vendor',
                    'purchase_order': 'id',
                },
                'constraints': {
                    'max_per_parent': 0,
                    'unique_per_parent': False,
                },
            },
        ],
    }

    _fields = {
        'sequence_id': Many2OneField(
            label='Order Type',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen (PO Local / PO Import, dll)',
        ),
        'reference': CharField(label='Reference', required=True, editable_statuses=[], placeholder='Automatic'),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
            autofill={'address': 'address', 'code': 'code', 'bill_method': 'bill_method'},
        ),
        'address': TextField(label='Alamat Vendor', virtual=True),
        'code': TextField(label='Kode Vendor', virtual=True),
        'description': TextField(label='Description'),
        'notes': TextField(label='Notes', chatter_show=False),
        'order_date': DateField(label='Order Date'),
        'expected_date': DateField(label='Expected Date'),
        'category': SelectionField(
            label='Category',
            options=['Raw Material', 'Finished Good', 'Service', 'Asset'],
        ),
        'priority': SelectionField(
            label='Priority',
            options=[
                ('low', 'Low'),
                ('medium', 'Medium'),
                ('high', 'High'),
            ],
        ),
        'is_active': BooleanField(label='Active', default=True, chatter_show=False),
        # ── Summary fields ──
        'discount_type': SelectionField(
            label='Tipe Diskon',
            options=[('per_product', 'Per Product'), ('global', 'Global Discount')],
            default='per_product',
            onchange={'global_discount': 0},
        ),
        'discount_method': SelectionField(
            label='Metode Diskon',
            options=[('percentage', 'Discount (%)'), ('nominal', 'Discount (Rp)')],
            default='percentage',
            onchange={'global_discount': 0},
        ),
        'global_discount': FloatField(label='Global Discount', default=0,
            compute='_compute_summary'),
        'bill_method': SelectionField(
            label='Metode Tagihan',
            options=[('on_order', 'On Order'), ('on_receipt', 'On Receipt')],
            default=None,
            help_text='Default mengikuti setting Vendor',
        ),
        'discount': MonetaryField(label='Discount', currency='IDR',
            compute='_compute_summary', depends=['order_lines', 'discount_type', 'discount_method', 'global_discount']),
        'tax': MonetaryField(label='Tax', currency='IDR',
            compute='_compute_summary', depends=['order_lines']),
        'subtotal': MonetaryField(label='Subtotal', currency='IDR',
            compute='_compute_summary', depends=['order_lines']),
        'grand_total': MonetaryField(label='Grand Total', currency='IDR',
            compute='_compute_summary', depends=['order_lines', 'discount_type', 'discount_method', 'global_discount']),

        # ── Down Payment & Bill Info ──
        'dp_amount': MonetaryField(
            label='DP Amount', currency='IDR',
            compute='_compute_dp_info', depends=[],
            virtual=True,
        ),
        'due_amount': MonetaryField(
            label='Unbilled Amount', currency='IDR',
            compute='_compute_dp_info', depends=[],
            virtual=True,
        ),

        'order_lines': One2ManyField(
            label='Order Lines',
            relation='purchase.order.line',
            inverse_field='order_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'sequence_id', 'vendor', 'order_date', 'status'],
        'filters': ['status', 'category', 'order_date'],
        'group_by': ['status', 'category'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': [ 'reference', 'vendor', 'code', 'address', 
                               'order_date', 'expected_date',  'sequence_id',
                               'discount_type', 'discount_method', 'global_discount'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['bill_method', 'notes', 'priority'],
                },
            ],
            'actions': [
                {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {
                    'label': 'Terima Barang',
                    'icon': 'InboxOutlined',
                    'color': 'primary',
                    'action': 'receive_goods',
                    'states': ['confirmed'],
                    'wizard': {
                        'title': 'Penerimaan Barang',
                        'modes': [
                            {'value': 'save_draft', 'label': '📄 Buat Draft Dokumen', 'icon': 'FileAddOutlined'},
                            {'value': 'confirm', 'label': '✅ Konfirm Penerimaan', 'icon': 'CheckCircleOutlined'},
                        ],
                        'line_selection': {
                            'relation': 'order_lines',
                            'columns': ['product', 'qty', 'done_qty', 'in_receipt_qty', 'remaining_qty'],
                            'show_for_modes': ['save_draft', 'confirm'],
                        },
                    },
                },
                {
                    'label': 'Buat Tagihan',
                    'icon': 'FileTextOutlined',
                    'color': 'primary',
                    'action': 'create_bill',
                    'states': ['confirmed', 'done'],
                    'wizard': {
                        'title': 'Buat Tagihan',
                        'modes': [
                            {'value': 'bill_all', 'label': '📄 Tagihan Regular', 'icon': 'FileTextOutlined'},
                            {'value': 'bill_dp', 'label': '💵 Down Payment', 'icon': 'DollarOutlined',
                             'inputs': [
                                 {'key': 'dp_value', 'label': 'DP', 'type': 'number', 'default': 0, 'min': 0},
                                 {'key': 'dp_mode', 'label': 'Mode', 'type': 'selection',
                                  'options': [{'value': 'percentage', 'label': '%'}, {'value': 'nominal', 'label': 'Rp'}],
                                  'default': 'percentage'},
                             ]},
                        ],
                        'line_selection': {
                            'relation': 'order_lines',
                            'columns': ['product', 'qty', 'billed_qty', 'remaining_bill_qty'],
                            'show_for_modes': ['bill_all'],
                            'qty_label': 'Bill Qty',
                        },
                    },
                },
                {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'confirmed']},
            ],
            'smart_buttons': [
                {'label': 'Receipt', 'model': 'purchase.goods_receipt', 'icon': 'InboxOutlined'},
                {'label': 'Bill', 'model': 'accounting.vendor_bill', 'icon': 'FileTextOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Order Lines',
                'relation': 'order_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'tax_percentage', 'tax_amount', 'total'],
                'summary': {
                    'columns': {'qty': 'sum', 'discount_amount': 'sum', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'tax'],
                    'compute_deps': ['discount_type', 'discount_method', 'global_discount'],
                    'grand_total': 'grand_total',
                    'after_grand_total': ['due_amount'],
                    'child_details': {
                        'label': 'Down Payments & Bills',
                        'data_key': '_bill_details',
                        'model': 'accounting.vendor_bill',
                    },
                },
            },
            {
                'key': 'penerimaan_barang',
                'label': 'Penerimaan Barang',
                'relation': 'order_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'done_qty', 'in_receipt_qty', 'remaining_qty', 'billed_qty'],
                'read_only': True,
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    # ── Guards ──

    def _guard_confirm(self):
        """Wajib pilih sequence sebelum konfirmasi."""
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

        # Validasi minimal 1 order line
        if not self.pk:
            raise ValueError('Record belum disimpan.')
        from core.model_meta import ErpModelBase
        fd = self._field_descriptors.get('order_lines')
        if fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                count = child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ).count()
                if count == 0:
                    raise ValueError('Minimal harus ada 1 Order Line sebelum konfirmasi.')

    def _guard_cancel(self):
        """Prevent cancel if children are active."""
        can_cancel, msg = self._can_cancel()
        if not can_cancel:
            raise ValueError(msg)

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    # ── Computed Fields ──

    def _compute_summary(self):
        """Compute subtotal, discount, tax, and grand_total from order lines.

        Single formula for both per-product and global discount:
          subtotal    = sum(qty × price)
          discount    = sum(discount_amount per line)  — includes prorated GDA in global mode
          tax         = sum(tax_amount per line)
          grand_total = subtotal - discount + tax

        Global discount: prorated directly into discount_amount per line.
        """
        lines_data = getattr(self, '_tmp_one2many', {}).get('order_lines', [])

        # Jika tidak ada data tmp, load dari DB
        if not lines_data and self.pk:
            fd = self._field_descriptors.get('order_lines')
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
                            'tax_percentage': float(getattr(line, 'tax_percentage', 0) or 0),
                        })

        # ── Recompute per-line values dari raw data ──
        computed_lines = []
        for line in lines_data:
            qty = float(line.get('qty', 0) or 0)
            price = float(line.get('price', 0) or 0)
            subtotal = qty * price

            # Line-level discount
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
                'tax_percentage': float(line.get('tax_percentage', 0) or 0),
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

            # Reset & prorata
            for cl in computed_lines:
                cl['discount_percentage'] = 0
                if raw_all > 0:
                    cl['discount_amount'] = round((cl['subtotal_raw'] / raw_all) * total_disc, 2)
                else:
                    cl['discount_amount'] = 0

        # ── Per-product: bersihkan stale values ──
        # Saat pindah dari global ke per_product + %, frontend line items masih
        # bawa discount_amount=prorata. Karena di mode % nilai discount_amount
        # harus berasal dari discount_percentage, kita reset ke 0 jika disc%=0.
        # (Menangani mode switch global→per_product tanpa perlu compare DB)
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
                    cl['discount_amount'] = 0
                    

        # ── Recompute tax & total (1 formula untuk semua mode) ──
        for cl in computed_lines:
            taxable = cl['subtotal_raw'] - cl['discount_amount']
            tax_pct = cl['tax_percentage']
            tax_amt = round(taxable * (tax_pct / 100), 2)
            cl['tax_amount'] = tax_amt
            cl['total'] = round(cl['subtotal_raw'] - cl['discount_amount'] + tax_amt, 2)

        # ── Summary (1 formula) ──
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
            'order_lines': [
                {k: cl[k] for k in ('_key', 'discount_amount', 'discount_percentage', 'tax_amount', 'total')}
                for cl in computed_lines
                if cl.get('_key')
            ],
        }

    @classmethod
    def get_model_config(cls):
        '''Override: inject default sequence_id (Order Type) & column config rules.'''
        config = super().get_model_config()
        # Lazy import untuk hindari circular import
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='purchase.order', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk

        # -- Generic column config rules untuk frontend --
        # Memberi tahu frontend kolom mana yg di-hide/readonly berdasarkan field value
        # tanpa hardcode nama field di ModelFormPage.tsx
        config['column_config_rules'] = {
            'order_lines': {
                'discount_percentage': {
                    'hide_when': {'discount_method': 'nominal', 'discount_type': 'global'},
                },
                'discount_amount': {
                    'readonly_when': {'discount_type': 'global'},
                    'editable_when': {'discount_method': 'nominal'},
                },
            },
        }

        # -- Field config rules untuk form fields --
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

    def to_record(self):
        """Override: trigger compute & tambah bill_details untuk summary."""
        self._compute_dp_info()
        data = super().to_record()

        # Tambah daftar bill (DP + Regular) untuk render di summary
        from core.models.accounting.vendor_bill import VendorBill
        bills = VendorBill.objects.filter(
            purchase_order=self.pk,
            is_deleted=False,
        ).exclude(status='cancelled').order_by('pk')
        data['_bill_details'] = []
        for bill in bills:
            # Recompute agar grand_total sesuai logika terbaru (termasuk DP)
            bill._run_compute()
            bill.save(update_fields=bill.get_computed_fields())
            data['_bill_details'].append({
                'id': bill.pk,
                'label': 'DP Bill' if bill.is_down_payment else 'Bill',
                'ref': bill.reference or f'#{bill.pk}',
                'amount': float(bill.grand_total or 0),
            })

        # bill_method: jika None di PO, tampilkan dari Vendor
        if data.get('bill_method') is None:
            vendor_bm = getattr(self.vendor, 'bill_method', None) if getattr(self, 'vendor', None) else None
            data['bill_method'] = vendor_bm or 'on_order'

        return data

    def _compute_dp_info(self):
        """Cari DP bill & hitung dp_amount, due_amount."""
        from core.models.accounting.vendor_bill import VendorBill
        bills = VendorBill.objects.filter(
            purchase_order=self.pk,
            is_deleted=False,
        ).exclude(status='cancelled')

        total_billed = sum(float(b.grand_total or 0) for b in bills)
        dp_bill = bills.filter(is_down_payment=True).first()
        self.dp_amount = dp_bill.grand_total or 0 if dp_bill else 0
        self.due_amount = max(float(self.grand_total or 0) - total_billed, 0)

    # ── Legacy Actions (not state transitions) ──

    def _action_receive_goods(self, data=None):
        """Buat Goods Receipt + copy lines dari PO, lalu open form GR.
        
        data: dict dari frontend wizard — {mode, selected_lines}
          mode = save_draft | confirm
            save_draft → GR status = waiting (draft)
            confirm   → GR status = done
          selected_lines = [{id, qty}, ...] — selalu dikirim dari frontend,
            semua line = ALL, sebagian = PARTIAL (dari checklist user)
        """
        from django.db import transaction

        mode = (data or {}).get('mode', 'save_draft')
        gr_status = 'done' if mode == 'confirm' else 'waiting'

        # selected_lines: [{id: line_id, qty: received_qty}, ...]
        selected_lines_raw = (data or {}).get('selected_lines')
        qty_map = {}
        selected_ids_set = set()
        if selected_lines_raw and isinstance(selected_lines_raw, list):
            for item in selected_lines_raw:
                lid = item.get('id')
                if lid is not None:
                    qty_map[int(lid)] = float(item.get('qty', 0) or 0)
                    selected_ids_set.add(int(lid))

        # Dapatkan child config dari _document_flow
        child_cfg = self._get_child_flow('purchase.goods_receipt')
        if not child_cfg:
            return {'error': 'Child flow configuration for goods_receipt not found'}

        # ── Validasi qty sebelum transaction ──
        po_lines_fd = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
        lines_qs_for_validation = None
        if po_lines_fd:
            line_model = ErpModelBase._model_registry.get(po_lines_fd.relation)
            if line_model:
                lines_qs_for_validation = line_model.objects.filter(
                    **{po_lines_fd.inverse_field: self.pk, 'is_deleted': False}
                )
                if selected_ids_set:
                    lines_qs_for_validation = lines_qs_for_validation.filter(pk__in=selected_ids_set)

                from django.db.models import Sum as ModelSum

                for line in lines_qs_for_validation:
                    received_qty = qty_map.get(line.pk, float(line.qty or 0))
                    prod_name = line.name or str(line.product or 'Produk')

                    if received_qty <= 0:
                        return {'error': f'"{prod_name}": qty diterima harus lebih dari 0.'}

                    # over-receiving
                    existing_qty = float(
                        GoodsReceiptLine.objects.filter(
                            product=line.product,
                            receipt_id__purchase_order=self,
                            receipt_id__is_deleted=False,
                            receipt_id__status__in=['done', 'waiting'],
                            is_deleted=False,
                        ).aggregate(total=ModelSum('received_qty'))['total'] or 0
                    )
                    if existing_qty + received_qty > float(line.qty or 0):
                        remaining = max(float(line.qty or 0) - existing_qty, 0)
                        return {
                            'error': (
                                f'"{prod_name}": qty diterima ({received_qty:.0f}) '
                                f'melebihi sisa pesanan ({remaining:.0f}). '
                                f'Sudah diterima {existing_qty:.0f} dari {float(line.qty or 0):.0f}.'
                            )
                        }

        with transaction.atomic():
            # Apply mapping dari parent → child via _run_child_mapping
            child_data = self._run_child_mapping(child_cfg)

            # Set source field (purchase_order)
            source_field = child_cfg.get('source_field_in_child', 'purchase_order')
            child_data[source_field] = self

            # Set status sesuai mode
            child_data['status'] = gr_status

            # Buat GR
            gr = GoodsReceipt.objects.create(**child_data)

            # Auto-assign sequence + reference untuk GR
            from core.models.settings.sequence import Sequence
            from core.sequence_engine import SequenceEngine
            gr_seq = Sequence.objects.filter(
                model_ref='purchase.goods_receipt', active=True
            ).first()
            if gr_seq:
                gr.sequence_id = gr_seq
                gr.reference = SequenceEngine.next_by_id(gr_seq.pk)
                gr.save(update_fields=['sequence_id', 'reference'])

            # Copy PO lines → GR lines (hanya yang dicentang)
            if lines_qs_for_validation is not None:
                for line in lines_qs_for_validation:
                    received_qty = qty_map.get(line.pk, float(line.qty or 0))

                    GoodsReceiptLine.objects.create(
                            receipt_id=gr,
                            product=line.product,
                            name=line.name,
                            received_qty=received_qty,
                            unit_price=line.price,
                        )

        mode_label = 'draft dibuat' if mode == 'save_draft' else 'diterima'
        return {
            '_action_type': 'open_record',
            'model': 'purchase.goods_receipt',
            'record_id': gr.pk,
            'message': f'Goods Receipt berhasil {mode_label}',
        }

    def _action_create_bill(self, data=None):
        """Buat Vendor Bill + copy lines dari PO, lalu open form Bill.

        data: dict dari frontend wizard — {mode, selected_lines, dp_percentage, dp_nominal}
          mode = bill_all | bill_dp_pct | bill_dp_nominal
          selected_lines = [{id, qty}, ...] untuk mode dengan line selection
        """
        from django.db import transaction
        from core.models.accounting.vendor_bill import VendorBill
        from core.models.accounting.vendor_bill_line import VendorBillLine
        from core.models.settings.sequence import Sequence

        def _set_default_sequence(bill_obj):
            """Set sequence_id ke active sequence untuk accounting.vendor_bill."""
            seq = Sequence.objects.filter(
                model_ref='accounting.vendor_bill', active=True, is_deleted=False
            ).first()
            if seq:
                bill_obj.sequence_id = seq
                bill_obj.save(update_fields=['sequence_id'])

        mode = (data or {}).get('mode', 'bill_all')

        # ── Guard DP: jika sudah ada bill regular, DP tidak boleh ──
        if mode == 'bill_dp':
            # Cegah DP jika sudah ada tagihan regular (non-cancelled)
            if VendorBill.objects.filter(
                purchase_order=self,
                is_deleted=False,
                is_down_payment=False,
            ).exclude(status='cancelled').exists():
                return {
                    'error': (
                        'PO ini sudah memiliki tagihan regular. '
                        'DP tidak dapat dibuat setelah tagihan regular.'
                    )
                }

            # Cegah multiple DP bills — hanya 1 DP per PO (non-cancelled)
            if VendorBill.objects.filter(
                purchase_order=self,
                is_deleted=False,
                is_down_payment=True,
            ).exclude(status='cancelled').exists():
                return {
                    'error': (
                        'PO ini sudah memiliki DP bill. '
                        'Hanya 1 DP bill yang diperbolehkan per PO.'
                    )
                }

            dp_mode = (data or {}).get('dp_mode', 'percentage')
            dp_value = float((data or {}).get('dp_value', 0) or 0)

            if dp_mode == 'percentage':
                dp_pct = dp_value / 100

                with transaction.atomic():
                    child_cfg = self._get_child_flow('accounting.vendor_bill')
                    child_data = self._run_child_mapping(child_cfg) if child_cfg else {}
                    child_data['purchase_order'] = self
                    child_data['is_down_payment'] = True
                    child_data['status'] = 'draft'
                    bill = VendorBill.objects.create(**child_data)
                    _set_default_sequence(bill)

                    # Buat 1 DP line per PO line (proporsional per DPP)
                    from core.models.purchase.purchase_order_line import PurchaseOrderLine
                    po_lines = PurchaseOrderLine.objects.filter(
                        order_id=self.pk, is_deleted=False
                    )
                    # Group by (tax_pct, disc_pct) → 1 DP line per kelompok
                    groups = {}
                    for po_line in po_lines:
                        subtotal = float(po_line.qty or 0) * float(po_line.price or 0)
                        disc_pct = float(getattr(po_line, 'discount_percentage', 0) or 0)
                        dpp = subtotal * dp_pct
                        tax_pct = float(po_line.tax_percentage or 0)
                        key = (tax_pct, disc_pct)
                        if key not in groups:
                            groups[key] = {'dpp': 0.0, 'tax_pct': tax_pct, 'disc_pct': disc_pct}
                        groups[key]['dpp'] += dpp

                    for (tax_pct, disc_pct), data in groups.items():
                        price = data['dpp']
                        # Buat label
                        parts = [f'DP {dp_value:.0f}%']
                        if disc_pct > 0:
                            parts.append(f'Disc {disc_pct:.0f}%')
                        parts.append(f'Tax {tax_pct:.0f}%' if tax_pct > 0 else 'Non Tax')
                        label = ', '.join(parts)
                        VendorBillLine.objects.create(
                            bill_id=bill,
                            name=label,
                            qty=1,
                            price=price,
                            discount_percentage=disc_pct,
                            tax_percentage=tax_pct,
                        )

                    # Paksa compute summary agar grand_total terisi
                    bill._compute_summary()
                    bill.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

                dp_nominal = float(self.grand_total or 0) * dp_pct
                return {
                    '_action_type': 'open_record',
                    'model': 'accounting.vendor_bill',
                    'record_id': bill.pk,
                    'message': f'DP Bill berhasil dibuat: Rp {dp_nominal:,.0f}',
                }

            else:  # nominal
                with transaction.atomic():
                    child_cfg = self._get_child_flow('accounting.vendor_bill')
                    child_data = self._run_child_mapping(child_cfg) if child_cfg else {}
                    child_data['purchase_order'] = self
                    child_data['is_down_payment'] = True
                    child_data['status'] = 'draft'
                    bill = VendorBill.objects.create(**child_data)
                    _set_default_sequence(bill)
                    VendorBillLine.objects.create(
                        bill_id=bill,
                        name=f'DP (Nominal) — {self.reference or str(self)}',
                        qty=1,
                        price=dp_value,
                    )
                    # Paksa compute summary agar grand_total terisi
                    bill._compute_summary()
                    bill.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

                return {
                    '_action_type': 'open_record',
                    'model': 'accounting.vendor_bill',
                    'record_id': bill.pk,
                    'message': f'DP Bill berhasil dibuat: Rp {dp_value:,.0f}',
                }

        # ── Normal: bill_all ──

        # selected_lines: [{id: line_id, qty: bill_qty}, ...]
        selected_lines_raw = (data or {}).get('selected_lines')
        qty_map = {}
        selected_ids_set = set()
        if selected_lines_raw and isinstance(selected_lines_raw, list):
            for item in selected_lines_raw:
                lid = item.get('id')
                if lid is not None:
                    qty_map[int(lid)] = float(item.get('qty', 0) or 0)
                    selected_ids_set.add(int(lid))

        # Dapatkan child config dari _document_flow
        child_cfg = self._get_child_flow('accounting.vendor_bill')
        if not child_cfg:
            return {'error': 'Child flow configuration for vendor_bill not found'}

        # ── Guard: qty tidak boleh melebihi remaining billable ──
        po_lines_fd = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
        if po_lines_fd:
            line_model = ErpModelBase._model_registry.get(po_lines_fd.relation)
            if line_model:
                from core.models.accounting.vendor_bill import VendorBill
                from core.models.accounting.vendor_bill_line import VendorBillLine

                bill_ids_qs = VendorBill.objects.filter(
                    purchase_order=self.pk,
                    is_deleted=False,
                    is_down_payment=False,
                ).exclude(status='cancelled').values_list('pk', flat=True)

                lines_qs = line_model.objects.filter(
                    **{po_lines_fd.inverse_field: self.pk, 'is_deleted': False}
                )
                if selected_ids_set:
                    lines_qs = lines_qs.filter(pk__in=selected_ids_set)

                for line in lines_qs:
                    req_qty = qty_map.get(line.pk, float(line.qty or 0))
                    if req_qty <= 0:
                        return {
                            'error': (
                                f'Qty tagihan harus lebih dari 0 untuk "{line.name or line.product}"'
                            )
                        }
                    # hitung billed_qty existing
                    billed_agg = VendorBillLine.objects.filter(
                        bill_id__pk__in=list(bill_ids_qs) if bill_ids_qs else [],
                        product=line.product.pk if hasattr(line.product, 'pk') else line.product,
                    ).aggregate(total=models.Sum('qty'))
                    existing_billed = float(billed_agg['total'] or 0)
                    remaining = float(line.qty or 0) - existing_billed
                    if req_qty > remaining:
                        return {
                            'error': (
                                f'Qty tagihan melebihi sisa untuk "{line.name or line.product}": '
                                f'input {req_qty}, sisa {remaining:.0f}'
                            )
                        }

                    # ── Guard on_receipt: cek barang sudah diterima ──
                    po_bm = getattr(self, 'bill_method', None)
                    vendor_bm = getattr(self.vendor, 'bill_method', None) if getattr(self, 'vendor', None) else None
                    bill_method = po_bm if po_bm is not None else (vendor_bm or 'on_order')
                    if bill_method == 'on_receipt':
                        done_qty_agg = GoodsReceiptLine.objects.filter(
                            product=line.product.pk if hasattr(line.product, 'pk') else line.product,
                            receipt_id__purchase_order=self,
                            receipt_id__is_deleted=False,
                            receipt_id__status='done',
                        ).aggregate(total=models.Sum('received_qty'))
                        done_qty = float(done_qty_agg['total'] or 0)
                        if req_qty > done_qty:
                            remaining_for_bill = max(done_qty - existing_billed, 0)
                            return {
                                'error': (
                                    f'Metode tagihan "On Receipt". Barang "{line.name or line.product}" '
                                    f'baru diterima {done_qty:.0f}. '
                                    f'Sisa yang bisa ditagih {remaining_for_bill:.0f}, '
                                    f'input {req_qty:.0f}.'
                                )
                            }

        with transaction.atomic():
            # Apply mapping dari parent → child via _run_child_mapping
            child_data = self._run_child_mapping(child_cfg)

            # Set source field
            source_field = child_cfg.get('source_field_in_child', 'purchase_order')
            child_data[source_field] = self

            # Set status = draft
            child_data['status'] = 'draft'

            # Buat Bill
            bill = VendorBill.objects.create(**child_data)
            _set_default_sequence(bill)

            # Copy PO lines → Bill lines
            po_lines = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
            if po_lines:
                child_model = ErpModelBase._model_registry.get(po_lines.relation)
                if child_model:
                    lines_qs = child_model.objects.filter(
                        **{po_lines.inverse_field: self.pk, 'is_deleted': False}
                    )
                    # Filter selected lines untuk partial mode
                    if selected_ids_set:
                        lines_qs = lines_qs.filter(pk__in=selected_ids_set)
                    for line in lines_qs:
                        qty = qty_map.get(line.pk, float(line.qty or 0))
                        VendorBillLine.objects.create(
                            bill_id=bill,
                            product=line.product,
                            name=line.name,
                            qty=qty,
                            uom=line.uom,
                            price=line.price,
                            discount_percentage=line.discount_percentage,
                            tax_percentage=line.tax_percentage,
                        )

        # Trigger compute summary agar down_payment_amount & grand_total terisi
        bill._compute_down_payment()
        bill._compute_summary()
        bill.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

        return {
            '_action_type': 'open_record',
            'model': 'accounting.vendor_bill',
            'record_id': bill.pk,
            'message': 'Tagihan berhasil dibuat',
        }

    def _action_print(self, *args, **kwargs):
        """Print PO — tampilkan print preview di halaman yang sama (bukan tab baru)."""
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/purchase.order/{self.pk}/preview/',
            'pdf_url': f'/api/print/purchase.order/{self.pk}/download/',
        }

    def _print_context(self):
        """Auto: parent collects all fields + resolves Many2One.
        Override: tambah computed summary fields (discount, tax).
        """
        data = super()._print_context()
        lines = data.get('order_lines', [])
        lines_total = sum(float(line.get('total', 0) or 0) for line in lines)
        lines_discount = sum(float(line.get('discount_amount', 0) or 0) for line in lines)
        lines_tax = sum(float(line.get('tax_amount', 0) or 0) for line in lines)

        raw_subtotal = lines_total + lines_discount - lines_tax

        # Hitung total discount tergantung tipe
        discount_type = data.get('discount_type', 'per_product') or 'per_product'
        if discount_type == 'global':
            global_val = float(data.get('global_discount', 0) or 0)
            disc_method = data.get('discount_method', 'percentage') or 'percentage'
            if disc_method == 'nominal':
                total_discount = global_val
            else:
                total_discount = raw_subtotal * (global_val / 100)
        else:
            total_discount = lines_discount

        data['subtotal'] = raw_subtotal
        data['discount'] = total_discount
        data['tax'] = lines_tax
        if discount_type == 'global' and raw_subtotal > 0:
            computed_tax = lines_tax * (raw_subtotal - total_discount) / raw_subtotal
            data['tax'] = computed_tax
        data['grand_total'] = raw_subtotal - total_discount + data['tax']
        return data
