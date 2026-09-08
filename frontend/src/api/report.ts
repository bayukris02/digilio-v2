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

// ── Stock Balance (agregasi StockEngine dari stock ledger) ──

export interface StockBalanceRow {
  product_id: number;
  code: string;
  name: string;
  uom: string;
  opening: number;
  qty_in: number;
  qty_out: number;
  closing: number;
}

export interface StockBalanceData {
  key: string;
  title: string;
  period: { date_from: string; date_to: string };
  rows: StockBalanceRow[];
  totals: { opening: number; qty_in: number; qty_out: number; closing: number };
}

export const stockBalanceApi = {
  get: (params?: { date_from?: string; date_to?: string; location?: number }) =>
    api.get<StockBalanceData>('/stock/balance/', { params }).then((r) => r.data),
};
