from core.fields import (
    CharField, DateField, MonetaryField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class Project(BaseModel):
    """Inisiasi dan pencatatan data dasar proyek baru."""

    _model_name = 'project.project'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Proyek', required=True),
        'category': Many2OneField(
            label='Kategori',
            relation='project.project_category',
            required=False,
            help_text='Kategori proyek dari master Project Kategori',
        ),
        'date_start': DateField(label='Tanggal Mulai'),
        'date_end': DateField(label='Tanggal Selesai'),
        'project_manager': Many2OneField(
            label='Manajer Proyek (PM)',
            relation='settings.user',
            required=False,
        ),
        'contract_value': MonetaryField(
            label='Nilai Kontrak',
            currency='IDR',
        ),
        'client': Many2OneField(
            label='Client / Owner',
            relation='sales.customer',
            required=False,
        ),
        'location': CharField(label='Lokasi'),
        'executing_entity': Many2OneField(
            label='Entitas Pelaksana',
            relation='settings.company',
            required=False,
        ),
        'lines': One2ManyField(
            label='Baris Proyek',
            relation='project.project_line',
            inverse_field='project_id',
        ),
        'units': One2ManyField(
            label='Unit Proyek',
            relation='project.project_unit',
            inverse_field='project_id',
        ),
        'unit_details': One2ManyField(
            label='Detail Unit',
            relation='project.project_unit_detail',
            inverse_field='project_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'category', 'client', 'project_manager', 'date_start', 'date_end', 'contract_value', 'location'],
        'filters': ['category'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'category', 'date_start', 'date_end'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['project_manager', 'contract_value', 'client', 'location', 'executing_entity'],
                },
            ],
            'actions': [
                {
                    'label': 'Perbarui Progress',
                    'icon': 'EditOutlined',
                    'color': 'primary',
                    'action': 'update_progress',
                    'goto_tab': 'lines',
                },
                {
                    'label': 'Input Penjualan',
                    'icon': 'SendOutlined',
                    'color': 'primary',
                    'action': 'input_sales',
                    'wizard': {
                        'title': 'Input Penjualan',
                        'modes': [
                            {
                                'value': 'create',
                                'label': '✅ Buat Penjualan',
                                'icon': 'CheckCircleOutlined',
                                'inputs': [
                                    {'key': 'customer', 'label': 'Nama Customer', 'type': 'many2one', 'relation': 'sales.customer'},
                                    {'key': 'unit', 'label': 'Unit', 'type': 'many2one', 'relation': 'project.project_unit',
                                     'filter': {'project_id': '{record_id}'},
                                     'value_field': 'unit_id', 'label_field': 'unit_id'},
                                    {'key': 'harga_jual', 'label': 'Harga Jual (Rp)', 'type': 'number', 'default': 0},
                                    {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
                                ],
                            },
                        ],
                    },
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Milestone Proyek',
                'relation': 'lines',
                'columns': ['milestone_id', 'progress'],
                'row_actions': [
                    {
                        'label': 'Perbarui Progress',
                        'actions': [
                            {
                                'label': 'Perbarui Progress',
                                'action': 'update_progress',
                                'wizard': {
                                    'title': 'Perbarui Progress',
                                    'modes': [
                                        {
                                            # Summary dokumen milestone — bukan option aksi (icon Home)
                                            'value': 'progress',
                                            'label': '',
                                            'icon': 'HomeOutlined',
                                            'table': {
                                                'title': 'Progress Dokumen',
                                                'columns': [
                                                    {'key': 'reference', 'label': 'Referensi'},
                                                    {'key': 'status', 'label': 'Status'},
                                                    {'key': 'amount', 'label': 'Jumlah'},
                                                    {'key': 'progress', 'label': 'Progress'},
                                                ],
                                            },
                                        },
                                        {
                                            'value': 'buat_tagihan',
                                            'label': 'Buat Tagihan',
                                            'inputs': [
                                                {'key': 'vendor', 'label': 'Vendor', 'type': 'many2one', 'relation': 'purchase.vendor'},
                                                {'key': 'bill_date', 'label': 'Tanggal Tagihan', 'type': 'date'},
                                                {'key': 'due_date', 'label': 'Jatuh Tempo', 'type': 'date'},
                                                {'key': 'milestone_line', 'label': 'Baris Milestone', 'type': 'many2one', 'relation': 'project.milestone_line'},
                                                {'key': 'amount', 'label': 'Nominal (Rp)', 'type': 'number', 'default': 0},
                                                {'key': 'description', 'label': 'Deskripsi', 'type': 'text'},
                                            ],
                                        },
                                        {
                                            'value': 'input_expenses',
                                            'label': 'Input Biaya',
                                            'inputs': [
                                                {'key': 'date', 'label': 'Tanggal', 'type': 'date'},
                                                {'key': 'payment_method', 'label': 'Metode Pembayaran', 'type': 'many2one', 'relation': 'accounting.payment_method'},
                                                {'key': 'milestone_line', 'label': 'Baris Milestone', 'type': 'many2one', 'relation': 'project.milestone_line'},
                                                {'key': 'description', 'label': 'Deskripsi', 'type': 'text'},
                                                {'key': 'amount', 'label': 'Nominal (Rp)', 'type': 'number', 'default': 0},
                                            ],
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                ],
            },
            {
                'key': 'units',
                'label': 'Progress Penjualan',
                'relation': 'units',
                'columns': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
            },
            {
                'key': 'unit_details',
                'label': 'Detail Unit',
                'relation': 'unit_details',
                'columns': ['name', 'unit_id', 'selling_price', 'est_cost', 'est_margin'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project'
        verbose_name_plural = 'Project'

    def __str__(self):
        return self.name or ''

    # ── Actions ──

    def _action_update_progress(self, data=None):
        """Wizard Update Progress per milestone — dispatch by mode.

        mode = buat_tagihan | input_expenses | update (progress lama)
        """
        mode = (data or {}).get('mode', '')
        if mode == 'buat_tagihan':
            return self._action_buat_tagihan(data)
        if mode == 'input_expenses':
            return self._action_input_expenses(data)
        if mode == 'progress':
            return self._action_progress_table(data)
        # Fallback: mode lama 'update' / tanpa mode → update progress lines
        return self._update_progress_lines(data)

    def _update_progress_lines(self, data=None):
        """Update progress milestone lines (nilai input = progress baru)."""
        from core.model_meta import ErpModelBase

        selected_lines_raw = (data or {}).get('selected_lines')
        if not selected_lines_raw or not isinstance(selected_lines_raw, list):
            return {'error': 'Tidak ada baris yang dipilih.'}

        fd = self._field_descriptors.get('lines')
        if not fd:
            return {'error': 'Konfigurasi lines tidak ditemukan.'}
        line_model = ErpModelBase._model_registry.get(fd.relation)
        if not line_model:
            return {'error': 'Model project.project_line tidak ditemukan.'}

        updated = 0
        for item in selected_lines_raw:
            lid = item.get('id')
            if lid is None:
                continue
            value = float(item.get('qty', 0) or 0)
            line = line_model.objects.filter(
                pk=int(lid), project_id=self.pk, is_deleted=False
            ).first()
            if not line:
                continue
            line.progress = min(max(value, 0), 100)
            line.save(update_fields=['progress'])
            updated += 1

        return {'message': f'Progress diupdate untuk {updated} milestone.'}

    def _action_buat_tagihan(self, data=None):
        """Buat Vendor Bill draft dari wizard (vendor + nominal), lalu open form bill."""
        from django.db import transaction
        from datetime import date
        from core.model_meta import ErpModelBase
        from core.models.accounting.vendor_bill import VendorBill
        from core.models.accounting.vendor_bill_line import VendorBillLine
        from core.models.settings.sequence import Sequence

        vendor_id = (data or {}).get('vendor')
        amount = float((data or {}).get('amount', 0) or 0)
        bill_date = (data or {}).get('bill_date') or None
        due_date = (data or {}).get('due_date') or None
        description = ((data or {}).get('description') or '').strip()
        if not vendor_id:
            return {'error': 'Vendor wajib diisi.'}
        if amount <= 0:
            return {'error': 'Nominal harus lebih dari 0.'}

        # Milestone tujuan (dari row action — line_id baris yang diklik)
        line_id = (data or {}).get('line_id')
        project_line = None
        if line_id:
            line_model = ErpModelBase._model_registry.get('project.project_line')
            if line_model:
                project_line = line_model.objects.filter(
                    pk=int(line_id), project_id=self.pk, is_deleted=False
                ).first()

        # Milestone Line tujuan (dari wizard — sub-line milestone)
        milestone_line_id = (data or {}).get('milestone_line')
        milestone_line = None
        if milestone_line_id:
            ml_model = ErpModelBase._model_registry.get('project.milestone_line')
            if ml_model:
                milestone_line = ml_model.objects.filter(
                    pk=int(milestone_line_id), is_deleted=False
                ).first()

        vendor_model = ErpModelBase._model_registry.get('purchase.vendor')
        vendor = vendor_model.objects.filter(pk=int(vendor_id), is_deleted=False).first() if vendor_model else None
        if not vendor:
            return {'error': 'Vendor tidak ditemukan.'}

        # Inject sequence aktif (sama seperti get_model_config) biar bill bisa langsung Confirm
        active_seq = Sequence.objects.filter(
            model_ref='accounting.vendor_bill', active=True, is_deleted=False
        ).first()

        with transaction.atomic():
            bill = VendorBill.objects.create(
                vendor=vendor,
                sequence_id=active_seq,
                status='draft',
                bill_date=bill_date or date.today(),
                due_date=due_date,
                project=self,
                project_line=project_line,
                milestone_line=milestone_line,
            )
            VendorBillLine.objects.create(
                bill_id=bill,
                name=description or f'Tagihan proyek: {self.name or ""}',
                qty=1,
                price=amount,
            )
            # Compute summary + payment summary
            bill._compute_summary()
            bill._compute_payment_summary()
            bill.save()

        return {
            '_action_type': 'open_record',
            'model': 'accounting.vendor_bill',
            'record_id': bill.pk,
            'message': f'Vendor Bill berhasil dibuat: Rp {amount:,.0f}',
        }

    def _action_input_expenses(self, data=None):
        """Wizard Input Expenses — buat accounting.expense draft + 1 line.

        description & nominal dari wizard otomatis mengisi Expense Line.
        """
        from django.db import transaction
        from datetime import date
        from core.model_meta import ErpModelBase
        from core.models.accounting.expense import Expense
        from core.models.accounting.expense_line import ExpenseLine
        from core.models.settings.sequence import Sequence

        expense_date = (data or {}).get('date') or date.today().isoformat()
        payment_method_id = (data or {}).get('payment_method')
        description = ((data or {}).get('description') or '').strip()
        amount = float((data or {}).get('amount', 0) or 0)
        if amount <= 0:
            return {'error': 'Nominal harus lebih dari 0.'}

        payment_method = None
        if payment_method_id:
            pm_model = ErpModelBase._model_registry.get('accounting.payment_method')
            if pm_model:
                payment_method = pm_model.objects.filter(
                    pk=int(payment_method_id), is_deleted=False
                ).first()
                if not payment_method:
                    return {'error': 'Payment Method tidak ditemukan.'}

        line_desc = description or f'Biaya proyek: {self.name or ""}'

        # Milestone tujuan (dari row action — line_id baris yang diklik)
        line_id = (data or {}).get('line_id')
        project_line = None
        if line_id:
            pl_model = ErpModelBase._model_registry.get('project.project_line')
            if pl_model:
                project_line = pl_model.objects.filter(
                    pk=int(line_id), project_id=self.pk, is_deleted=False
                ).first()

        # Milestone Line tujuan (dari wizard — sub-line milestone)
        milestone_line_id = (data or {}).get('milestone_line')
        milestone_line = None
        if milestone_line_id:
            ml_model = ErpModelBase._model_registry.get('project.milestone_line')
            if ml_model:
                milestone_line = ml_model.objects.filter(
                    pk=int(milestone_line_id), is_deleted=False
                ).first()

        # Inject sequence aktif (sama seperti get_model_config) biar bisa langsung Confirm
        active_seq = Sequence.objects.filter(
            model_ref='accounting.expense', active=True, is_deleted=False
        ).first()

        with transaction.atomic():
            expense = Expense.objects.create(
                sequence_id=active_seq,
                status='draft',
                date=expense_date,
                payment_method=payment_method,
                description=line_desc,
                project_line=project_line,
                milestone_line=milestone_line,
            )
            ExpenseLine.objects.create(
                expense_id=expense,
                description=line_desc,
                amount=amount,
            )

        return {
            '_action_type': 'open_record',
            'model': 'accounting.expense',
            'record_id': expense.pk,
            'message': f'Input Biaya berhasil dibuat: Rp {amount:,.0f}',
        }

    def _action_progress_table(self, data=None):
        """Mode Progress — tabel dokumen (tagihan + expenses) per milestone.

        Kolom: Reference / Status / Amount / Progress per dokumen.
        Kontribusi progress sama dengan _sync_milestone_progress:
        draft 10% / confirmed 50% / paid|posted 100%.
        """
        from core.models.accounting.vendor_bill import VendorBill
        from core.models.accounting.expense import Expense
        from core.models.accounting.expense_line import ExpenseLine

        line_id = (data or {}).get('line_id')
        if not line_id:
            return {'error': 'Pilih milestone terlebih dahulu.'}

        rows = []

        # ── Vendor Bills ──
        bills = VendorBill.objects.filter(
            project_line_id=int(line_id), is_deleted=False
        ).exclude(status='cancelled')
        for b in bills:
            if b.payment_status == 'paid':
                status_label, prog = 'Paid', 100.0
            elif b.status == 'confirmed':
                status_label, prog = 'Confirmed', 50.0
            else:
                status_label, prog = 'Draft', 10.0
            rows.append({
                'reference': b.reference or f'#{b.pk}',
                'status': status_label,
                'amount': f'Rp {float(b.grand_total or 0):,.0f}',
                'progress': f'{prog:.0f}%',
            })

        # ── Expenses ──
        expenses = Expense.objects.filter(
            project_line_id=int(line_id), is_deleted=False
        )
        for e in expenses:
            if e.status == 'posted':
                status_label, prog = 'Posted', 100.0
            elif e.status == 'confirmed':
                status_label, prog = 'Confirmed', 50.0
            else:
                status_label, prog = 'Draft', 10.0
            total = sum(
                float(l.amount or 0)
                for l in ExpenseLine.objects.filter(expense_id=e, is_deleted=False)
            )
            rows.append({
                'reference': e.reference or f'#{e.pk}',
                'status': status_label,
                'amount': f'Rp {total:,.0f}',
                'progress': f'{prog:.0f}%',
            })

        return {'_action_type': 'table', 'rows': rows}

    def _action_input_sales(self, data=None):
        """Input Penjualan — buat accounting.customer_invoice dari wizard, lalu line baru di Detail Unit.

        Wizard input: customer, unit, harga_jual, tanggal.
        Menghasilkan:
          - accounting.customer_invoice draft (customer + 1 invoice line,
            qty=1, price=harga_jual, name=unit)
          - project.project_unit_detail baru (name=customer, unit_id=unit,
            selling_price=harga_jual) → line baru di tab Detail Unit.
          - update qty_sold di project.project_unit (tab Progress Penjualan).
        Ditolak jika unit sudah terjual 100% (qty_sold >= qty_available).
        """
        from django.db import transaction
        from datetime import date
        from core.model_meta import ErpModelBase
        from core.models.accounting.customer_invoice import CustomerInvoice
        from core.models.accounting.customer_invoice_line import CustomerInvoiceLine
        from core.models.settings.sequence import Sequence

        customer_id = (data or {}).get('customer')
        unit_id = (data or {}).get('unit')
        harga_jual = float((data or {}).get('harga_jual', 0) or 0)
        tanggal = (data or {}).get('tanggal') or date.today().isoformat()

        if not customer_id:
            return {'error': 'Nama Customer wajib diisi.'}
        if not unit_id:
            return {'error': 'Unit wajib diisi.'}
        if harga_jual <= 0:
            return {'error': 'Harga Jual harus lebih dari 0.'}

        customer_model = ErpModelBase._model_registry.get('sales.customer')
        customer = customer_model.objects.filter(pk=int(customer_id), is_deleted=False).first() if customer_model else None
        if not customer:
            return {'error': 'Customer tidak ditemukan.'}

        unit_model = ErpModelBase._model_registry.get('project.unit')
        unit = unit_model.objects.filter(pk=int(unit_id), is_deleted=False).first() if unit_model else None
        if not unit:
            return {'error': 'Unit tidak ditemukan.'}

        # Baris Progress Penjualan (project.project_unit) untuk unit ini
        from core.models.project.project_unit import ProjectUnit
        project_unit = ProjectUnit.objects.filter(
            project_id=self, unit_id=unit, is_deleted=False
        ).first()
        if not project_unit:
            return {'error': f'Unit "{unit}" tidak ada di tab Progress Penjualan proyek ini.'}
        available = int(project_unit.qty_available or 0)
        sold = int(project_unit.qty_sold or 0)
        if available > 0 and sold >= available:
            return {'error': f'Unit "{unit}" sudah terjual 100% — tidak bisa membuat Invoice.'}

        # Inject sequence aktif (pola sama seperti _action_buat_tagihan)
        active_seq = Sequence.objects.filter(
            model_ref='accounting.customer_invoice', active=True, is_deleted=False
        ).first()

        with transaction.atomic():
            invoice = CustomerInvoice.objects.create(
                customer=customer,
                sequence_id=active_seq,
                status='draft',
                invoice_date=tanggal,
            )
            CustomerInvoiceLine.objects.create(
                invoice_id=invoice,
                name=str(unit),
                qty=1,
                price=harga_jual,
            )
            # Compute summary + payment summary
            invoice._compute_summary()
            invoice._compute_payment_summary()
            invoice.save()

            # Line baru di Detail Unit (tab unit_details)
            from core.models.project.project_unit_detail import ProjectUnitDetail
            ProjectUnitDetail.objects.create(
                project_id=self,
                name=str(customer),
                unit_id=unit,
                selling_price=harga_jual,
            )

            # Update Unit Terjual di tab Progress Penjualan
            project_unit.qty_sold = sold + 1
            project_unit.save()  # _run_compute → sold_percentage

        return {
            '_action_type': 'open_record',
            'model': 'accounting.customer_invoice',
            'record_id': invoice.pk,
            'message': f'Faktur dibuat: {invoice.reference or f"#{invoice.pk}"} — line baru di Detail Unit.',
        }
