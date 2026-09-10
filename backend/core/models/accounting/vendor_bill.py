from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel, ErpModelBase


class VendorBill(BaseModel):
    _model_name = 'accounting.vendor_bill'
    _display_name = 'reference'

    # ── State Machine ──
    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
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
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'sequence_id': Many2OneField(
            label='Sequence',
            relation='settings.sequence',
            help_text='Pilih format nomor dokumen tagihan',
        ),
        'reference': CharField(label='Referensi', required=True, editable_statuses=[], placeholder='Otomatis'),
        'vendor': Many2OneField(
            label='Vendor',
            relation='purchase.vendor',
            required=True,
            autofill={'address': 'address', 'code': 'code'},
        ),
        'address': TextField(label='Alamat Vendor', virtual=True),
        'code': TextField(label='Kode Vendor', virtual=True),
        'bill_date': DateField(label='Tanggal Tagihan'),
        'due_date': DateField(label='Jatuh Tempo'),
        'description': TextField(label='Deskripsi'),
        'notes': TextField(label='Catatan', chatter_show=False),
        'purchase_order': Many2OneField(
            label='Purchase Order',
            relation='purchase.order',
            required=False,
        ),
        'quick_purchase': Many2OneField(
            label='Quick Purchase',
            relation='purchase.quick_purchase',
            required=False,
        ),
        'project': Many2OneField(
            label='Project',
            relation='project.project',
            required=False,
            help_text='Project asal tagihan (otomatis dari wizard Buat Tagihan)',
        ),
        'project_line': Many2OneField(
            label='Milestone',
            relation='project.project_line',
            required=False,
            help_text='Milestone terkait (otomatis dari wizard Buat Tagihan)',
        ),
        'milestone_line': Many2OneField(
            label='Baris Milestone',
            relation='project.milestone_line',
            required=False,
            help_text='Sub-line milestone terkait (dari wizard Buat Tagihan)',
        ),

        # ── Down Payment ──
        'is_down_payment': BooleanField(label='Tagihan DP', default=False),
        'deduct_dp': BooleanField(
            label='Potong DP dari Tagihan ini',
            default=False,
            help_text='Kurangi jumlah DP PO dari total tagihan ini (dicentang via wizard Buat Tagihan mode Regular).',
        ),
        'down_payment_amount': MonetaryField(label='Jumlah DP', currency='IDR',
            compute='_compute_down_payment', depends=['purchase_order', 'deduct_dp']),

        # ── Summary fields ──
        'subtotal': MonetaryField(label='Subtotal', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'discount': MonetaryField(label='Diskon', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'tax': MonetaryField(label='Pajak', currency='IDR',
            compute='_compute_summary', depends=['bill_lines']),
        'manual_discount': FloatField(label='Diskon Manual (%)', default=0),
        'grand_total': MonetaryField(label='Grand Total', currency='IDR',
            compute='_compute_summary', depends=['bill_lines', 'manual_discount', 'down_payment_amount']),

        # ── Payment fields ──
        'due_amount': MonetaryField(label='Sisa Tagihan', currency='IDR',
            compute='_compute_payment_summary', depends=['grand_total', 'paid_amount']),
        'paid_amount': MonetaryField(label='Sudah Dibayar', currency='IDR', default=0),
        'payment_status': SelectionField(
            label='Status Pembayaran',
            options=[('unpaid', 'Belum Dibayar'), ('partial', 'Sebagian'), ('paid', 'Lunas')],
            compute='_compute_payment_summary',
            depends=['grand_total', 'paid_amount'],
            default='unpaid',
            colors={'unpaid': 'red', 'partial': 'orange', 'paid': 'green'},
        ),

        'bill_lines': One2ManyField(
            label='Baris Tagihan',
            relation='accounting.vendor_bill_line',
            inverse_field='bill_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'project', 'project_line', 'purchase_order', 'vendor', 'bill_date', 'due_date', 'status', 'grand_total', 'due_amount', 'payment_status'],
        'filters': ['status', 'vendor', 'bill_date', 'payment_status', 'project', 'project_line'],
        'group_by': ['status', 'vendor', 'payment_status', 'project', 'project_line'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['reference', 'project', 'project_line', 'purchase_order', 'vendor', 'code', 'address',
                               'bill_date', 'due_date', 'sequence_id'],
                },
                {
                    'key': 'details',
                    'label': 'Detail',
                    'fields': ['notes'],
                },
            ],
            'smart_buttons': [
            {'label': 'Purchase Order', 'model': 'purchase.order', 'icon': 'FileTextOutlined'},
        ],
        'actions': [
            {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
            {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
            {'label': 'Proses Pembayaran', 'color': 'primary', 'action': 'process_payment', 'states': ['confirmed'],
             'hide_when_paid': True,
             'guard': '_guard_process_payment', 'wizard': {
                'title': 'Proses Pembayaran',
                'modes': [
                    {
                        'value': 'payment',
                        'label': 'Proses Pembayaran',
                        'icon': 'SendOutlined',
                        'row_info': {
                            'title': 'Informasi Tagihan',
                            'fields': [],
                            'remaining': {
                                'label': 'Sisa Tagihan',
                                'field': 'due_amount',
                                'input': 'nominal',
                                'currency': 'Rp ',
                                'done_text': 'lunas',
                            },
                        },
                        'inputs': [
                            {'key': 'nominal', 'label': 'Nominal Pembayaran', 'type': 'number', 'min': 0,
                             'default_from_field': 'due_amount'},
                            {'key': 'payment_method', 'label': 'Metode Pembayaran', 'type': 'many2one', 'relation': 'accounting.payment_method'},
                            {'key': 'payment_date', 'label': 'Tanggal Pembayaran', 'type': 'date', 'default': 'today', 'min_date_from': 'bill_date'},
                            {'key': 'payment_ref', 'label': 'Ref Pembayaran', 'type': 'text'},
                            {'key': 'mark_paid', 'label': 'Tandai Lunas', 'type': 'boolean',
                             'show_if': {'field': '_has_remaining', 'value': True}},
                            {'key': 'diff_account', 'label': 'Akun Selisih (COA)', 'type': 'many2one', 'relation': 'accounting.chart_of_account',
                             'show_if': {'field': 'mark_paid', 'value': True},
                             'help': 'Wajib dipilih jika Tandai Lunas aktif.'},
                        ],
                    },
                ],
             }},
            {'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'primary', 'action': 'cancel', 'states': ['draft', 'confirmed']},
            {'label': 'Action', 'icon': 'MoreOutlined', 'color': 'primary'},
        ],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Baris Tagihan',
                'relation': 'bill_lines',
                'summary': {
                    'columns': {'qty': 'sum', 'discount_percentage': 'avg', 'discount_amount': 'sum',
                                'tax_amount': 'sum', 'total': 'sum'},
                    'subtotal': 'subtotal',
                    'lines': ['discount', 'manual_discount', 'tax', 'down_payment_amount'],
                    'inputs': ['manual_discount'],
                    'grand_total': 'grand_total',
                    'after_grand_total': ['due_amount'],
                    'child_details': [
                        {
                            'label': 'Pembayaran',
                            'data_key': '_payment_details',
                            'model': 'accounting.vendor_payment',
                        },
                        {
                            'label': 'Refund',
                            'data_key': '_refund_details',
                            'model': 'accounting.refund',
                        },
                    ],
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Tagihan'
        verbose_name_plural = 'Tagihan'

    @classmethod
    def get_model_config(cls):
        """Override: inject default sequence_id dari active sequence."""
        config = super().get_model_config()
        from core.models.settings.sequence import Sequence
        active_seq = Sequence.objects.filter(model_ref='accounting.vendor_bill', active=True, is_deleted=False).first()
        if active_seq:
            config['fields']['sequence_id']['default'] = active_seq.pk
        return config

    # ── Guards ──

    def _guard_confirm(self):
        if not self.sequence_id:
            raise ValueError('Silakan pilih Sequence terlebih dahulu.')

    # ── Effects ──

    def _effect_confirm(self):
        from core.sequence_engine import SequenceEngine
        if (self.reference or '').startswith('Draft#'):
            self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)

    # ── Computed Fields ──

    def _bill_line_components(self):
        """Iterator (gross, disc_amount, tax_ids) per baris tagihan.

        Sumber: payload _tmp_one2many (belum disimpan) atau DB. Dipakai compute
        summary agar porsi include tax bisa dikeluarkan dari subtotal (include
        tidak menambah total tagihan).
        """
        from core.models.accounting.tax import _norm_tax_ids
        lines_data = getattr(self, '_tmp_one2many', {}).get('bill_lines', [])
        if lines_data:
            for l in lines_data:
                qty = float(l.get('qty', 0) or 0)
                price = float(l.get('price', 0) or 0)
                disc = float(l.get('discount_amount', 0) or 0)
                if not disc:
                    pct = float(l.get('discount_percentage', 0) or 0)
                    disc = qty * price * (pct / 100)
                yield (qty * price, disc, _norm_tax_ids(l.get('taxes')))
            return
        fd = self._field_descriptors.get('bill_lines')
        if self.pk and fd:
            child_model = ErpModelBase._model_registry.get(fd.relation)
            if child_model:
                for line in child_model.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                ):
                    gross = float(line.qty or 0) * float(line.price or 0)
                    tid = getattr(line, 'taxes_id', None)
                    yield (gross, float(line.discount_amount or 0), [tid] if tid else [])

    def _compute_summary(self):
        from core.models.accounting.tax import line_tax_parts

        gross_sum = disc_sum = inc_sum = exc_sum = 0.0
        for gross, disc_amt, tax_ids in self._bill_line_components():
            inc_t, exc_t, _net = line_tax_parts(gross - disc_amt, tax_ids)
            gross_sum += gross
            disc_sum += disc_amt
            inc_sum += inc_t
            exc_sum += exc_t

        # Subtotal tampil = harga dikurangi porsi include tax (DPP); untuk baris
        # tanpa include nilainya tetap Σ qty×price seperti sebelumnya.
        raw_subtotal = gross_sum - inc_sum

        # Manual discount applied to pre-tax base
        manual_disc_pct = float(getattr(self, 'manual_discount', 0) or 0)
        after_line_disc = raw_subtotal - disc_sum
        manual_disc_amt = after_line_disc * (manual_disc_pct / 100)

        self.subtotal = raw_subtotal
        self.discount = disc_sum
        self.tax = inc_sum + exc_sum
        dp_amount = float(getattr(self, 'down_payment_amount', 0) or 0)
        # grand = subtotal − diskon − diskon manual + pajak − DP; karena subtotal
        # sudah bebas include tax, porsi include tidak menambah total tagihan.
        self.grand_total = after_line_disc - manual_disc_amt + (inc_sum + exc_sum) - dp_amount

    def _compute_down_payment(self):
        """Hitung jumlah DP PO yang dipotong dari tagihan ini.

        DP hanya dipotong bila tagihan ini di-opt-in (`deduct_dp=True`) — diatur
        lewat wizard Buat Tagihan mode Regular (checklist DP). Tanpa opt-in,
        tagihan regular TIDAK otomatis mengurangi DP (mencegah grand_total
        minus saat tagihan dibuat parsial).
        """
        if (not self.purchase_order or self.is_down_payment or not self.deduct_dp):
            self.down_payment_amount = 0
            return
        dp_bills = self.__class__.objects.filter(
            purchase_order=self.purchase_order,
            is_down_payment=True,
            is_deleted=False,
        ).exclude(status='cancelled')
        self.down_payment_amount = sum(float(b.grand_total or 0) for b in dp_bills)

    # ── Refund terkait (dari pembayaran tagihan ini) ──

    def _refund_payment_ids(self):
        """Id vendor_payment yang mengalokasikan ke tagihan ini (exclude cancelled)."""
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        return list(
            VendorPaymentLine.objects.filter(
                bill_id=self.pk, is_deleted=False
            ).exclude(payment_id__status='cancelled')
            .values_list('payment_id', flat=True).distinct()
        )

    def _refunded_total(self):
        """Total refund pembayaran tagihan ini — mengurangi pembayaran efektif."""
        from django.db.models import Sum
        from core.models.accounting.refund import Refund
        ids = self._refund_payment_ids()
        if not ids:
            return 0.0
        total = Refund.objects.filter(
            is_deleted=False, vendor_payment_id__in=ids
        ).aggregate(t=Sum('amount'))['t'] or 0
        return float(total)

    def _refund_rows(self):
        """Refund (aktif) yang menempel pada pembayaran tagihan ini."""
        from core.models.accounting.refund import Refund
        ids = self._refund_payment_ids()
        if not ids:
            return []
        return list(Refund.objects.filter(
            is_deleted=False, vendor_payment_id__in=ids
        ).order_by('refund_date', 'id'))

    def _compute_payment_summary(self):
        """Hitung due_amount & payment_status — pembayaran efektif = paid − refund."""
        paid = float(getattr(self, 'paid_amount', 0) or 0)
        refunded = self._refunded_total()
        effective_paid = max(paid - refunded, 0)
        grand = float(getattr(self, 'grand_total', 0) or 0)
        self.due_amount = max(grand - effective_paid, 0)
        if effective_paid <= 0:
            self.payment_status = 'unpaid'
        elif effective_paid >= grand:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'

    # ── Auto Progress Milestone ──

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_milestone_progress()

    def _sync_milestone_progress(self):
        """Auto-update progress milestone = rata-rata kontribusi semua dokumen aktif.

        Kontribusi per bill: draft 10% / confirmed 50% / paid 100%.
        Bill cancelled di-exclude; kalau tidak ada dokumen aktif → progress 0.
        """
        line = self.project_line
        if not line:
            return

        bills = self.__class__.objects.filter(
            project_line=line, is_deleted=False
        ).exclude(status='cancelled')
        if not bills.exists():
            line.progress = 0.0
            line.save(update_fields=['progress'])
            return

        total = sum(
            100.0 if b.payment_status == 'paid'
            else 50.0 if b.status == 'confirmed'
            else 10.0
            for b in bills
        )
        avg = total / bills.count()
        line.progress = round(avg, 1)
        line.save(update_fields=['progress'])

    # ── Action: Proses Pembayaran (langsung dari Tagihan) ──

    def _guard_process_payment(self):
        """Proses Pembayaran hanya untuk Tagihan Confirmed yang masih punya sisa.

        Dipanggil otomatis oleh core (config `guard` pada action) SEBELUM
        wizard dibuka (precheck) maupun sebelum action dieksekusi. Kalau
        gagal, frontend menampilkan notif dan popup tidak dibuka.
        """
        if getattr(self, 'status', None) != 'confirmed':
            raise ValueError(
                'Pembayaran hanya bisa diinput untuk Tagihan berstatus Confirmed.'
            )
        if float(self.due_amount or 0) <= 0:
            raise ValueError(
                'Tagihan ini sudah Lunas — tidak ada sisa tagihan yang bisa dibayar.'
            )

    def _action_process_payment(self, data=None):
        """Buat VendorPayment (draft) untuk tagihan ini, lalu open record.

        Dipicu tombol 'Proses Pembayaran' di header Tagihan → wizard input
        nominal (0 = lunas / parsial), metode, tanggal, ref pembayaran.
        Vendor/No Tagihan/Sisa ditampilkan otomatis dari bill ini.

        Selisih nominal vs sisa tagihan (kurang bayar) ditangani lewat flag
        `mark_paid` (wizard 'Tandai Lunas'):
          - mark_paid false → nominal dibayar sebagian, tagihan tetap Sebagian
          - mark_paid true (+ `diff_account`) → selisih diakui ke akun COA,
            alokasi penuh sisa → tagihan Lunas saat Confirm
        Lebih bayar: tanpa mapping kelebihan mengendap sebagai Sisa Alokasi
        pembayaran; dengan mark_paid + akun, kelebihan dicatat ke akun COA.

        Payment dibuat & langsung dikonfirmasi otomatis (efek di
        vendor_payment) — paid_amount tagihan ter-update & status jadi Lunas/
        Sebagian seketika.
        """
        from django.db import transaction
        from core.models.accounting.vendor_payment import VendorPayment
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        from core.models.settings.sequence import Sequence

        self._guard_process_payment()

        remaining = float(self.due_amount or 0)
        amount = float((data or {}).get('nominal') or 0)
        if amount <= 0:
            amount = remaining  # 0/kosong → lunasi sisa

        mark_paid = bool((data or {}).get('mark_paid'))
        diff_account = (data or {}).get('diff_account') or None

        # ── Hitung alokasi line, total kas, & selisih mapping ──
        diff_amount = 0.0
        allocation = amount   # nilai yang dialokasikan ke bill ini (line)
        total = amount        # total kas pada dokumen pembayaran
        if amount < remaining - 0.005:
            if mark_paid:
                # Kurang bayar + Tandai Lunas: selisih diakui ke akun COA,
                # bill dialokasi penuh sisa (kas + selisih dari akun) → Lunas.
                if not diff_account:
                    raise ValueError('Pilih Akun Selisih (COA) untuk menandai Lunas.')
                diff_amount = remaining - amount
                allocation = remaining
                total = remaining
        elif amount > remaining + 0.005:
            if mark_paid:
                # Lebih bayar + Tandai Lunas: kelebihan dicatat ke akun COA.
                if not diff_account:
                    raise ValueError('Pilih Akun Selisih (COA) untuk menandai Lunas.')
                diff_amount = amount - remaining
                allocation = remaining
                total = amount
            else:
                # Lebih bayar tanpa mapping: hanya sisa yang dialokasikan;
                # kelebihan mengendap sebagai Sisa Alokasi pembayaran.
                allocation = remaining
                total = amount
        # amount == remaining (±toleransi) → lunas penuh, tanpa selisih.

        payment_date = ((data or {}).get('payment_date') or '').strip()
        if not payment_date:
            raise ValueError('Tanggal Pembayaran wajib diisi.')
        payment_method = (data or {}).get('payment_method') or None
        if not payment_method:
            raise ValueError('Metode Pembayaran wajib diisi.')

        active_seq = Sequence.objects.filter(
            model_ref='accounting.vendor_payment', active=True, is_deleted=False
        ).first()
        if not active_seq:
            raise ValueError(
                'Tidak ada Sequence aktif untuk Pembayaran — aktifkan sequence terlebih dahulu.'
            )

        with transaction.atomic():
            payment = VendorPayment.objects.create(
                vendor=self.vendor,
                status='draft',
                sequence_id=active_seq,
                payment_date=payment_date,
                payment_method_id=int(payment_method),
                payment_ref=((data or {}).get('payment_ref') or '').strip(),
                currency='IDR',
                total_amount=total,
                difference_amount=diff_amount,
                difference_account_id=int(diff_account) if diff_account else None,
            )
            VendorPaymentLine.objects.create(
                payment_id=payment,
                bill_id=self,
                paid_amount=allocation,
            )
            # Langsung konfirmasi (bukan draft): nomor resmi diterbitkan &
            # paid_amount/status tagihan ter-update seketika.
            payment.status = 'confirmed'
            payment._effect_confirm()
            payment.save()

        msg = 'Pembayaran dibuat & otomatis dikonfirmasi — status tagihan ter-update.'
        if diff_amount > 0 and mark_paid:
            arah = 'kurang' if amount < remaining else 'lebih'
            msg = (
                f'Tagihan ditandai Lunas — selisih {arah} bayar Rp {diff_amount:,.0f} '
                f'dimapping ke akun. Pembayaran otomatis dikonfirmasi.'
            )
        elif amount > remaining + 0.005:
            msg = (
                'Pembayaran dibuat & otomatis dikonfirmasi — kelebihan tidak dimapping '
                '& tersimpan sebagai Sisa Alokasi.'
            )

        return {
            '_action_type': 'open_record',
            'model': 'accounting.vendor_payment',
            'record_id': payment.pk,
            'message': msg,
        }

    # ── Legacy Actions ──

    def _action_print(self, *args, **kwargs):
        return {
            '_action_type': 'print_preview',
            'url': f'/api/print/accounting.vendor_bill/{self.pk}/preview/',
            'pdf_url': f'/api/print/accounting.vendor_bill/{self.pk}/download/',
        }

    def _print_context(self):
        data = super()._print_context()
        from core.models.accounting.tax import _norm_tax_ids, line_tax_parts
        lines = data.get('bill_lines', [])
        gross_sum = disc_sum = inc_sum = exc_sum = 0.0
        for line in lines:
            qty = float(line.get('qty', 0) or 0)
            price = float(line.get('price', 0) or 0)
            gross = qty * price
            disc = float(line.get('discount_amount', 0) or 0)
            if not disc:
                pct = float(line.get('discount_percentage', 0) or 0)
                disc = gross * (pct / 100)
            inc_t, exc_t, _n = line_tax_parts(gross - disc, _norm_tax_ids(line.get('taxes')))
            gross_sum += gross
            disc_sum += disc
            inc_sum += inc_t
            exc_sum += exc_t
        manual_disc_pct = float(data.get('manual_discount', 0) or 0)
        dp_amount = float(data.get('down_payment_amount', 0) or 0)

        # Subtotal = harga − porsi include tax (DPP); include tidak menambah total.
        data['subtotal'] = gross_sum - inc_sum
        data['discount'] = disc_sum
        data['tax'] = inc_sum + exc_sum
        data['manual_discount'] = (gross_sum - inc_sum - disc_sum) * (manual_disc_pct / 100)
        data['grand_total'] = (gross_sum - inc_sum - disc_sum - data['manual_discount']
                               + inc_sum + exc_sum - dp_amount)
        return data

    def to_record(self):
        """Sertakan daftar payment terkait untuk child_details di summary."""
        data = super().to_record()
        from core.models.accounting.vendor_payment_line import VendorPaymentLine
        lines = VendorPaymentLine.objects.filter(
            bill_id=self.pk, is_deleted=False
        ).exclude(payment_id__status='cancelled').order_by('pk')
        data['_payment_details'] = []
        for line in lines:
            p = line.payment_id
            data['_payment_details'].append({
                'id': p.pk,
                'label': 'Pembayaran',
                'ref': p.reference or f'#{p.pk}',
                'amount': float(line.paid_amount or 0),
            })
        # Refund pembayaran — ditampilkan minus (mengurangi pembayaran efektif)
        data['_refund_details'] = [
            {
                'id': r.pk,
                'label': 'Refund',
                'ref': r.reference or f'#{r.pk}',
                'amount': -float(r.amount or 0),
            }
            for r in self._refund_rows()
        ]
        return data
