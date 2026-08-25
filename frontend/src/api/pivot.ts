import api from './client';

export interface PivotColumn {
  field: string;
  label: string;
  rowGroup?: boolean;
  pivot?: boolean;
  aggFunc?: string;
}

export interface PivotData {
  key: string;
  title: string;
  columns: PivotColumn[];
  rowData: Record<string, unknown>[];
}

export const pivotApi = {
  get: (key: string, params?: { date_from?: string; date_to?: string }) =>
    api.get<PivotData>(`/pivots/${key}/`, { params }).then((r) => r.data),
};
