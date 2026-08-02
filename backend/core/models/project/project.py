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
            help_text='Kategori proyek dari master Project Categories',
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
            label='Project Lines',
            relation='project.project_line',
            inverse_field='project_id',
        ),
        'units': One2ManyField(
            label='Project Units',
            relation='project.project_unit',
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
                    'label': 'General',
                    'fields': ['name', 'category', 'date_start', 'date_end'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['project_manager', 'contract_value', 'client', 'location', 'executing_entity'],
                },
            ],
            'actions': [
                {
                    'label': 'Update Progress',
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
                    'goto_tab': 'units',
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Project Milestones',
                'relation': 'lines',
                'columns': ['milestone_id', 'progress'],
                'row_actions': [
                    {
                        'label': 'Update Progress',
                        'actions': [
                            {
                                'label': 'Update Progress',
                                'action': 'update_progress',
                                'wizard': {
                                    'title': 'Update Progress',
                                    'modes': [
                                        {
                                            'value': 'buat_tagihan',
                                            'label': 'Buat Tagihan',
                                            'icon': 'FileTextOutlined',
                                            'inputs': [
                                                {'key': 'vendor', 'label': 'Vendor', 'type': 'many2one', 'relation': 'purchase.vendor'},
                                                {'key': 'bill_date', 'label': 'Bill Date', 'type': 'date'},
                                                {'key': 'due_date', 'label': 'Due Date', 'type': 'date'},
                                                {'key': 'amount', 'label': 'Nominal (Rp)', 'type': 'number', 'default': 0},
                                                {'key': 'description', 'label': 'Deskripsi', 'type': 'text'},
                                            ],
                                        },
                                        {
                                            'value': 'input_expenses',
                                            'label': 'Input Expenses',
                                            'icon': 'SendOutlined',
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
                'label': 'Unit',
                'relation': 'units',
                'columns': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

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
            return {'message': 'Input Expenses belum diimplementasikan.'}
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

    def _action_input_sales(self, data=None):
        """Input penjualan unit — set qty_sold (sold_percentage recompute otomatis)."""
        from core.model_meta import ErpModelBase

        selected_lines_raw = (data or {}).get('selected_lines')
        if not selected_lines_raw or not isinstance(selected_lines_raw, list):
            return {'error': 'Tidak ada baris yang dipilih.'}

        fd = self._field_descriptors.get('units')
        if not fd:
            return {'error': 'Konfigurasi units tidak ditemukan.'}
        unit_model = ErpModelBase._model_registry.get(fd.relation)
        if not unit_model:
            return {'error': 'Model project.project_unit tidak ditemukan.'}

        updated = 0
        for item in selected_lines_raw:
            lid = item.get('id')
            if lid is None:
                continue
            value = float(item.get('qty', 0) or 0)
            unit = unit_model.objects.filter(
                pk=int(lid), project_id=self.pk, is_deleted=False
            ).first()
            if not unit:
                continue
            unit.qty_sold = value
            unit.save()  # _run_compute → sold_percentage
            updated += 1

        return {'message': f'Penjualan diinput untuk {updated} unit.'}
