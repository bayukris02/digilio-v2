# Product Requirements Document (PRD)
## ERP System — Build from Scratch

**Versi:** 1.0
**Tanggal:** 21 Juni 2026
**Status:** Draft

---

## 1. Latar Belakang & Masalah

Pembangunan ERP sebelumnya dilakukan tanpa framework dan konvensi baku ("vibe coding"), menghasilkan:
- UI tidak konsisten antar form/modul
- Cara fetching data berbeda-beda di tiap modul backend
- Development modul baru lambat karena selalu dibangun dari nol
- Sulit maintenance & debugging karena tidak ada pola baku

**Tujuan proyek ini:** membangun ulang ERP dari nol dengan arsitektur yang **memaksa konsistensi** di seluruh modul, sehingga development modul baru menjadi cepat (template-based, bukan from-scratch), dan mudah dipelihara dalam jangka panjang.

---

## 2. Tujuan Produk

1. Membangun sistem ERP modular yang dapat menangani jutaan baris transaksi dan diakses puluhan user secara bersamaan.
2. Memastikan konsistensi struktur kode di seluruh modul (backend & frontend) melalui base class, convention, dan template yang baku.
3. Mendukung integrasi dengan aplikasi mobile dan pihak ketiga melalui Open API.
4. Mendukung fitur transaksional ERP standar: onchange field, auto-compute, multi-table editable (grid), dan dashboard (dapat realtime).
5. Menyediakan sistem access control (role & permission) yang granular dan aman.

---

## 3. Target Pengguna

- Internal staff perusahaan (berbagai role: Admin, Finance, Sales, Purchasing, Warehouse, Manager)
- Pengguna mobile app (field staff, approval on-the-go)
- Pihak ketiga/sistem eksternal yang terintegrasi via Open API

---

## 4. Lingkup (Scope)

### 4.1 In-Scope (Fase Awal)
- Modul inti: User, Role, Permission (RBAC)
- Modul master data (Supplier, Customer, Produk, dll — disesuaikan kebutuhan bisnis)
- Modul transaksi contoh sebagai template (Purchase Order, Sales Order)
- Sistem autentikasi & otorisasi (JWT)
- Dashboard ringkasan data
- Open API untuk integrasi mobile & pihak ketiga

### 4.2 Out-of-Scope (Fase Awal, dipertimbangkan ke depan)
- Modul reporting keuangan kompleks (neraca, laba-rugi) — fase lanjutan
- Multi-currency, multi-company — fase lanjutan
- AI assistant untuk read/write data — fase lanjutan setelah pondasi modul inti stabil

---

## 5. Functional Requirements

### 5.1 Konsistensi Arsitektur
| ID | Requirement |
|---|---|
| FR-01 | Setiap modul backend wajib extend dari base model/serializer/permission class yang baku |
| FR-02 | Setiap modul frontend wajib menggunakan base hook (fetch data), base form component, dan base service yang baku |
| FR-03 | Tersedia template/generator modul baru agar developer (atau AI saat vibe coding) memiliki starting point seragam |

### 5.2 Form & Interaksi (ERP-style)
| ID | Requirement |
|---|---|
| FR-04 | Form transaksi mendukung onchange — perubahan satu field otomatis memicu update/komputasi field lain |
| FR-05 | Form mendukung auto-compute (contoh: qty × price × (1-discount) = subtotal) secara real-time tanpa reload |
| FR-06 | Form mendukung multi-table editable (grid) mirip spreadsheet untuk input item transaksi (PO, SO, Invoice, dll) dengan performa baik meski data besar |

### 5.3 Dashboard
| ID | Requirement |
|---|---|
| FR-07 | Dashboard menampilkan ringkasan data bisnis (sales, stok, dll) dalam bentuk chart |
| FR-08 | Dashboard dapat menampilkan data secara realtime (push) untuk kasus kritikal (notifikasi, alert stok), dan polling untuk data non-kritikal |

### 5.4 Access Control
| ID | Requirement |
|---|---|
| FR-09 | Sistem mendukung Role-Based Access Control (RBAC): module-level (CRUD per modul) |
| FR-10 | Sistem mendukung field-level permission (sembunyikan kolom sensitif sesuai role) |
| FR-11 | Sistem mendukung row-level permission (data spesifik per user/role, misal sales hanya lihat order miliknya) |
| FR-12 | Validasi access control wajib dilakukan di backend (source of truth); frontend hanya untuk UX (sembunyikan menu/tombol) |

### 5.5 Integrasi
| ID | Requirement |
|---|---|
| FR-13 | Seluruh fungsi backend terekspos melalui REST API (Open API/Swagger docs) |
| FR-14 | API mendukung autentikasi token (JWT) untuk konsumsi dari web, mobile, dan pihak ketiga |

---

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Sistem mampu menangani jutaan baris data transaksi tanpa degradasi performa signifikan (dengan indexing & partitioning database yang tepat) |
| NFR-02 | Sistem mampu menangani puluhan user concurrent tanpa bottleneck |
| NFR-03 | Operasi multi-tabel (misal posting jurnal akuntansi) wajib menggunakan database transaction (rollback otomatis jika gagal) |
| NFR-04 | Semua data transaksi memiliki audit trail (created_by, created_at, updated_at) dan mendukung soft-delete |
| NFR-05 | Response time API untuk operasi CRUD standar < 500ms pada kondisi normal |
| NFR-06 | Sistem harus dapat diakses dari web (desktop/tablet) dan mobile app |

---

## 7. Tech Stack

| Layer | Teknologi | Catatan |
|---|---|---|
| Backend | Python + Django + Django REST Framework (DRF) | Struktur baku (model/view/url), ORM built-in, admin panel gratis |
| Database | PostgreSQL | ACID, partitioning native untuk tabel transaksi besar |
| Auth | JWT (`djangorestframework-simplejwt`) | API-only, mendukung web + mobile + 3rd party |
| Realtime | Django Channels + Redis (Pub/Sub) | Untuk notifikasi/alert yang butuh push, bukan polling |
| Background Job | Celery + Redis | Proses berat: export, report, email |
| Frontend Web | React + TypeScript | Ekosistem luas, AI-assist kuat |
| State Management | Zustand | Konsisten di semua modul |
| Data Fetching | TanStack Query | Caching otomatis, satu pattern fetch |
| UI Component | Ant Design | Komponen siap pakai untuk admin/ERP-style |
| Grid Editable | AG Grid (React) | Multi-row editable, performa tinggi |
| Form Validation | React Hook Form + Zod | Validasi konsisten, type-safe |
| Chart/Dashboard | ECharts (`echarts-for-react`) | Visualisasi data, update sering |
| Mobile | React Native | Reuse logic dengan web (JS/TS) |
| Server/Infra | Nginx + Gunicorn/Uvicorn | Reverse proxy + WSGI/ASGI server |
| Caching | Redis | Session, cache, backbone Celery & Channels |
| Access Control | RBAC custom (Role + Permission model) | Backend sebagai source of truth |

---

## 8. Prinsip Arsitektur (Wajib Dipatuhi)

1. **Base class di backend**: `BaseModel` (abstract model dengan audit field), base permission class, base serializer.
2. **Base pattern di frontend**: base hook (TanStack Query), base form component, base service untuk API call.
3. **Template/generator modul baru**: modul baru harus mereferensikan modul existing sebagai pattern (terutama saat vibe coding dengan AI).
4. **Database design**: soft delete, audit trail, partitioning tabel transaksi besar sejak awal.
5. **Security**: backend tidak pernah mempercayai data/validasi dari frontend.

---

## 9. Milestone / Roadmap (Usulan Awal)

| Fase | Deliverable |
|---|---|
| Fase 1 | Setup project skeleton (backend + frontend), modul User/Role/Permission |
| Fase 2 | Modul master data inti (Supplier, Customer, Produk, dll) |
| Fase 3 | Modul transaksi pertama sebagai template (Purchase Order) — lengkap dengan onchange, auto-compute, grid item |
| Fase 4 | Replikasi pola dari Fase 3 ke modul transaksi lain (Sales Order, Invoice, dll) |
| Fase 5 | Dashboard & reporting dasar |
| Fase 6 | Mobile app (React Native) terintegrasi dengan Open API |
| Fase 7 | Fitur AI assist untuk read/write data (opsional, lanjutan) |

---

## 10. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Inkonsistensi kode kembali terjadi saat vibe coding | Wajib referensikan modul existing ke AI setiap membuat modul baru; gunakan base class & template |
| Performa menurun saat data transaksi membesar | Partitioning tabel, indexing tepat, pagination wajib di semua list endpoint |
| Kompleksitas realtime (WebSocket) berlebihan dari awal | Evaluasi kebutuhan riil — gunakan polling untuk kasus non-kritikal, WebSocket hanya untuk notifikasi kritikal |
| Solo developer — beban development tinggi | Prioritaskan modul inti & template dulu sebelum ekspansi modul lain |

---

## 11. Catatan Tambahan

Dokumen ini adalah hasil rangkuman diskusi perencanaan teknis. Detail requirement bisnis per modul (field spesifik, business rule, approval flow) perlu didefinisikan lebih lanjut per modul saat masuk fase development masing-masing.