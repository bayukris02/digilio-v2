# Standar UI Report (metadriven)

Berlaku untuk **semua halaman report** di `frontend/src/pages/base/*ReportPage*` dan
`StockBalancePage` / `StockCardPage`: grid gudang stok, laba rugi, neraca, buku besar,
arus kas, perubahan modal, report pajak, dst.

Tujuan: layout, CSS, dan perilaku loading/refresh **hanya ada di satu tempat**.
Halaman report hanya mendefinisikan **metadata** (judul, filter, kolom, query, export).
Perbedaan antar report = **hanya** daftar filter, daftar kolom, dan sumber data.

## 1. Struktur wajib (2 card)

```
div padding:16
└── div maxWidth:1100, margin:0 auto
    ├── Header (satu baris, semua sejajar tengah)
    │     kiri : Title level={4}
    │     kanan: [filter place:'header' — label bold inline + kontrol]  [Export Excel]  [Refresh]
    │            + "Data per: 11-Sep-2026 14:05" (italic, absolute di bawah tombol Refresh)
    │     (subtitle/notice opsional — taruh di bawah judul kalau perlu; report standar = tanpa subtitle)
    ├── Card 1 — FILTER (Card size="small", marginBottom:12)
    │     Row gutter={[12,10]} → 4 kolom (span 6 per kolom)
    │     setiap item: label 12px **bold** (+ chip preset) di atas, kontrol size="small" width 100% di bawah
    └── Card 2 — TABEL (Card size="small", body padding 8)
          Table size="small" pagination={false} + summary opsional + locale.emptyText
          Tampilan rapat via ConfigProvider scoped (token Table):
          cellPaddingBlockSM: 4 · cellPaddingInlineSM: 8 · headerBg '#e8eef6' ·
          headerColor '#1f1f1f' · headerSplitColor '#cfd8e3' · borderColor '#e3e8ee'
```

Filter yang menempel di header (mis. **Periode**) memakai `place: 'header'` + `width` (px, default 200);
label-nya dirender bold inline di sebelah kontrol. Filter `place:'card'` masuk grid 4 kolom di Card filter.
Tinggi sel filter header dijaga setinggi kontrolnya: teks info tanggal (italic) dan picker Kustom
diposisikan **absolute** di bawah kontrol (`top:100%`), jadi posisi field tidak pernah bergeser dan
selalu sejajar dengan tombol Export/Refresh (header diberi `marginBottom` ekstra 30px untuk ruangnya).

Saat `loading`: Card 2 diganti `div textAlign:center padding:48 color:#8c8c8c` → `Loading report…`
(Card filter tetap tampil).

## 2. Shell: `src/components/report/ReportPage.tsx`

```tsx
<ReportPage<RowType>
  title="Stock Card"
  fetchedAt={query.dataUpdatedAt}          // WAJIB: waktu data diambil (epoch ms)
  filters={filters}                        // metadata filter, §3
  loading={loading}
  refreshing={refreshing}
  onRefresh={onRefresh}
  columns={columns}                        // metadata kolom, §2a
  dataSource={rows}
  rowKey="id"                              // atau (row, index) => string
  summaryCells={summaryCells}              // §2b
  emptyText="Tidak ada data untuk filter ini"
  exportConfig={exportConfig}              // §2c — tombol Export muncul otomatis
/>
```

### 2a. Kolom — `ReportColumn<T>[]` (jangan tulis objek kolom antd)
`{ key, title, dataIndex?, width?, align?, render?(row), export? }` — shell mengonversi ke kolom antd
(`render` menerima **row**, bukan value) dan memakai `title` + `export`/`dataIndex` untuk file Excel.

### 2b. Baris Total — `summaryCells: ReportSummaryCell[]`
`[{ colSpan?, value?, align? }]` — shell merender `Table.Summary.Row`; tidak ada JSX Summary di halaman.

### 2c. Export Excel — `exportConfig`
`{ filename: () => string, sheetName?, meta?: (string|number)[][] }` — header kolom & isi file
**diturunkan otomatis** dari `columns` (kolom `export: false` dilewati; `export.value(row)` untuk nilai
khusus); lebar kolom dihitung dari `width` kolom. Halaman tidak lagi menyusun baris Excel manual.

**Dilarang** menulis ulang `padding`/`maxWidth`/header/Card/penanda loading di halaman report.

## 3. Metadata filter — `src/components/report/types.ts`

Grid selalu **4 kolom**; `cols` = lebar item (`1` = 1 kolom → span 6, `2` = 2 kolom → span 12).

| type        | kontrol        | catatan |
|-------------|----------------|---------|
| `select`    | Select         | `multiple`, `showSearch` (client) atau `serverSearch`+`onSearch` (cari ke server) |
| `period`    | Select periode | **standar filter tanggal**: opsi periode dari `options` + opsi "Kustom…". `mode:'range'` (default) = rentang; `mode:'date'` = satu tanggal snapshot (custom pakai DatePicker, info teks `Per 11-Sep-2026`) — dipakai Stock Balance. Lihat detail di bawah |
| `date`      | DatePicker     | `presets` chip opsional, `disabled`, `disabledDate` |
| `daterange` | RangePicker    | `presets` chip opsional, **wajib `cols: 2`** |
| `boolean`   | Switch         | `value` boolean |
| `text`      | Input          | untuk filter teks bebas |

Label filter selalu **bold** (`Text strong`) — jangan pakai `type="secondary"`.

Contoh (Stock Card: dropdown + dropdown + dropdown periode = 1+1+2 kolom):

```tsx
const filters: ReportFilter[] = [
  { key: 'product',   label: 'Produk',  type: 'select', value: productId, options: productOptions,
    showSearch: true, serverSearch: true, onSearch: setProductSearch, onChange: (v, o) => { /* … */ } },
  { key: 'warehouse', label: 'Gudang',  type: 'select', value: warehouseIds, options: warehouseOptions,
    multiple: true, showSearch: true, onChange: (v) => setWarehouseIds((v as number[]) ?? []) },
  { key: 'period',    label: 'Periode', type: 'period', place: 'header', width: 240,
    value: period, range: customRange, resolvedRange: range, options: PERIOD_OPTIONS, disabledDate: notFuture,
    onChange: ({ key, range }) => { setPeriod(key); if (key === 'custom') setCustomRange(range); } },
];
```

Pola periode: `value` = key opsi (`today` / `last_7_days` / `this_month` / `last_month` / `this_year` / `all` / `custom`);
range efektif diturunkan `useMemo` dari key (`periodRange(key)`), `customRange` hanya dipakai saat key `custom`.
Di bawah dropdown **selalu** tampil teks efektif (italic, absolute → tidak menggeser kontrol): rentang `x s/d y`
atau `Per <tanggal>` untuk `mode:'date'`. Saat Kustom picker muncul lalu berganti teks (klik teks untuk ubah).
Semua DatePicker/RangePicker di shell memakai `format={DATE_FORMAT}` (dd-mmm-yyyy, mis. `11-Sep-2026`) dari `utils/format.ts`.

## 3a. Report yang sudah memakai standar

Stock Card (`pages/base/StockCardPage.tsx`) · Stock Balance (`pages/base/StockBalancePage.tsx`) ·
Stock Ledger (`pages/base/StockLedgerPage.tsx`, data dari `GET /api/stock/ledger/`).
Sisa: seluruh Laporan Keuangan (`FinancialReportPage`), Report Pajak, dan report lain di menu REPORT.

## 4. Helper format — `src/utils/reportFormat.ts`

`fmtQty` · `fmtIDR` · `fmtNum` · `fmtReportDate` · `fmtDateTime` (mengikuti `DATE_FORMAT` global di `utils/format.ts`).
Jangan bikin `fmt…` baru di halaman report. File Excel sepenuhnya disusun shell (`exportXlsx` internal):
judul report → `exportConfig.meta` → baris kosong → header kolom → data.

## 5. Cara migrasi report lain (mis. Stock Balance, Laba Rugi, Neraca, Report Pajak)

1. Hapus blok header + Card filter + Card tabel di halaman (termasuk `padding`/`maxWidth` lokal).
2. Petakan filter lama → metadata `filters[]` (date range → `cols: 2`; preset chips → `presets`).
3. Pindahkan `columns` apa adanya (render tetap di halaman — kolom memang konteks report).
4. Ganti helper format lokal ke `utils/reportFormat.ts`.
5. Bungkus dengan `<ReportPage>`; `maxWidth` default 1100 (jangan override kecuali diminta).
6. Verifikasi: `npx tsc -b 2>&1 | grep <file yang diubah>` (0 error) + modul ter-transform di Vite
   (`curl -o /dev/null -w '%{http_code}' http://127.0.0.1:3002/src/pages/base/<Page>.tsx` → 200).

Referensi implementasi: **`frontend/src/pages/base/StockCardPage.tsx`** (report pertama yang memakai standar ini).
