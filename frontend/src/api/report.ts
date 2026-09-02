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
