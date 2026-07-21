# Import Feature Implementation Plan

**Goal:** Generic import CSV/Excel untuk semua model ERP — upload, preview (5 rows + error detection), pilih sheet (multisheet), execute dengan partial import, error report.

**Architecture:** Backend `imports/` app dengan parser → validator → importer pipeline. Frontend `ImportModal` component untuk upload → sheet select → preview → execute. Threshold 100 rows: synchronous ≤ 100, background > 100.

**Tech Stack:** openpyxl (Excel), csv (stdlib), Django REST Framework, React + Ant Design Modal/Upload/Table/Progress.

---

## Tasks

### Task 1: Setup imports app + dependencies

**Files:**
- Create: `backend/imports/__init__.py`
- Create: `backend/imports/apps.py`
- Create: `backend/imports/parser.py`
- Create: `backend/imports/validator.py`
- Create: `backend/imports/importer.py`
- Create: `backend/imports/views.py`
- Create: `backend/imports/urls.py`
- Modify: `backend/config/settings.py` — register app
- Modify: `backend/config/urls.py` — register routes

**Steps:**
1. Create app directory structure
2. Install openpyxl: `uv add openpyxl`
3. Write apps.py
4. Register in settings.py
5. Add URLs

### Task 2: Write parser.py

**Files:**
- Create: `backend/imports/parser.py`

Parsing logic:
- Detect file type (CSV vs XLSX) by extension
- Parse CSV: detect delimiter (comma/semicolon/tab), read header + rows
- Parse XLSX: read all sheet names, read selected sheet, read header + rows
- Return: `{'headers': [...], 'rows': [[...]], 'sheets': ['Sheet1', ...]}`

### Task 3: Write validator.py

**Files:**
- Create: `backend/imports/validator.py`

Validation logic:
- Skip: compute, virtual, one2many, base fields (auto-detect)
- Map column headers to field names (by label → fname)
- Validate each cell by field type:
  - Many2One: lookup by name → code → id
  - Date: parse YYYY-MM-DD
  - Monetary/Float: parse number
  - Selection: match option value
  - Boolean: yes/no/true/false/1/0
- Return: `{'valid_rows': [...], 'error_rows': [...], 'field_mapping': {...}}`

### Task 4: Write importer.py + views.py + urls.py

**Files:**
- Create: `backend/imports/importer.py`
- Create: `backend/imports/views.py`
- Create: `backend/imports/urls.py`

Endpoints:
- `POST /api/import/{model_name}/preview/` — upload file → parse sheet → preview 5 rows + validation
- `POST /api/import/{model_name}/template/` — download CSV template
- `POST /api/import/{model_name}/execute/` — execute import (sync, partial)
- `POST /api/import/{model_name}/execute/background/` — execute import (Celery, future)

### Task 5: Write frontend ImportModal component

**Files:**
- Create: `frontend/src/components/ImportModal.tsx`
- Modify: `frontend/src/pages/model/ModelListPage.tsx` — add Import button + modal

Component flow:
1. Upload file (CSV/XLSX) — Ant Design Upload
2. If multi-sheet → dropdown pilih sheet
3. Preview table — Ant Design Table (5 rows + field mapping)
4. Error report validation
5. Execute button → progress spinner → result notification

---

## Threshold Logic

| Rows | Mode | UX |
|---|---|---|
| 1–100 | Sync | Loading spinner + progress |
| >100 | Background | Notifikasi setelah selesai |
| >100 & no Celery | Block | "Max 100 rows — pisahkan file" |

## Field Auto-Skip Rules

| Tipe | Skip? | Deteksi |
|---|---|---|
| compute | ✅ | `fd.compute` |
| virtual | ✅ | `fd.virtual` |
| one2many | ✅ | `fd.field_type == 'one2many'` |
| Base fields (id, created_at, etc.) | ✅ | Not in `_field_descriptors` |

## Many2One Lookup Priority

1. By `name` field
2. By `code` field (if exists)
3. By `id` (if numeric value)
