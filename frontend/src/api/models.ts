import api from './client';

export interface FieldConfig {
  type: string;
  label: string;
  required: boolean;
  default: unknown;
  help_text: string;
  max_length?: number;
  min_length?: number;
  currency?: string;
  options?: { value: string; label: string }[];
  relation?: string;
  chatter_show?: boolean;
  virtual?: boolean;
  autofill?: Record<string, string>;
  allow_duplicate?: boolean;
  onchange?: Record<string, unknown>;
}

export interface ListViewConfig {
  columns?: string[];
  filters?: string[];
  group_by?: string[];
  default_sort?: string[];
}

export interface ModelConfig {
  model_name: string;
  verbose_name: string;
  verbose_name_plural: string;
  fields: Record<string, FieldConfig>;
  form_view: {
    header?: {
      fields?: string[];
      actions?: { label: string; icon: string; color: string }[];
      smart_buttons?: { label: string; model?: string; count: number; color?: string; icon?: string }[];
    };
    notebook?: {
      key: string;
      label: string;
      fields?: string[];
      relation?: string;
      summary?: Record<string, unknown>;
    }[];
  } | null;
  list_view: ListViewConfig | null;
}

export interface ModelInfo {
  model_name: string;
  verbose_name: string;
  verbose_name_plural: string;
}

export const modelApi = {
  /** Get list of all registered ERP models */
  listModels: () =>
    api.get<ModelInfo[]>('/models/').then((r) => r.data),

  /** Get model config (fields + views) */
  getConfig: (modelName: string) =>
    api.get<ModelConfig>(`/models/${modelName}/config/`).then((r) => r.data),

  /** List records — supports server-side pagination */
  listRecords: (modelName: string, page?: number, pageSize?: number, extraParams?: Record<string, string>) => {
    const params: Record<string, string> = {};
    if (page !== undefined) params.page = String(page);
    if (pageSize !== undefined) params.page_size = String(pageSize);
    if (extraParams) Object.assign(params, extraParams);
    return api.get<{
      count: number;
      results: Record<string, unknown>[];
      page: number;
      page_size: number;
    }>(`/models/${modelName}/records/`, { params }).then((r) => r.data);
  },

  /** Get single record */
  getRecord: (modelName: string, id: number) =>
    api.get<Record<string, unknown>>(`/models/${modelName}/records/${id}/`).then((r) => r.data),

  /** Create record */
  createRecord: (modelName: string, data: Record<string, unknown>) =>
    api.post(`/models/${modelName}/records/`, data).then((r) => r.data),

  /** Update record */
  updateRecord: (modelName: string, id: number, data: Record<string, unknown>) =>
    api.put(`/models/${modelName}/records/${id}/`, data).then((r) => r.data),

  /** Soft-delete record */
  deleteRecord: (modelName: string, id: number) =>
    api.delete(`/models/${modelName}/records/${id}/`),

  /** Execute a named action on a record (confirm, approve, print, etc.) */
  postAction: (modelName: string, id: number, action: string, extraData?: Record<string, unknown>) =>
    api.post<Record<string, unknown>>(`/models/${modelName}/records/${id}/action/`, { action, ...extraData }).then((r) => r.data),

  /** Compute: send partial data, get computed field values back */
  compute: (modelName: string, data: Record<string, unknown>) =>
    api.post<Record<string, unknown>>(`/models/${modelName}/compute/`, data).then((r) => r.data),

  /** Get chatter logs for a record */
  getChatterLogs: (modelName: string, recordId: number) =>
    api.get<{ id: number; field_name: string; old_value: string | null; new_value: string | null; created_by: number | null; created_by_name: string | null; created_at: string }[]>(
      `/chatter/${modelName}/${recordId}/`
    ).then((r) => r.data),
};
