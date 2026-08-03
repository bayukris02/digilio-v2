import api from './client';
import type { FieldConfig } from './models';

export type BlockType = 'kpi' | 'pie' | 'bar' | 'line' | 'funnel' | 'aging' | 'summary' | 'grid';

export interface DashboardBlockData {
  value?: number;
  series?: { label: string; value: number }[];
  rows?: Record<string, unknown>[];
  count?: number;
  page?: number;
  page_size?: number;
  error?: string;
}

export interface DashboardBlock {
  key: string;
  title: string;
  type: BlockType;
  span?: number;
  model: string;
  aggregate?: { field: string; func: 'count' | 'sum' | 'avg' };
  group_by?: string;
  date_field?: string;
  filters?: Record<string, unknown>;
  limit?: number;
  sort?: string;
  order_by?: string[];
  columns?: string[];
  items?: { label: string; model: string; filters?: Record<string, unknown> }[];
  buckets?: { key: string; label: string; min_days?: number; max_days?: number }[];
  page_size?: number;
  height?: number;
  data: DashboardBlockData;
}

export interface DashboardData {
  key: string;
  title: string;
  blocks: DashboardBlock[];
  fields: Record<string, Record<string, FieldConfig>>;
}

export interface DashboardParams {
  date_from?: string;
  date_to?: string;
  /** Pagination per block: { [`page_${key}`]: n, [`page_size_${key}`]: n } */
  [key: string]: string | undefined;
}

export const dashboardApi = {
  /** Fetch dashboard config + computed data for all blocks (single round trip) */
  get: (key: string, params?: DashboardParams) =>
    api.get<DashboardData>(`/dashboards/${key}/`, { params }).then((r) => r.data),
};
