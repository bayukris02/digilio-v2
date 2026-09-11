# Pemeliharaan Data — Clear Database

Fitur untuk membersihkan isi database dari dalam aplikasi (menu **Pengaturan → Pemeliharaan Data**).
Hanya bisa dipakai **admin/staff** (`IsAdmin`) dan **tidak pernah menghapus user** (tabel `auth_user`).

- UI: `frontend/src/pages/base/DataMaintenancePage.tsx` (`/settings/data_maintenance`)
- API: `frontend/src/api/maintenance.ts` → `backend/core/purge_api.py`
- Endpoint: `GET /api/maintenance/purge/preview/` (baca saja) · `POST /api/maintenance/purge/` (eksekusi)

## Dua aksi

### 1. Hapus Transaksi — `scope: "transactions"`
Menghapus **42 model** dokumen & pergerakan (PO/SO/GR/DO/faktur/tagihan/jurnal/stok/dll) + seluruh baris
dokumen + **seluruh log chatter**, lalu **mereset counter nomor dokumen**:

- `settings.sequence_date_range` (counter) dikosongkan → penomoran dokumen **mulai dari 1** lagi.
- **Definisi `settings.sequence` (prefix/padding/reset_period) TIDAK dihapus** — hanya counter-nya.
- Karena itu counter tampil sebagai baris **“Reset”** di UI, bukan sebagai data yang dihapus.

### 2. Hapus Master Data — `scope: "master"`
Menghapus **26 model** master data: customer, vendor, produk & kategori, UOM, gudang & lokasi, COA, pajak,
payment method, pricelist (+baris), order template (+baris), vendor pricelist, project/unit/block/milestone/
dokumen, **role & RBAC** (`settings.role`, `role_menu_access`, `user_role`).

Disisakan:
- **1 Company** dan **1 Branch** (yang paling awal / `pk` terkecil); sisa company/branch dihapus.
- **Seluruh user** (tabel auth tidak disentuh) — tanpa role, user non-staff hanya bisa membuka Dashboard.
- **`settings.sequence`** (konfigurasi penomoran).
- **Semua log chatter** dihapus pada kedua scope.

## Aturan teknis

- **Hard delete** — termasuk baris yang sudah soft-deleted (`is_deleted=True`).
- **Backup otomatis**: seluruh isi DB di-dump (`dumpdata`) ke `backend/backups/backup-<scope>-<stamp>.json`
  sebelum penghapusan (best-effort; kalau gagal, path & error tetap dilaporkan di UI).
- **Atomic**: semua penghapusan dijalankan dalam satu transaksi database.
- **Konfirmasi wajib**: user harus mengetik frasa (`HAPUS TRANSAKSI` / `HAPUS MASTER DATA`) — salah → HTTP 400,
  tidak ada perubahan.
- **Urutan disarankan**: Hapus Transaksi dulu, baru Hapus Master Data (agar dokumen tidak kehilangan relasi).
- Klasifikasi model **meta-driven dari registry** (`ErpModelBase._model_registry`):
  `TRANSACTION_MODELS` / `KEEP_MASTER_MODELS` / `RESET_COUNTER_MODELS` di `core/purge_api.py`.
  Model baru otomatis terklasifikasi sebagai master kecuali ditambahkan ke daftar lain — pastikan daftar
  diperbarui bila menambah model baru.
- `backend/backups/` masuk `.gitignore`.

## Uji aman (tanpa menyentuh data asli)

1. `CREATE DATABASE digilio_purgetest TEMPLATE digilio`
2. Arahkan `settings.DATABASES['default']['NAME']` ke DB sandbox, jalankan `purge_preview` + `purge_run`
   langsung (bypass permission, `RequestFactory`).
3. Verifikasi: konfirmasi salah → 400 & tidak berubah; setelah hapus transaksi → 0 sisa & counter 0;
   setelah hapus master → company 1 / branch 1 / user utuh / Sequence utuh.
4. `DROP DATABASE digilio_purgetest WITH (FORCE)`.

Hasil uji terakhir: 9.673 baris (transaksi, termasuk 8.246 chatter) · 197 baris (master) — 0 sisa, tanpa error.
