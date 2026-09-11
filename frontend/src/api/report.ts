import api from './client';

export interface ReportRow {
  code: string;
  name: string;
  amount: number;
  debit?: number;
  credit?: number;
}

export interface ReportSection {
  key: string;
  title: string;
  rows: ReportRow[];
  subtotal: number;
  debit_subtotal?: number;
  credit_subtotal?: number;
}

export interface ReportTotal {
  key: string;
  label: string;
  amount: number;
}

export interface ReportData {
  key: string;
  title: string;
  period: { date_from: string; date_to: string };
  sections: ReportSection[];
  totals: ReportTotal[];
  show_sides?: boolean;
  show_balance_col?: boolean;
}

export const reportApi = {
  get: (key: string, params?: { date_from?: string; date_to?: string }) =>
    api.get<ReportData>(`/reports/${key}/`, { params }).then((r) => r.data),
};

// ── Stock reports (agregasi StockEngine dari stock ledger) ──

export interface StockBalanceRow {
  product_id: number;
  code: string;
  name: string;
  uom: string;
  qty: number;
}

export interface StockBalanceData {
  key: string;
  title: string;
  date: string;
  rows: StockBalanceRow[];
  totals: { qty: number };
}

export const stockBalanceApi = {
  get: (params?: { date?: string; warehouses?: string; product?: number }) =>
    api.get<StockBalanceData>('/stock/balance/', { params }).then((r) => r.data),
};

export interface StockCardRow {
  kind: 'opening' | 'movement' | 'closing';
  product_id: number;
  code: string;
  name: string;
  uom: string;
  location_id: number;
  location_name: string;
  date: string;
  source_label: string;
  reference: string;
  description: string;
  qty_in: number | null;
  qty_out: number | null;
  balance: number | null;
}

export interface StockCardData {
  key: string;
  title: string;
  filters: { product_id: number | null; warehouse_ids: number[]; date_from: string; date_to: string };
  rows: StockCardRow[];
}

export const stockCardApi = {
  get: (params?: { product?: number; warehouses?: string; date_from?: string; date_to?: string }) =>
    api.get<StockCardData>('/stock/card/', { params }).then((r) => r.data),
};

// ── Stock ledger (daftar mentah pergerakan stok) ──

export interface StockLedgerRow {
  id: number;
  date: string;
  product_id: number;
  code: string;
  name: string;
  uom: string;
  location_id: number;
  location_name: string;
  quantity: number;
  qty_in: number | null;
  qty_out: number | null;
  unit_cost: number;
  source_model: string;
  source_label: string;
  reference: string;
  description: string;
}

export interface StockLedgerData {
  key: string;
  title: string;
  filters: {
    product_id: number | null;
    warehouse_ids: number[];
    date_from: string;
    date_to: string;
    source_models: string[];
  };
  sources: { value: string; label: string }[];
  rows: StockLedgerRow[];
  totals: { qty_in: number; qty_out: number; net: number; count: number };
}

export const stockLedgerApi = {
  get: (params?: { product?: number; warehouses?: string; date_from?: string; date_to?: string; sources?: string }) =>
    api.get<StockLedgerData>('/stock/ledger/', { params }).then((r) => r.data),
};

// ── Tax report (rekap pajak per tag dari baris dokumen lintas modul) ──

export interface TaxReportModule {
  key: string;
  label: string;
  short: string;
}

export interface TaxReportBucket {
  dpp: number;
  tax_amount: number;
  count: number;
}

export interface TaxReportRow extends TaxReportBucket {
  tax_id: number;
  name: string;
  rate: number;
  is_include: boolean;
  by_module: Record<string, TaxReportBucket>;
}

export interface TaxReportData {
  key: string;
  title: string;
  period: { date_from: string; date_to: string };
  include_draft: boolean;
  undated_count: number;
  modules: TaxReportModule[];
  rows: TaxReportRow[];
  totals: TaxReportBucket & { by_module: Record<string, TaxReportBucket> };
}

export const taxReportApi = {
  get: (params?: {
    date_from?: string;
    date_to?: string;
    modules?: string;
    taxes?: string;
    include_draft?: string;
  }) => api.get<TaxReportData>('/tax/report/', { params }).then((r) => r.data),
};
