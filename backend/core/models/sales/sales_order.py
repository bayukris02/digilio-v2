from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    SelectionField, BooleanField, IntegerField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase
from core.models.sales.delivery_order import DeliveryOrder
from core.models.sales.delivery_order_line import DeliveryOrderLine
from core.models.accounting.customer_invoice import CustomerInvoice
from core.models.accounting.customer_invoice_line import CustomerInvoiceLine


class SalesOrder(BaseModel):
    _model_name = 'sales.order'
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
            'name': 'cancel',
            'from': ['draft', 'confirmed', 'done'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
            'guard': '_guard_cancel',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Order Type',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen (SO Local / SO Online, dll)',
        ),
        'reference': CharField(label='Reference', required=True, editable_statuses=[], placeholder='Automatic'),
        'customer': Many2OneField(
            label='Customer',
            relation='sales.customer',
            required=True,
        ),
        'order_date': DateField(label='Order Date'),
        'expected_date': DateField(label='Expected Date'),
        'notes': TextField(label='Notes'),
        'sales': CharField(label='Sales'),
        # ── Summary fields ──
        'discount_method': SelectionField(
            label='Metode Diskon',
            options=[('percentage', 'Discount (%)'), ('nominal', 'Discount (Rp)')],
            default='percentage',
            line_onchange={'discount_amount': 0, 'discount_percentage': 0},
        ),
        'discount_type': SelectionField(
            label='Tipe Diskon',
            options=[('per_product', 'Per Product'), ('global', 'Global Discount')],
            default='per_product',
            line_onchange={'discount_amount': 0, 'discount_percentage': 0},
        ),
        'global_discount': FloatField(label='Global Discount', default=0),
        'discount': MonetaryField(label='Discount', currency='IDR',
            compute='_compute_summary', depends=['order_lines', 'discount_type', 'discount_method', 'global_discount']),
        'tax': MonetaryField(label='Tax', currency='IDR',
            compute='_compute_summary', depends=['order_lines']),
        'manual_discount': FloatField(label='Manual Disc (%)', default=0),
        'subtotal': MonetaryField(label='Subtotal', currency='IDR', compute='_compute_summary', depends=['order_lines']),
        'grand_total': MonetaryField(label='Grand Total', currency='IDR', compute='_compute_summary', depends=['order_lines', 'manual_discount', 'discount_type', 'discount_method', 'global_discount']),

        # ── Down Payment & Invoice Info ──
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
            relation='sales.order.line',
            inverse_field='order_id',
        ),
    }

    # ── Document Flow ──
    _document_flow = {
        'children': [
            {
                'model': 'sales.delivery_order',
                'label': 'Delivery Order',
                'icon': 'CarOutlined',
                'source_field_in_child': 'sales_order',
                'state_conditions': {
                    'allowed_parent_states': ['confirmed', 'done'],
                    'blocked_child_states_for_parent_cancel': ['draft', 'waiting', 'done'],
                },
                'mapping': {
                    'sales_order': 'id',
                    'customer': 'customer',
                },
                'constraints': {
                    'max_per_parent': 0,  # 0 = unlimited, multiple DO per SO
                    'unique_per_parent': False,
                },
            },
            {
                'model': 'accounting.customer_invoice',
                'label': 'Customer Invoice',
                'icon': 'FileTextOutlined',
                'source_field_in_child': 'sales_order',
                'state_conditions': {
                    'allowed_parent_states': ['confirmed', 'done'],
                    'blocked_child_states_for_parent_cancel': ['draft', 'confirmed', 'done'],
                },
                'mapping': {
                    'sales_order': 'id',
                    'customer': 'customer',
                },
                'constraints': {
                    'max_per_parent': 0,
                    'unique_per_parent': False,
                },
            },
        ],
    }

    _list_view = {
        'columns': ['reference', 'customer', 'order_date', 'status'],
        'filters': ['status', 'order_date'],
        'group_by': ['status'],
        'default_sort': ['-order_date'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'sequence_id', 'customer', 'order_date', 'expected_date',
                               'discount_method', 'discount_type', 'global_discount'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['notes', 'sales'],
                },
            ],
            'actions': [
                {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
                {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
                {
                    'label': 'Kirim Barang',
                    'icon': 'CarOutlined',
                    'color': 'primary',
                    'action': 'create_delivery_order',
                    'states': ['confirmed'],
                    'wizard': {
                        'title': 'Kirim Barang',
                        'modes': [
                            {'value': 'save_draft', 'label': '📄 Buat Draft DO', 'icon': 'FileAddOutlined'},
                            {'value': 'confirm', 'label': '✅ Kirim Barang (Langsung Selesai)', 'icon': 'CheckCircleOutlined'},
                        ],
                        'line_selection': {
                            'relation': 'order_lines',
                            'columns': ['product', 'qty', 'delivered_qty', 'in_delivery_qty', 'remaining_qty'],
                            'show_for_modes': ['save_draft', 'confirm'],
                        },
                    },
                },
                {
                    'label': 'Buat Invoice',
                    'icon': 'FileTextOutlined',
                    'color': 'primary',
                    'action': 'create_invoice',
                    'states': ['confirmed', 'done'],
                    'wizard': {
                        'title': 'Buat Faktur',
                        'modes': [
                            {'value': 'bill_all', 'label': '📄 Faktur Regular', 'icon': 'FileTextOutlined'},
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
                            'qty_label': 'Invoice Qty',
                        },
                    },
                },
                {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'red', 'action': 'cancel', 'states': ['draft', 'confirmed', 'done']},
            ],
            'smart_buttons': [
                {'label': 'Delivery', 'model': 'sales.delivery_order', 'icon': 'CarOutlined'},
                {'label': 'Invoice', 'model': 'accounting.customer_invoice', 'icon': 'FileTextOutlined'},
            ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Order Lines',
                'relation': 'order_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'price', 'discount_percentage', 'discount_amount', 'global_discount_amount', 'tax_percentage', 'tax_amount', 'total'],
                'summary': {
                    'columns': {'qty': 'sum', 'discount_percentage': 'avg', 'discount_amount': 'sum',
                                'global_discount_amount': 'sum',
                                'tax_percentage': 'avg', 'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'manual_discount', 'tax'],
                    'inputs': ['manual_discount'],
                    'compute_deps': ['discount_type', 'discount_method', 'global_discount'],
                    'grand_total': 'grand_total',
                    'after_grand_total': ['due_amount'],
                    'child_details': {
                        'data_key': '_invoice_details',
                        'model': 'accounting.customer_invoice',
                    },
                },
            },
            {
                'key': 'pengiriman_barang',
                'label': 'Pengiriman Barang',
                'relation': 'order_lines',
                'columns': ['product', 'name', 'qty', 'uom', 'delivered_qty', 'in_delivery_qty', 'remaining_qty', 'billed_qty'],
                'read_only': True,
            },
            {
                'key': 'commissions',
                'label': 'Komisi',
                'fields': ['sales'],
            },
        ],
    }

    # ── Guards ──

    def _guard_cancel(self):
        """Prevent cancel if children are active."""
        can_cancel, msg = self._can_cancel()
        if not can_cancel:
            raise ValueError(msg)

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

    def _effect_confirm(self):
        """Generate reference dari sequence setelah confirm."""
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/sales.order/{self.pk}/preview/',
            'pdf_url': f'/api/print/sales.order/{self.pk}/download/',
        }

    def _action_create_delivery_order(self, data=None):
        """Buat Delivery Order + copy lines dari SO, lalu open form DO.

        data: dict dari frontend wizard — {mode, selected_lines}
          mode = save_draft | confirm
            save_draft → DO status = waiting (draft)
            confirm   → DO status = done
          selected_lines = [{id, qty}, ...] — selalu dikirim dari frontend,
            semua line = ALL, sebagian = PARTIAL (dari checklist user)
        """
        from django.db import transaction

        mode = (data or {}).get('mode', 'save_draft')
        do_status = 'done' if mode == 'confirm' else 'waiting'

        # selected_lines: [{id: line_id, qty: delivered_qty}, ...]
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
        child_cfg = self._get_child_flow('sales.delivery_order')
        if not child_cfg:
            return {'error': 'Child flow configuration for delivery_order not found'}

        # ── Validasi qty sebelum transaction ──
        so_lines_fd = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
        if so_lines_fd:
            line_model = ErpModelBase._model_registry.get(so_lines_fd.relation)
            if line_model:
                lines_qs = line_model.objects.filter(
                    **{so_lines_fd.inverse_field: self.pk, 'is_deleted': False}
                )
                if selected_ids_set:
                    lines_qs = lines_qs.filter(pk__in=selected_ids_set)

                from django.db.models import Sum as ModelSum

                for line in lines_qs:
                    delivered_qty = qty_map.get(line.pk, float(line.qty or 0))
                    prod_name = line.name or str(line.product or 'Produk')

                    if delivered_qty <= 0:
                        return {'error': f'"{prod_name}": qty dikirim harus lebih dari 0.'}

                    # over-delivery check
                    existing_qty = float(
                        DeliveryOrderLine.objects.filter(
                            product=line.product,
                            delivery_id__sales_order=self,
                            delivery_id__is_deleted=False,
                            delivery_id__status__in=['done', 'waiting'],
                            is_deleted=False,
                        ).aggregate(total=ModelSum('delivered_qty'))['total'] or 0
                    )
                    if existing_qty + delivered_qty > float(line.qty or 0):
                        remaining = max(float(line.qty or 0) - existing_qty, 0)
                        return {
                            'error': (
                                f'"{prod_name}": qty dikirim ({delivered_qty:.0f}) '
                                f'melebihi sisa pesanan ({remaining:.0f}). '
                                f'Sudah dikirim {existing_qty:.0f} dari {float(line.qty or 0):.0f}.'
                            )
                        }

        with transaction.atomic():
            # Apply mapping dari parent → child via _run_child_mapping
            child_data = self._run_child_mapping(child_cfg)

            # Set source field (sales_order)
            source_field = child_cfg.get('source_field_in_child', 'sales_order')
            child_data[source_field] = self

            # Copy customer reference
            if hasattr(self, 'customer') and self.customer:
                child_data['customer'] = self.customer

            # Set status sesuai mode
            child_data['status'] = do_status

            # Buat DO
            do = DeliveryOrder.objects.create(**child_data)

            # Copy SO lines → DO lines (hanya yang dipilih)
            if so_lines_fd:
                line_model = ErpModelBase._model_registry.get(so_lines_fd.relation)
                if line_model:
                    lines_qs = line_model.objects.filter(
                        **{so_lines_fd.inverse_field: self.pk, 'is_deleted': False}
                    )
                    if selected_ids_set:
                        lines_qs = lines_qs.filter(pk__in=selected_ids_set)
                    for line in lines_qs:
                        delivered_qty = qty_map.get(line.pk, float(line.qty or 0))

                        DeliveryOrderLine.objects.create(
                            delivery_id=do,
                            product=line.product,
                            name=line.name,
                            delivered_qty=delivered_qty,
                            unit_price=line.price,
                        )

        mode_label = 'draft DO dibuat' if mode == 'save_draft' else 'barang dikirim'
        return {
            '_action_type': 'open_record',
            'model': 'sales.delivery_order',
            'record_id': do.pk,
            'message': f'Delivery Order berhasil {mode_label}',
        }

    def _action_create_invoice(self, data=None):
        """Buat Customer Invoice + copy lines dari SO, lalu open form Invoice.

        data: dict dari frontend wizard — {mode, selected_lines, dp_percentage, dp_nominal}
          mode = bill_all | bill_dp_pct | bill_dp_nominal
          selected_lines = [{id, qty}, ...] untuk mode dengan line selection
        """
        from django.db import transaction

        mode = (data or {}).get('mode', 'bill_all')

        # ── Guard DP: jika sudah ada invoice regular, DP tidak boleh ──
        if mode == 'bill_dp':
            # Cegah DP jika sudah ada faktur regular (non-cancelled)
            if CustomerInvoice.objects.filter(
                sales_order=self,
                is_deleted=False,
                is_down_payment=False,
            ).exclude(status='cancelled').exists():
                return {
                    'error': (
                        'SO ini sudah memiliki faktur regular. '
                        'DP tidak dapat dibuat setelah faktur regular.'
                    )
                }

            # Cegah multiple DP invoices — hanya 1 DP per SO (non-cancelled)
            if CustomerInvoice.objects.filter(
                sales_order=self,
                is_deleted=False,
                is_down_payment=True,
            ).exclude(status='cancelled').exists():
                return {
                    'error': (
                        'SO ini sudah memiliki DP invoice. '
                        'Hanya 1 DP invoice yang diperbolehkan per SO.'
                    )
                }

            dp_mode = (data or {}).get('dp_mode', 'percentage')
            dp_value = float((data or {}).get('dp_value', 0) or 0)

            if dp_mode == 'percentage':
                dp_pct = dp_value / 100

                with transaction.atomic():
                    child_cfg = self._get_child_flow('accounting.customer_invoice')
                    child_data = self._run_child_mapping(child_cfg) if child_cfg else {}
                    child_data['sales_order'] = self
                    child_data['is_down_payment'] = True
                    child_data['status'] = 'draft'
                    invoice = CustomerInvoice.objects.create(**child_data)

                    # Buat 1 DP line per SO line (proporsional per DPP)
                    from core.models.sales.sales_order_line import SalesOrderLine
                    so_lines = SalesOrderLine.objects.filter(
                        order_id=self.pk, is_deleted=False
                    )
                    # Group by (tax_pct, disc_pct) → 1 DP line per kelompok
                    groups = {}
                    for so_line in so_lines:
                        subtotal = float(so_line.qty or 0) * float(so_line.price or 0)
                        disc_pct = float(getattr(so_line, 'discount_percentage', 0) or 0)
                        dpp = subtotal * dp_pct
                        tax_pct = float(so_line.tax_percentage or 0)
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
                        CustomerInvoiceLine.objects.create(
                            invoice_id=invoice,
                            name=label,
                            qty=1,
                            price=price,
                            discount_percentage=disc_pct,
                            tax_percentage=tax_pct,
                        )

                    # Paksa compute summary agar grand_total terisi
                    invoice._compute_summary()
                    invoice.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

                dp_nominal = float(self.grand_total or 0) * dp_pct
                return {
                    '_action_type': 'open_record',
                    'model': 'accounting.customer_invoice',
                    'record_id': invoice.pk,
                    'message': f'DP Invoice berhasil dibuat: Rp {dp_nominal:,.0f}',
                }

            else:  # nominal
                with transaction.atomic():
                    child_cfg = self._get_child_flow('accounting.customer_invoice')
                    child_data = self._run_child_mapping(child_cfg) if child_cfg else {}
                    child_data['sales_order'] = self
                    child_data['is_down_payment'] = True
                    child_data['status'] = 'draft'
                    invoice = CustomerInvoice.objects.create(**child_data)
                    CustomerInvoiceLine.objects.create(
                        invoice_id=invoice,
                        name=f'DP (Nominal) — {self.reference or str(self)}',
                        qty=1,
                        price=dp_value,
                    )
                    # Paksa compute summary agar grand_total terisi
                    invoice._compute_summary()
                    invoice.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

                return {
                    '_action_type': 'open_record',
                    'model': 'accounting.customer_invoice',
                    'record_id': invoice.pk,
                    'message': f'DP Invoice berhasil dibuat: Rp {dp_value:,.0f}',
                }

        # ── Normal: bill_all ──

        # selected_lines: [{id: line_id, qty: invoice_qty}, ...]
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
        child_cfg = self._get_child_flow('accounting.customer_invoice')
        if not child_cfg:
            return {'error': 'Child flow configuration for customer_invoice not found'}

        # ── Guard: qty tidak boleh melebihi remaining billable ──
        so_lines_fd = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
        if so_lines_fd:
            line_model = ErpModelBase._model_registry.get(so_lines_fd.relation)
            if line_model:
                inv_ids_qs = CustomerInvoice.objects.filter(
                    sales_order=self.pk,
                    is_deleted=False,
                    is_down_payment=False,
                ).exclude(status='cancelled').values_list('pk', flat=True)

                lines_qs = line_model.objects.filter(
                    **{so_lines_fd.inverse_field: self.pk, 'is_deleted': False}
                )
                if selected_ids_set:
                    lines_qs = lines_qs.filter(pk__in=selected_ids_set)

                for line in lines_qs:
                    req_qty = qty_map.get(line.pk, float(line.qty or 0))
                    if req_qty <= 0:
                        return {
                            'error': (
                                f'Qty faktur harus lebih dari 0 untuk "{line.name or line.product}"'
                            )
                        }
                    # hitung billed_qty existing
                    billed_agg = CustomerInvoiceLine.objects.filter(
                        invoice_id__pk__in=list(inv_ids_qs) if inv_ids_qs else [],
                        product=line.product.pk if hasattr(line.product, 'pk') else line.product,
                    ).aggregate(total=models.Sum('qty'))
                    existing_billed = float(billed_agg['total'] or 0)
                    remaining = float(line.qty or 0) - existing_billed
                    if req_qty > remaining:
                        return {
                            'error': (
                                f'Qty faktur melebihi sisa untuk "{line.name or line.product}": '
                                f'input {req_qty}, sisa {remaining:.0f}'
                            )
                        }

        with transaction.atomic():
            # Apply mapping dari parent → child via _run_child_mapping
            child_data = self._run_child_mapping(child_cfg)

            # Set source field
            source_field = child_cfg.get('source_field_in_child', 'sales_order')
            child_data[source_field] = self

            # Copy customer reference
            if hasattr(self, 'customer') and self.customer:
                child_data['customer'] = self.customer

            # Set status = draft
            child_data['status'] = 'draft'

            # Buat Invoice
            invoice = CustomerInvoice.objects.create(**child_data)

            # Copy SO lines → Invoice lines
            so_lines = self.__class__.objects.get(pk=self.pk)._field_descriptors.get('order_lines')
            if so_lines:
                child_model = ErpModelBase._model_registry.get(so_lines.relation)
                if child_model:
                    lines_qs = child_model.objects.filter(
                        **{so_lines.inverse_field: self.pk, 'is_deleted': False}
                    )
                    # Filter selected lines
                    if selected_ids_set:
                        lines_qs = lines_qs.filter(pk__in=selected_ids_set)
                    for line in lines_qs:
                        qty = qty_map.get(line.pk, float(line.qty or 0))
                        CustomerInvoiceLine.objects.create(
                            invoice_id=invoice,
                            product=line.product,
                            name=line.name,
                            qty=qty,
                            uom=line.uom,
                            price=line.price,
                        )

        # Trigger compute summary agar down_payment_amount & grand_total terisi
        invoice._compute_summary()
        invoice.save(update_fields=['subtotal', 'discount', 'tax', 'grand_total'])

        return {
            '_action_type': 'open_record',
            'model': 'accounting.customer_invoice',
            'record_id': invoice.pk,
            'message': 'Faktur berhasil dibuat',
        }

    def _print_context(self):
        data = super()._print_context()
        lines_total = sum(float(line.get('total', 0) or 0) for line in data.get('order_lines', []))
        lines_discount = sum(float(line.get('discount_amount', 0) or 0) for line in data.get('order_lines', []))
        lines_tax = sum(float(line.get('tax_amount', 0) or 0) for line in data.get('order_lines', []))
        manual_disc_pct = float(data.get('manual_discount', 0) or 0)

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
            total_discount = lines_discount + raw_subtotal * (manual_disc_pct / 100)

        data['subtotal'] = raw_subtotal
        data['discount'] = total_discount
        data['tax'] = lines_tax
        if discount_type == 'global' and raw_subtotal > 0:
            computed_tax = lines_tax * (raw_subtotal - total_discount) / raw_subtotal
            data['tax'] = computed_tax
        data['grand_total'] = raw_subtotal - total_discount + data['tax']
        return data

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Sales Order'
        verbose_name_plural = 'Sales Orders'

    def _compute_summary(self):
        """Compute subtotal, discount, tax, and grand_total from order lines + manual_discount."""
        # Get line totals from in-memory data (compute API) or from DB
        lines_data = getattr(self, '_tmp_one2many', {}).get('order_lines', [])

        def sum_lines(field):
            if lines_data:
                return sum(float(line.get(field, 0) or 0) for line in lines_data)
            elif self.pk:
                fd = self._field_descriptors.get('order_lines')
                if fd:
                    child_model = ErpModelBase._model_registry.get(fd.relation)
                    if child_model:
                        return sum(
                            float(getattr(line, field, 0) or 0)
                            for line in child_model.objects.filter(
                                **{fd.inverse_field: self.pk, 'is_deleted': False}
                            )
                        )
            return 0

        line_total = sum_lines('total')
        line_discount = sum_lines('discount_amount')
        line_tax = sum_lines('tax_amount')

        # Raw subtotal = sum(qty*price)
        raw_subtotal = line_total + line_discount - line_tax

        # Hitung total discount tergantung tipe
        discount_type = getattr(self, 'discount_type', 'per_product') or 'per_product'
        if discount_type == 'global':
            global_val = float(getattr(self, 'global_discount', 0) or 0)
            disc_method = getattr(self, 'discount_method', 'percentage') or 'percentage'
            if disc_method == 'nominal':
                total_discount = global_val
            else:
                total_discount = raw_subtotal * (global_val / 100)
        else:
            # Pre-tax base setelah line discounts
            after_line_disc = raw_subtotal - line_discount
            # Manual discount applied to pre-tax base
            manual_disc_pct = float(getattr(self, 'manual_discount', 0) or 0)
            manual_disc_amt = after_line_disc * (manual_disc_pct / 100)
            total_discount = line_discount + manual_disc_amt

        self.subtotal = raw_subtotal
        self.discount = total_discount
        if discount_type == 'global' and raw_subtotal > 0:
            computed_tax = line_tax * (raw_subtotal - total_discount) / raw_subtotal
        else:
            computed_tax = line_tax
        self.tax = computed_tax
        self.grand_total = raw_subtotal - total_discount + computed_tax

    def _compute_dp_info(self):
        """Cari DP invoice & hitung dp_amount, due_amount."""
        from core.models.accounting.customer_invoice import CustomerInvoice
        invoices = CustomerInvoice.objects.filter(
            sales_order=self.pk,
            is_deleted=False,
        ).exclude(status='cancelled')

        total_invoiced = sum(float(i.grand_total or 0) for i in invoices)
        dp_inv = invoices.filter(is_down_payment=True).first()
        self.dp_amount = dp_inv.grand_total or 0 if dp_inv else 0
        self.due_amount = max(float(self.grand_total or 0) - total_invoiced, 0)

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='sales.order', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk

        # -- Generic column config rules untuk frontend --
        config['column_config_rules'] = {
            'order_lines': {
                'discount_percentage': {
                    'hide_when': {'discount_method': 'nominal', 'discount_type': 'global'},
                },
                'discount_amount': {
                    'hide_when': {'discount_type': 'global'},
                    'editable_when': {'discount_method': 'nominal'},
                },
                'global_discount_amount': {
                    'hide_when': {'discount_type': 'per_product'},
                    'readonly_when': {'discount_type': 'global'},
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
        """Override: trigger compute & tambah invoice_details untuk summary."""
        self._compute_dp_info()
        data = super().to_record()

        # Tambah daftar invoice (DP + Regular) untuk render di summary
        from core.models.accounting.customer_invoice import CustomerInvoice
        invoices = CustomerInvoice.objects.filter(
            sales_order=self.pk,
            is_deleted=False,
        ).exclude(status='cancelled').order_by('pk')
        data['_invoice_details'] = []
        for inv in invoices:
            # Recompute agar grand_total sesuai logika terbaru (termasuk DP)
            inv._run_compute()
            inv.save(update_fields=inv.get_computed_fields())
            data['_invoice_details'].append({
                'id': inv.pk,
                'label': 'DP Invoice' if inv.is_down_payment else 'Invoice',
                'ref': inv.reference or f'#{inv.pk}',
                'amount': float(inv.grand_total or 0),
            })

        return data
