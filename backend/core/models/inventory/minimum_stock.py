"""Minimum Stock — batas stok minimum per Produk per Gudang.

Aturan:
  * `min_qty`      : stok minimum yang harus tersedia di gudang tersebut.
  * `max_qty`      : stok maksimum yang diinginkan (input user).
  * Qty order      : OTOMATIS = max_qty - on_hand (saat stok di bawah minimum).
  * `location`     : many2many lokasi (otomatis terisi semua lokasi gudang
                     terpilih, tetap bisa ditambah/dikurangi user).
  * `on_hand`      : total stok dari lokasi terpilih (otomatis).
  * `action_type`  : dokumen yang dibuat otomatis saat di bawah stok —
                     'pr' = Purchase Request, 'po' = Draft Purchase Order.
  * `auto_vendor`  : vendor untuk draft PO (many2one ke master Vendor).
  * `notify_users` : many2many user penerima email notifikasi.

Otomatisasi dipanggil dari StockEngine setiap ada pergerakan stok
(`check_and_fulfill`) — dokumen order dibuat hanya bila stok di bawah minimum
dan belum ada dokumen auto-order yang masih terbuka.
"""
from datetime import date

from django.db import models
from core.fields import (
    CharField, TextField, FloatField, BooleanField, SelectionField,
    Many2OneField, Many2ManyField,
)
from core.model_meta import BaseModel


class MinimumStock(BaseModel):
    _model_name = 'inventory.minimum_stock'
    _display_name = 'name'

    # ── Smart button: dokumen yang lahir dari aturan ini ──
    _document_flow = {
        'children': [
            {
                'model': 'purchase.request',
                'label': 'Purchase Request',
                'icon': 'FileTextOutlined',
                'source_field_in_child': 'minimum_stock',
            },
            {
                'model': 'purchase.order',
                'label': 'Purchase Order',
                'icon': 'ShoppingCartOutlined',
                'source_field_in_child': 'minimum_stock',
            },
        ],
    }

    _fields = {
        'name': CharField(
            label='Nama Aturan', required=True,
            editable_statuses=[], placeholder='Otomatis',
        ),
        'product': Many2OneField(
            label='Produk',
            relation='inventory.product',
            required=True,
            autofill={'name': 'name'},
        ),
        'warehouse': Many2OneField(
            label='Gudang',
            relation='inventory.warehouse',
            required=True,
            # Pilih Gudang → Lokasi otomatis terisi semua lokasi gudang tsb.
            autofill={'location': 'locations'},
        ),
        'location': Many2ManyField(
            label='Lokasi',
            relation='inventory.warehouse_location',
            help_text='Otomatis terisi semua lokasi gudang; bisa diubah',
        ),
        'is_active': BooleanField(label='Aktif', default=True),
        'min_qty': FloatField(
            label='Minimum Stock', required=True, default=0,
            help_text='Stok minimum yang harus tersedia di gudang ini',
        ),
        'max_qty': FloatField(
            label='Maximum Stock', required=True, default=0,
            help_text='Stok maksimum — qty order otomatis = Maximum Stock - Stock Saat Ini',
        ),
        'on_hand': FloatField(
            label='Stock Saat Ini', default=0,
            compute='_compute_stock',
            depends=['product', 'location'],
            editable_statuses=[],
            help_text='Total stok dari lokasi terpilih',
        ),
        'below_min': BooleanField(
            label='Di Bawah Minimum', default=False,
            compute='_compute_stock',
            depends=['product', 'location', 'min_qty'],
            editable_statuses=[],
        ),
        'action_type': SelectionField(
            label='Aksi Otomatis Jika Di Bawah Stok',
            required=True,
            default='pr',
            options=[
                ('pr', 'Buat Purchase Request'),
                ('po', 'Buat Draft Purchase Order'),
            ],
        ),
        'auto_vendor': Many2OneField(
            label='Auto Order Vendor',
            relation='purchase.vendor',
            help_text='Vendor yang dipakai saat membuat draft PO otomatis',
        ),
        'notify_users': Many2ManyField(
            label='Email Notifikasi',
            relation='settings.user',
            help_text='User yang dikirimi email saat stok di bawah minimum',
        ),
        'notes': TextField(label='Catatan'),
    }

    _list_view = {
        'columns': [
            'product', 'warehouse', 'min_qty', 'max_qty',
            'on_hand', 'below_min', 'action_type', 'is_active',
        ],
        'filters': ['product', 'warehouse', 'below_min', 'is_active', 'action_type'],
        'default_sort': ['product'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': [
                        'name', 'product', 'warehouse', 'location', 'is_active',
                        'min_qty', 'max_qty', 'on_hand', 'below_min',
                    ],
                },
                {
                    'key': 'automation',
                    'label': 'Otomatisasi',
                    'fields': ['action_type', 'auto_vendor', 'notify_users'],
                },
                {
                    'key': 'details',
                    'label': 'Catatan',
                    'fields': ['notes'],
                },
            ],
            'actions': [
                {
                    'label': 'Proses Automation',
                    'color': 'primary',
                    'action': 'run_order',
                    'guard': '_guard_run_order',
                },
                {
                    'label': 'Cek Stok',
                    'color': 'default',
                    'action': 'check_stock',
                },
            ],
            'smart_buttons': [
                {
                    'label': 'Purchase Request', 'model': 'purchase.request',
                    'icon': 'FileTextOutlined',
                    'preview_columns': ['reference', 'request_date', 'status'],
                },
                {
                    'label': 'Purchase Order', 'model': 'purchase.order',
                    'icon': 'ShoppingCartOutlined',
                    'preview_columns': ['reference', 'vendor', 'order_date', 'status'],
                },
            ],
        },
    }

    _actions_menu = [
        {'key': 'run_order', 'label': 'Proses Automation', 'icon': 'ThunderboltOutlined', 'action': 'run_order'},
    ]

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Minimum Stock'
        verbose_name_plural = 'Minimum Stock'

    def __str__(self):
        return self.name or f'MinStock#{self.pk}'

    # ── Konfigurasi field (generik, dibaca frontend) ─────────────────────────

    @classmethod
    def get_model_config(cls):
        config = super().get_model_config()
        # Ganti Produk / Gudang / Min / Max → hitung ulang Stock Saat Ini &
        # Di Bawah Minimum lewat compute API.
        refresh_stock = [
            {'field': 'on_hand', 'refresh': True},
            {'field': 'below_min', 'refresh': True},
        ]
        config['field_config_rules'] = {
            'product': {'compute_fields': list(refresh_stock)},
            'warehouse': {'compute_fields': list(refresh_stock)},
            'min_qty': {'compute_fields': [{'field': 'below_min', 'refresh': True}]},
            'max_qty': {'compute_fields': [{'field': 'below_min', 'refresh': True}]},
        }
        return config

    # ── Simpan ──────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        # Anti-duplikat: 1 produk hanya boleh 1 aturan per gudang.
        if self.product_id and self.warehouse_id:
            dup = type(self).objects.filter(
                product_id=self.product_id,
                warehouse_id=self.warehouse_id,
                is_deleted=False,
            )
            if self.pk:
                dup = dup.exclude(pk=self.pk)
            other = dup.first()
            if other:
                raise ValueError(
                    f'Gudang "{self.warehouse}" sudah memiliki aturan Minimum Stock '
                    f'untuk produk "{self.product}": {other.name or ("MinStock#" + str(other.pk))} '
                    f'(#{other.pk}). Hapus/ubah data tersebut terlebih dahulu.'
                )
        if not self.name:
            self.name = self._build_name()
        super().save(*args, **kwargs)
        # Lokasi belum dipilih → default semua lokasi gudang terpilih.
        if self.warehouse_id and not self._selected_location_ids():
            ids = self._warehouse_location_ids()
            if ids:
                self.location.set(ids)

    def _build_name(self):
        """Nama aturan = gabungan Produk + Gudang + jumlah Lokasi (ringkas)."""
        prod = str(self.product) if self.product_id else ''
        wh = str(self.warehouse) if self.warehouse_id else ''
        n_loc = len(self._selected_location_ids()) or len(self._warehouse_location_ids())
        parts = [p for p in (prod, wh) if p]
        base = ' · '.join(parts)
        if n_loc:
            base = f'{base} ({n_loc} lokasi)' if base else f'{n_loc} lokasi'
        return base or f'MinStock#{self.pk or ""}'

    # ── Compute ─────────────────────────────────────────────────────────────

    def _location_model(self):
        from core.model_meta import ErpModelBase
        return ErpModelBase._model_registry.get('inventory.warehouse_location')

    def _warehouse_location_ids(self):
        """Semua pk lokasi milik gudang terpilih."""
        if not self.warehouse_id:
            return []
        loc_cls = self._location_model()
        if loc_cls is None:
            return []
        try:
            return list(
                loc_cls.objects.filter(warehouse_id_id=self.warehouse_id, is_deleted=False)
                .values_list('pk', flat=True)
            )
        except Exception:
            return []

    def _selected_location_ids(self):
        """pk lokasi yang dipilih di field Lokasi (many2many)."""
        return self._m2m_ids('location') if self.pk else []

    def _compute_stock(self):
        """on_hand = total stok lokasi terpilih; below_min = on_hand < min_qty."""
        from core.stock_engine import StockEngine
        location_ids = self._selected_location_ids() or self._warehouse_location_ids()
        total = 0.0
        if self.product_id and location_ids:
            for lid in location_ids:
                try:
                    total += float(StockEngine.on_hand(self.product_id, lid) or 0)
                except Exception:
                    continue
        self.on_hand = round(total, 3)
        self.below_min = total < float(self.min_qty or 0)
        return self.on_hand

    # ── Guard ───────────────────────────────────────────────────────────────

    def _guard_run_order(self):
        if not self.pk:
            raise ValueError('Simpan aturan Minimum Stock terlebih dahulu.')
        if not self.product_id or not self.warehouse_id:
            raise ValueError('Produk dan Gudang wajib diisi.')
        if self._order_qty_value() <= 0:
            raise ValueError(
                'Qty order 0 — Maximum Stock harus lebih besar dari Stock Saat Ini.'
            )

    # ── Aksi (manual, dari tombol header / menu Fitur) ───────────────────────

    def _action_run_order(self, data=None):
        """Jalankan order sesuai `action_type` (pr / po)."""
        if (self.action_type or 'pr') == 'po':
            return self._action_create_po(data)
        return self._action_create_pr(data)

    def _action_check_stock(self, data=None):
        """Hitung ulang stok dari lokasi terpilih (tanpa membuat dokumen)."""
        self._compute_stock()
        self.save()
        if self.below_min:
            msg = (f'Stock di bawah minimum: {self.on_hand:g} < {float(self.min_qty or 0):g} '
                   f'(qty order {self._order_qty_value():g}).')
        else:
            msg = f'Stock aman: {self.on_hand:g} (minimum {float(self.min_qty or 0):g}).'
        return {'message': msg, '_action_type': 'refresh'}

    def _action_create_pr(self, data=None):
        """Buat Purchase Request draft otomatis (1 baris, qty = max - on_hand)."""
        return self._auto_fulfill(force=True)

    def _action_create_po(self, data=None):
        """Buat Draft Purchase Order otomatis (1 baris, qty = max - on_hand)."""
        return self._auto_fulfill(force=True, force_action='po')

    # ── Otomatisasi ─────────────────────────────────────────────────────────

    def _order_qty_value(self):
        """Qty order = max_qty - on_hand (minimum 0)."""
        on_hand = float(self.on_hand or 0)
        return max(0.0, round(float(self.max_qty or 0) - on_hand, 3))

    def _marker(self):
        return f'[MINSTOCK#{self.pk}]'

    def _has_open_order(self, action_type):
        """True bila sudah ada dokumen auto-order terbuka dari aturan ini."""
        if not self.pk:
            return False
        try:
            if action_type == 'po':
                from core.models.purchase.purchase_order import PurchaseOrder
                return PurchaseOrder.objects.filter(
                    minimum_stock_id=self.pk, is_deleted=False,
                ).exclude(status__in=['cancelled', 'done']).exists()
            from core.models.purchase.purchase_request import PurchaseRequest
            return PurchaseRequest.objects.filter(
                minimum_stock_id=self.pk, is_deleted=False,
            ).exclude(status='cancelled').exists()
        except Exception:
            return False

    def _auto_fulfill(self, force=False, force_action=None):
        """Buat dokumen order otomatis bila stok di bawah minimum (idempotent)."""
        from django.db import transaction

        action = force_action or (self.action_type or 'pr')
        self._compute_stock()
        qty = self._order_qty_value()

        if qty <= 0:
            return {'error': 'Qty order 0 — Maximum Stock harus lebih besar dari Stock Saat Ini.'}
        if not force and not self.below_min:
            return None
        if self._has_open_order(action):
            return None  # sudah ada dokumen auto-order terbuka → jangan dobel

        note = f'{self._marker()} Auto order {self.product} @ {self.warehouse} (qty {qty:g})'

        if action == 'po':
            from core.models.purchase.purchase_order import PurchaseOrder
            from core.models.purchase.purchase_order_line import PurchaseOrderLine
            from core.models.settings.sequence import Sequence

            vendor_id = self.auto_vendor_id
            if not vendor_id:
                return {'error': 'Belum ada Auto Order Vendor. Isi kolom Auto Order Vendor terlebih dahulu.'}

            seq = Sequence.objects.filter(
                model_ref='purchase.order', active=True, is_deleted=False
            ).first()

            with transaction.atomic():
                po = PurchaseOrder.objects.create(
                    sequence_id=seq,
                    vendor_id=int(vendor_id),
                    status='draft',
                    order_date=date.today(),
                    description=note,
                    minimum_stock_id=self.pk,
                )
                PurchaseOrderLine.objects.create(
                    order_id=po,
                    product=self.product,
                    name=str(self.product) if self.product_id else '',
                    qty=qty,
                )
            self._notify_below_min()
            return {
                'message': f'Draft Purchase Order {po.reference} dibuat otomatis (qty {qty:g}).',
                '_action_type': 'open_record',
                'model': 'purchase.order',
                'record_id': po.pk,
            }

        from core.models.purchase.purchase_request import PurchaseRequest
        from core.models.purchase.purchase_request_line import PurchaseRequestLine
        from core.models.settings.sequence import Sequence

        seq = Sequence.objects.filter(
            model_ref='purchase.request', active=True, is_deleted=False
        ).first()

        with transaction.atomic():
            pr = PurchaseRequest.objects.create(
                sequence_id=seq,
                status='draft',
                requested_by=getattr(self, 'updated_by', None),
                request_date=date.today(),
                notes=note,
                minimum_stock_id=self.pk,
            )
            PurchaseRequestLine.objects.create(
                request_id=pr,
                product=self.product,
                description=str(self.product) if self.product_id else '',
                qty=qty,
            )
        self._notify_below_min()
        return {
            'message': f'Purchase Request {pr.reference} dibuat otomatis (qty {qty:g}).',
            '_action_type': 'open_record',
            'model': 'purchase.request',
            'record_id': pr.pk,
        }

    @classmethod
    def check_and_fulfill(cls, product_ids=None):
        """Dipanggil StockEngine tiap ada pergerakan stok (best-effort)."""
        try:
            rules = cls.objects.filter(is_active=True, is_deleted=False)
            if product_ids:
                rules = rules.filter(product_id__in=list(set(product_ids)))
            for rule in rules:
                try:
                    rule._auto_fulfill()
                except Exception:
                    continue
        except Exception:
            return 0
        return 0

    # ── Email notifikasi ────────────────────────────────────────────────────

    def _notify_below_min(self):
        """Kirim email ke seluruh user di `notify_users` (bila di bawah minimum)."""
        if not self.below_min:
            return 0
        recipients = []
        try:
            for user in self.notify_users.all():
                mail = getattr(user, 'email', '') or ''
                if mail:
                    recipients.append(mail)
        except Exception:
            recipients = []
        if not recipients:
            return 0
        try:
            from django.conf import settings as dj_settings
            from django.core.mail import send_mail
            send_mail(
                subject=f'[Minimum Stock] {self.product} di bawah minimum',
                message=(
                    f'Produk: {self.product}\n'
                    f'Gudang: {self.warehouse}\n'
                    f'Stock saat ini: {self.on_hand:g}\n'
                    f'Minimum: {float(self.min_qty or 0):g}\n'
                    f'Maximum: {float(self.max_qty or 0):g}\n'
                    f'Qty order: {self._order_qty_value():g}\n'
                ),
                from_email=getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=recipients,
                fail_silently=True,
            )
        except Exception:
            return 0
        return len(recipients)
