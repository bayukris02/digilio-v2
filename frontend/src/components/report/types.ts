import type { ReactNode } from 'react';
import type { Dayjs } from 'dayjs';

/**
 * STANDAR REPORT — metadata (lihat docs/report-ui-standard.md)
 * Semua report memakai shell <ReportPage /> + daftar filter di sini.
 * Grid filter selalu 4 kolom; `cols` menentukan lebar (1 = 1 kolom, 2 = 2 kolom
 * — dipakai date range).
 */
export type ReportFilterOption = { value: string | number; label: string };

/**
 * Metadata kolom tabel. Halaman report TIDAK menulis objek kolom antd —
 * cukup deklarasi ini; shell mengonversi ke kolom antd + menyusun export Excel.
 */
export type ReportColumn<T> = {
  key: string;
  title: string;
  /** Field sumber nilai (dipakai juga untuk export bila `export` tidak diisi). */
  dataIndex?: string;
  width?: number;
  align?: 'left' | 'right' | 'center';
  /** Render sel; terima row (bukan value) — kolom report selalu konteks baris. */
  render?: (row: T) => ReactNode;
  /**
   * Nilai saat export Excel. Default: `dataIndex` apa adanya.
   * Isi `false` untuk mengeluarkan kolom ini dari file export.
   */
  export?: false | { value: (row: T) => string | number | null | undefined };
};

/** Satu sel baris Total ringkasan tabel. */
export type ReportSummaryCell = {
  /** Jumlah kolom yang dicakup (default 1). */
  colSpan?: number;
  value?: ReactNode;
  align?: 'left' | 'right' | 'center';
};

/** Konfigurasi export Excel — header & isi diturunkan otomatis dari `columns`. */
export type ReportExportConfig = {
  /** Nama file .xlsx — dihitung saat tombol diklik (boleh bergantung state filter). */
  filename: () => string;
  sheetName?: string;
  /** Blok konteks filter di atas header kolom (mis. [['Produk','Semua Produk']]). */
  meta?: (string | number)[][];
};

/** Chip preset tanggal (mis. "Bulan Ini") — value dibaca ulang saat diklik supaya tanggal relatif tetap segar. */
export type ReportPreset = {
  key: string;
  label: string;
  value: () => Dayjs | [Dayjs | null, Dayjs | null] | null;
};

type ReportFilterBase = {
  key: string;
  label: string;
  /** Lebar dalam grid 4 kolom: 1 = 1 kolom (span 6), 2 = 2 kolom (span 12). Default 1. */
  cols?: 1 | 2;
  /**
   * Penempatan filter: 'card' (default) = di dalam Card filter,
   * 'header' = sejajar dengan tombol Export/Refresh di baris judul.
   */
  place?: 'card' | 'header';
  /** Lebar kontrol saat place='header' (px). Default 200. */
  width?: number;
};

export type ReportSelectValue = string | number | (string | number)[] | null | undefined;

export type ReportSelectFilter = ReportFilterBase & {
  type: 'select';
  value: ReportSelectValue;
  options: ReportFilterOption[];
  multiple?: boolean;
  allowClear?: boolean;
  placeholder?: string;
  loading?: boolean;
  /** Aktifkan pencarian client-side (optionFilterProp="label"). */
  showSearch?: boolean;
  /** Pencarian dilakukan ke server: filterOption off + pakai onSearch. */
  serverSearch?: boolean;
  onSearch?: (q: string) => void;
  notFoundContent?: ReactNode;
  onChange: (v: ReportSelectValue, option?: unknown) => void;
};

export type ReportDateFilter = ReportFilterBase & {
  type: 'date';
  value: Dayjs | null;
  onChange: (v: Dayjs | null) => void;
  allowClear?: boolean;
  disabled?: boolean;
  disabledDate?: (d: Dayjs) => boolean;
  presets?: ReportPreset[];
  /** Key preset yang sedang aktif (untuk highlight chip). */
  activePreset?: string;
  onPresetClick?: (p: ReportPreset) => void;
};

export type ReportDateRangeFilter = ReportFilterBase & {
  type: 'daterange';
  value: [Dayjs | null, Dayjs | null] | null;
  onChange: (v: [Dayjs | null, Dayjs | null] | null) => void;
  allowClear?: boolean;
  disabledDate?: (d: Dayjs) => boolean;
  presets?: ReportPreset[];
  activePreset?: string;
  onPresetClick?: (p: ReportPreset) => void;
};

export type ReportBooleanFilter = ReportFilterBase & {
  type: 'boolean';
  value: boolean;
  onChange: (v: boolean) => void;
};

/**
 * Dropdown periode (standar untuk filter rentang tanggal).
 * Nilai = key preset dari `options`, atau `'custom'` → muncul RangePicker
 * di bawah dropdown (kolom yang sama, wajib `cols: 2`).
 */
export type ReportPeriodFilter = ReportFilterBase & {
  type: 'period';
  /**
   * 'range' (default) = periode rentang tanggal (custom pakai RangePicker),
   * 'date' = satu tanggal (snapshot, custom pakai DatePicker) — mis. Stock Balance.
   */
  mode?: 'range' | 'date';
  value: string;
  /** Range manual — dipakai saat value === 'custom'. */
  range: [Dayjs | null, Dayjs | null] | null;
  /**
   * Range efektif dari key periode yang sedang aktif (untuk semua opsi, termasuk
   * preset seperti "Bulan Ini") — ditampilkan sebagai teks info di bawah dropdown
   * supaya user tahu sistem memfilter dari tanggal berapa sampai berapa.
   */
  resolvedRange?: [Dayjs | null, Dayjs | null] | null;
  options: { key: string; label: string }[];
  customLabel?: string;
  disabledDate?: (d: Dayjs) => boolean;
  onChange: (v: { key: string; range: [Dayjs | null, Dayjs | null] | null }) => void;
};

export type ReportTextFilter = ReportFilterBase & {
  type: 'text';
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  allowClear?: boolean;
};

export type ReportFilter =
  | ReportSelectFilter
  | ReportDateFilter
  | ReportDateRangeFilter
  | ReportBooleanFilter
  | ReportPeriodFilter
  | ReportTextFilter;
