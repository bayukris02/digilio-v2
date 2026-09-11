"""Pemeliharaan data — hapus (clear) database.

Endpoint:
    GET  /api/maintenance/purge/preview/   → ringkasan yang akan dihapus (tanpa mengubah data)
    POST /api/maintenance/purge/           → jalankan penghapusan {scope, confirm}

Konsep (opsi A — clear in-app):
  * scope 'transactions' : SEMUA dokumen + baris dokumen + pergerakan stok + log chatter
                           (hanya log milik model transaksi — log master data tetap).
  * scope 'master'       : SEMUA master data, menyisakan 1 Company, 1 Branch, dan user
                           (tabel auth tidak pernah disentuh).

Aturan teknis:
  * Penghapusan bersifat HARDDELETE (termasuk baris yang sudah soft-deleted `is_deleted=True`).
  * Sebelum menghapus, isi database di-backup ke `backend/backups/` (best-effort, `dumpdata`).
  * Semua penghapusan dijalankan dalam SATU transaksi database (atomic).
  * Counter nomor dokumen (`settings.sequence_date_range`) dihapus agar penomoran mulai dari 1,
    sedangkan definisi `settings.sequence` DIPERTAHANKAN (konfigurasi penomoran).
  * Nomor ID otomatis (PK `<tabel>_id_seq`) tabel yang dikosongkan ikut di-RESTART ke 1 — sebab
    `DELETE` di PostgreSQL tidak memundurkan sequence (dulu menyebabkan record baru mulai dari
    `Draft#19`). Tabel yang masih berisi baris (mis. Company/Branch yang disisakan) dilewati.
  * Daftar model diambil dari registry `ErpModelBase._model_registry` — model baru otomatis
    masuk kategori bila ditambahkan ke salah satu daftar di bawah.
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings as dj_settings
from django.core.management import call_command
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.model_meta import ErpModelBase
from core.models.chatter_log import ChatterLog
from core.permissions import IsAdmin

# ── Klasifikasi model ────────────────────────────────────────────────────────
# Dokumen / baris dokumen / pergerakan stok (semua yang "transaksional").
TRANSACTION_MODELS = {
    # purchase
    'purchase.request', 'purchase.request.line',
    'purchase.order', 'purchase.order.line',
    'purchase.goods_receipt', 'purchase.goods_receipt.line',
    'purchase.quick_purchase', 'purchase.quick_purchase.line',
    # sales
    'sales.order', 'sales.order.line',
    'sales.delivery_order', 'sales.delivery.order.line',
    'sales.quick_sales', 'sales.quick_sales.line',
    # inventory (pergerakan & dokumen gudang)
    'inventory.stock_request', 'inventory.stock_request.line',
    'inventory.stock_out', 'inventory.stock_out.line',
    'inventory.stock_in', 'inventory.stock_in.line',
    'inventory.stock_adjustment', 'inventory.stock_adjustment.line',
    'inventory.stock_ledger',
    # accounting (dokumen & jurnal)
    'accounting.jurnal', 'accounting.jurnal_line',
    'accounting.vendor_bill', 'accounting.vendor_bill_line',
    'accounting.vendor_payment', 'accounting.vendor_payment_line',
    'accounting.customer_invoice', 'accounting.customer_invoice_line',
    'accounting.customer_invoice_installment',
    'accounting.customer_receipt', 'accounting.customer_receipt_line',
    'accounting.expense', 'accounting.expense_line',
    'accounting.transfer_cash_bank', 'accounting.deposit', 'accounting.refund',
    'accounting.asset', 'accounting.asset_depreciation_line',
    # project (progress / pembayaran unit = transaksi)
    'project.unit_progress', 'project.unit_detail_progress',
    'project.unit_detail_payment', 'project.project_line', 'project.milestone_line',
}

# Master data yang DIPERTAHANKAN saat scope 'master'.
KEEP_MASTER_MODELS = {
    'settings.company',      # disisakan 1 (paling awal)
    'settings.branch',       # disisakan 1 (paling awal, milik company tsb)
    'settings.user',         # tabel auth — TIDAK PERNAH dihapus
    'settings.sequence',     # konfigurasi penomoran (counter-nya yang dihapus)
}

MASTER_SCOPE_DESC = (
    'Hapus SEMUA master data (customer, vendor, produk, gudang, COA, pajak, UOM, '
    'pricelist, project, role/RBAC, dll) beserta log chatter-nya. Disisakan: 1 Company, 1 Branch, '
    'dan seluruh user (tabel auth tidak disentuh). Counter nomor dokumen direset.'
)


_MODULE_LABELS = {
    'purchase': 'Pembelian',
    'sales': 'Penjualan',
    'inventory': 'Stock',
    'accounting': 'Akunting',
    'project': 'Proyek',
    'settings': 'Pengaturan',
}


def _label(model_name: str) -> str:
    """Label manusiawi unik dari nama model: 'purchase.order.line' → 'Pembelian Order Line'."""
    if '.' not in model_name:
        return model_name.replace('_', ' ').title()
    module, rest = model_name.split('.', 1)
    pretty = rest.replace('.', ' ').replace('_', ' ').title()
    return f'{_MODULE_LABELS.get(module, module.title())} {pretty}'


def _registry() -> dict:
    return dict(ErpModelBase._model_registry)


def _model_names_for(scope: str) -> list:
    """Daftar model yang HAPUS BARISNYA untuk sebuah scope (transaksi / master), tanpa duplikat."""
    registry = _registry()
    if scope == 'transactions':
        names = [n for n in TRANSACTION_MODELS if n in registry]
    else:  # master
        names = [
            n for n in registry
            if n not in TRANSACTION_MODELS
            and n not in KEEP_MASTER_MODELS
            and n not in RESET_COUNTER_MODELS   # counter sequence ditangani sebagai RESET, bukan hapus
            and not n.startswith('settings.sequence')   # sequence = konfigurasi, tak pernah dihapus
        ]
    return sorted(dict.fromkeys(names))


# Model yang barisnya bukan "dihapus sebagai data" melainkan RESET counter
# (definisi Sequence TIDAK dihapus — konfigurasi penomoran tetap dipakai).
RESET_COUNTER_MODELS = ['settings.sequence_date_range']


def _reset_counts() -> list:
    """Isi counter nomor dokumen (yang akan direset ke 1 saat clear transaksi)."""
    registry = _registry()
    out = []
    for name in RESET_COUNTER_MODELS:
        cls = registry.get(name)
        if cls is None:
            continue
        count = cls.objects.count()
        if count:
            out.append({'model': name, 'label': 'Counter nomor dokumen (reset ke 1)', 'count': count})
    return out


def _chatter_models_for(scope: str) -> list:
    """Model yang log chatter-nya ikut dibersihkan = model yang datanya dikosongkan scope tsb.

    Chatter TIDAK digabung: clear transaksi hanya menghapus log model transaksi, clear master
    hanya menghapus log model master (log model yang datanya masih ada tetap dipertahankan).
    """
    names = list(_model_names_for(scope))
    if scope == 'transactions':
        names += RESET_COUNTER_MODELS   # counter nomor dokumen ikut dikosongkan
    return sorted(dict.fromkeys(names))


def _chatter_queryset(scope: str):
    return ChatterLog.objects.filter(model_name__in=_chatter_models_for(scope))


def _scope_tables(scope: str) -> list:
    """Daftar tabel DB yang barisnya dikosongkan pada scope tsb (dasar reset nomor ID/PK)."""
    registry = _registry()
    tables = []
    for name in _model_names_for(scope):
        cls = registry.get(name)
        if cls is not None:
            tables.append(cls._meta.db_table)
    if scope == 'transactions':
        tables.append(ChatterLog._meta.db_table)          # log chatter selalu ikut dibersihkan
        for name in RESET_COUNTER_MODELS:                  # counter nomor dokumen (dikosongkan)
            cls = registry.get(name)
            if cls is not None:
                tables.append(cls._meta.db_table)
    return sorted(dict.fromkeys(tables))


def _pk_sequences(tables: list) -> dict:
    """Petakan tabel → nama sequence nomor ID (PK) milik kolom `id`-nya (serial/identity)."""
    from django.db import connection

    found = {}
    with connection.cursor() as cur:
        for table in tables:
            cur.execute('SELECT pg_get_serial_sequence(%s, %s)', [table, 'id'])
            row = cur.fetchone()
            if row and row[0]:
                found[table] = row[0]
    return found


def _reset_pk_sequences(tables: list) -> list:
    """RESTART nomor ID (PK) tabel yang sudah benar-benar kosong → record baru mulai dari 1.

    PostgreSQL: `DELETE` tidak memundurkan sequence, jadi harus di-RESTART eksplisit.
    Tabel yang masih berisi baris dilewati (mis. Company/Branch yang disisakan saat clear master).
    """
    from django.db import connection

    out = []
    with connection.cursor() as cur:
        for table, seq in sorted(_pk_sequences(tables).items()):
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            if cur.fetchone()[0]:
                continue  # masih ada baris → jangan reset
            quoted = '.'.join(f'"{part}"' for part in seq.split('.'))
            cur.execute(f'ALTER SEQUENCE {quoted} RESTART WITH 1')
            out.append({'table': table, 'sequence': seq})
    return out


def _counts(names: list) -> list:
    registry = _registry()
    rows = []
    for name in names:
        cls = registry.get(name)
        if cls is None:
            continue
        count = cls.objects.count()
        if count:
            rows.append({'model': name, 'label': _label(name), 'count': count})
    return sorted(rows, key=lambda r: (-r['count'], r['label']))


def _pick_keep(company_id=None, branch_id=None) -> tuple:
    """Tentukan Company & Branch yang disisakan (pilihan user, fallback yang paling awal)."""
    from core.models.settings.branch import Branch
    from core.models.settings.company import Company

    company = None
    if company_id:
        company = Company.objects.filter(pk=company_id).first()
    if company is None:
        company = Company.objects.order_by('pk').first()

    branch = None
    if company is not None:
        if branch_id:
            branch = Branch.objects.filter(pk=branch_id, company_id=company.pk).first()
        if branch is None:
            branch = Branch.objects.filter(company_id=company.pk).order_by('pk').first()
    return company, branch


def _kept_info(company_id=None, branch_id=None) -> dict:
    """Info data yang disisakan saat clear master data."""
    from core.models.settings.sequence import Sequence
    from core.models.settings.user import User

    company, branch = _pick_keep(company_id, branch_id)
    return {
        'company': {'id': company.pk, 'name': company.name} if company else None,
        'branch': {'id': branch.pk, 'name': branch.name} if branch else None,
        'users': User.objects.count(),
        # Definisi Sequence = konfigurasi penomoran, TIDAK dihapus (counter-nya yang direset)
        'sequences': Sequence.objects.count(),
    }


def _options() -> dict:
    """Pilihan Company & Branch yang bisa disisakan (untuk dropdown di UI)."""
    from core.models.settings.branch import Branch
    from core.models.settings.company import Company

    return {
        'companies': [
            {'id': c.pk, 'name': c.name} for c in Company.objects.order_by('pk')
        ],
        'branches': [
            {'id': row['id'], 'name': row['name'], 'company_id': row['company_id_id']}
            for row in Branch.objects.order_by('pk').values('id', 'name', 'company_id_id')
        ],
    }


def _backup(scope: str) -> dict:
    """Backup seluruh isi DB ke file JSON di backend/backups/ (best-effort)."""
    out_dir = Path(dj_settings.BASE_DIR) / 'backups'
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = out_dir / f'backup-{scope}-{stamp}.json'
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            call_command('dumpdata', '--indent', '1', '-o', str(path), stdout=fh, stderr=fh)
        size = path.stat().st_size
        return {'ok': True, 'path': str(path), 'size': size}
    except Exception as exc:  # pragma: no cover — backup tidak boleh menggagalkan proses
        return {'ok': False, 'path': str(path), 'error': str(exc)}


SCOPES = {
    'transactions': {
        'phrase': 'HAPUS TRANSAKSI',
        'title': 'Hapus Transaksi',
        'desc': 'Hapus SEMUA data transaksi: dokumen (PO, SO, faktur, tagihan, jurnal, dll) '
                'beserta barisnya, pergerakan stok, dan log chatter model transaksi '
                '(log master data tidak ikut terhapus).',
    },
    'master': {
        'phrase': 'HAPUS MASTER DATA',
        'title': 'Hapus Master Data',
        'desc': MASTER_SCOPE_DESC,
    },
}


@api_view(['GET'])
@permission_classes([IsAdmin])
def purge_preview(request):
    """Ringkasan data yang akan dihapus / direset (tidak mengubah apa pun)."""
    out = {}
    for scope, cfg in SCOPES.items():
        rows = _counts(_model_names_for(scope))
        resets = _reset_counts() if scope == 'transactions' else []
        out[scope] = {
            'title': cfg['title'],
            'desc': cfg['desc'],
            'phrase': cfg['phrase'],
            'rows': rows,
            'models': len(rows),
            'total': sum(r['count'] for r in rows),
            # counter nomor dokumen: direset (bukan dihapus sebagai master data)
            'resets': resets,
            # nomor ID otomatis (PK) tabel yang dikosongkan juga ikut di-RESTART ke 1
            'identity_reset': len(_pk_sequences(_scope_tables(scope))),
            # log chatter hanya untuk model pada scope ini (tidak digabung antar scope)
            'chatter': _chatter_queryset(scope).count(),
        }
    out['kept'] = _kept_info()
    out['options'] = _options()
    return Response(out)


@api_view(['POST'])
@permission_classes([IsAdmin])
def purge_run(request):
    """Jalankan penghapusan. Body: {scope: 'transactions'|'master', confirm: '<frasa>'}."""
    data = request.data or {}
    scope = data.get('scope')
    confirm = (data.get('confirm') or '').strip().upper()
    # Company & Branch yang disisakan (pilihan user di UI) — hanya untuk scope master.
    keep_company_id = data.get('keep_company') or None
    keep_branch_id = data.get('keep_branch') or None
    cfg = SCOPES.get(scope)
    if not cfg:
        return Response({'error': "scope harus 'transactions' atau 'master'."}, status=400)
    if confirm != cfg['phrase']:
        return Response({'error': f'Konfirmasi salah. Ketik "{cfg["phrase"]}".'}, status=400)

    names = _model_names_for(scope)
    backup = _backup(scope)
    before = {r['model']: r['count'] for r in _counts(names)}
    registry = _registry()
    deleted = {}

    with transaction.atomic():
        for name in names:
            cls = registry.get(name)
            if cls is None:
                continue
            count = cls.objects.count()
            if not count:
                continue
            rows = cls.objects.all().delete()[0]
            deleted[name] = rows

        # Log chatter dibersihkan HANYA untuk model pada scope ini — log model lain
        # (mis. master data saat clear transaksi) tetap dipertahankan.
        chatter_removed = _chatter_queryset(scope).delete()[0]
        if chatter_removed:
            deleted['chatter_log'] = chatter_removed

        # Counter nomor dokumen direset (baris counter dihapus → nomor mulai dari 1 lagi).
        resets = []
        if scope == 'transactions':
            for row in _reset_counts():
                cls = registry.get(row['model'])
                if cls is None:
                    continue
                removed = cls.objects.all().delete()[0]
                if removed:
                    resets.append({'model': row['model'], 'label': row['label'], 'count': removed})

        if scope == 'master':
            # Sisakan 1 Company & 1 Branch (pilihan user, fallback yang paling awal);
            # user TIDAK pernah dihapus (tabel auth).
            from core.models.settings.branch import Branch
            from core.models.settings.company import Company

            keep_company, keep_branch = _pick_keep(keep_company_id, keep_branch_id)
            if keep_company:
                extra_branches = Branch.objects.exclude(pk=keep_branch.pk if keep_branch else 0)
                removed = extra_branches.count()
                if removed:
                    extra_branches.delete()
                    deleted['settings.branch (sisa)'] = removed
                extra_companies = Company.objects.exclude(pk=keep_company.pk)
                removed = extra_companies.count()
                if removed:
                    extra_companies.delete()
                    deleted['settings.company (sisa)'] = removed

        # Nomor ID otomatis (PK) tabel yang sudah kosong di-RESTART ke 1. `DELETE` di PostgreSQL
        # tidak memundurkan sequence, jadi harus eksplisit — kalau tidak, record baru mulai dari
        # angka terakhir (mis. dokumen baru langsung "Draft#19" di daftar).
        identity_resets = _reset_pk_sequences(_scope_tables(scope))

    return Response({
        'scope': scope,
        'title': cfg['title'],
        'deleted': sorted(
            ({'model': k, 'label': _label(k), 'count': v} for k, v in deleted.items() if v),
            key=lambda r: (-r['count'], r['label']),
        ),
        'resets': resets,
        # nomor ID otomatis (PK) yang di-RESTART ke 1 → record baru mulai dari 1
        'identity_resets': identity_resets,
        'total': sum(deleted.values()),
        'backup': backup,
        'kept': _kept_info(keep_company_id, keep_branch_id),
        'before': before,
    })
