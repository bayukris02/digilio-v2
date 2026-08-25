# Quick Purchase (purchase.quick_purchase) Implementation Plan

> **For Hermes:** Execute with `subagent-driven-development` — dispatch fresh subagent per task.

**Goal:** Modul versi cepat PO — 1 dokumen menyelesaikan seluruh flow PO → Goods Receipt → Bill → Payment sekaligus saat dikonfirmasi.

**Architecture:** Model baru `purchase.quick_purchase` + line, mengikuti pola `purchase.order`. Action `confirm` (draft → done) dalam 1 transaction membuat GR (done), Bill (confirmed), Payment (done) + alokasi penuh, lalu generate reference dari sequence sendiri. Dokumen anak tetap model existing — ditambah field relasi balik `quick_purchase` (optional) agar smart button & filtering bekerja.

**Tech Stack:** Django/DRF (model_meta metadata-driven) + React/Vite (route generic). Frontend menu SUDAH ada (`purchase.quick_purchase` → ComingSoon).

---

## Keputusan Desain (simple)

1. **State:** `draft` (edit/delete) → `done` via action `confirm`; `cancel` dari draft saja.
2. **1 tombol "Konfirmasi & Selesai"** = transition `confirm` + `_effect_confirm` yang dalam `transaction.atomic()`:
   - Buat **GoodsReceipt** status `done` + receipt lines (qty penuh), reference dari sequence GR.
   - Buat **VendorBill** status `confirmed` + bill lines (qty penuh, harga & pajak dari line), reference dari sequence bill, `bill_method='on_order'`.
   - Buat **VendorPayment** status `done` + 1 payment line (alloc = grand_total bill), `payment_method` dari header quick purchase, reference dari sequence payment.
   - Update `bill.paid_amount = grand_total` + `bill._run_compute()` → `payment_status='paid'`.
   - Set status dokumen = `done`, generate reference quick purchase dari sequence sendiri.
3. **Qty penuh** — tanpa partial receive/bill (beda dengan PO multi-tahap).
4. **Tidak ada efek stok** — konsisten dgn GR existing (belum ada modul stock).
5. **Sequence:** user membuat sequence `model_ref='purchase.quick_purchase'` via UI settings.sequence (tidak perlu seed command).

## Asumsi / Open Questions

- GR `purchase_order` diubah `required=False` + field baru `quick_purchase` (GR sekarang wajib PO). Perubahan model existing — 3 file model, bukan core.
- Payment method dipilih di header quick purchase (wajib, karena VendorPayment.payment_method required).
- Discount global (discount_type/method/global_discount) — ikut pola PO supaya konsisten.

---

## Tasks

### Task 1: Field relasi balik di model existing

**Files:**
- Modify: `backend/core/models/purchase/goods_receipt.py` — `purchase_order` → `required=False`; tambah `quick_purchase: Many2OneField(relation='purchase.quick_purchase', required=False)`
- Modify: `backend/core/models/accounting/vendor_bill.py` — tambah `quick_purchase` field (required=False)
- Modify: `backend/core/models/accounting/vendor_payment.py` — tambah `quick_purchase` field (required=False)

**Verifikasi:** `manage.py check` OK.

### Task 2: Model QuickPurchaseLine

**Files:**
- Create: `backend/core/models/purchase/quick_purchase_line.py`

Field (copy pola `purchase_order_line`): `quick_purchase_id` (Many2One inverse), `product`, `name`, `qty`, `uom`, `price`, `discount_percentage`, `discount_amount`, `tax_percentage`, `tax_amount`, `total` (compute: qty*price − disc + tax), `notes`. `_model_name = 'purchase.quick_purchase.line'`.

### Task 3: Model QuickPurchase (header + action)

**Files:**
- Create: `backend/core/models/purchase/quick_purchase.py`

- `_model_name = 'purchase.quick_purchase'`, `_display_name = 'reference'`
- `_states`: draft (edit/delete) / done / cancelled
- `_transitions`: `confirm` (draft→done, guard `_guard_confirm`, effect `_effect_confirm`), `cancel` (draft→cancelled)
- Fields: `sequence_id` (settings.sequence), `reference`, `vendor` (+autofill address/code), `address`, `code`, `order_date`, `payment_method` (accounting.payment_method, required), `payment_date`, `notes`, `discount_type`, `discount_method`, `global_discount`, `subtotal/discount/tax/grand_total` (compute `_compute_summary` — copy formula PO), `quick_purchase_lines` (One2Many)
- `_guard_confirm`: wajib sequence_id + min 1 line
- `_effect_confirm`: `transaction.atomic()` → generate reference (SequenceEngine model_ref `purchase.quick_purchase`) → buat GR done + lines, Bill confirmed + lines, Payment done + line alloc, update bill.paid_amount + `_run_compute()`, set status done
- `_document_flow`: 3 children (goods_receipt, vendor_bill, vendor_payment) `source_field_in_child='quick_purchase'`, `allowed_parent_states: ['done']`, mapping `vendor: vendor`
- `_form_view`: tab umum (reference/vendor/order_date/payment_method/sequence_id), notebook lines (produk/qty/price/discount/tax/total + summary grand_total), actions: Cetak / Konfirmasi (draft) / Batal (draft), smart_buttons GR/Bill/Payment
- `_list_view`: reference, vendor, order_date, status, grand_total

### Task 4: Registrasi + migration

**Files:**
- Modify: `backend/core/models/__init__.py` — import 2 model baru + `__all__`
- Generate: `manage.py makemigrations` (nama migration berisi quickpurchase + alter GR/bill/payment) → `manage.py migrate`

**Verifikasi:** `manage.py check` OK, `python -c "from core.models.purchase.quick_purchase import QuickPurchase"` OK.

### Task 5: Route frontend

**Files:**
- Modify: `frontend/src/routes/index.tsx` — ganti `purchase.quick_purchase` ComingSoon → `ModelListPage`/`ModelFormPage` modelName `purchase.quick_purchase` basePath `/purchase.quick_purchase` (pola sama dgn `purchase.order`)

**Verifikasi:** `npx tsc --noEmit` (atau build) OK.

### Task 6: Uji end-to-end (shell, tanpa browser)

1. Buat sequence `purchase.quick_purchase` via ORM.
2. Buat QuickPurchase draft + 1 line via ORM → POST action `confirm` ke `/api/models/purchase.quick_purchase/<id>/action/` (atau panggil `_effect_confirm` langsung).
3. Cek: status done, reference terisi; GR done + lines; Bill confirmed + `payment_status='paid'`; Payment done + alloc.
4. `curl /api/models/purchase.quick_purchase/config/` → 200.
5. Restart backend `digilio-v2-backend` (systemd, `--noreload` → wajib restart).

---

## Expected Results

| Step | Hasil |
|------|-------|
| 1 | GR/bill/payment bisa di-relasi ke quick purchase (tanpa PO wajib) |
| 2-3 | Model `purchase.quick_purchase(.line)` — form PO-like, konfirmasi sekali jadi semua |
| 4 | Model terdaftar + migration ter-apply |
| 5 | Menu Quick Purchase di sidebar → list/form nyata (bukan ComingSoon) |
| 6 | 1 dokumen → GR + Bill + Payment otomatis, bill paid, semua reference terisi |

## Risiko / Tradeoff

- Perubahan 3 model existing (GR required=False + field baru) — diperlukan karena dokumen anak mensyaratkan relasi. Aman: field optional, tidak mengubah behavior flow PO lama.
- Bila user ingin partial receive/bill → perlu wizard line_selection seperti PO (bukan simple).
- Payment dibuat langsung `done` — tidak ada tahap review payment.
