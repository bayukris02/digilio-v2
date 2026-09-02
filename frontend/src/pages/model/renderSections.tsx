/**
 * ============================================================================
 * renderSections — buildTabItems (ModelFormPage)
 * ============================================================================
 * Menampung `buildTabItems`: membangun array tab (Ant Tabs items) dari config
 * form_view — dipakai untuk BOTH header tabs (field form) dan notebook tabs
 * (AG Grid line items + SummaryCard).
 *
 * Bagian penting yang di-render di sini:
 *  - Tab field: Form + Row/Col, renderField per field (dengan field_config_rules
 *    hide_when / field_props), hidden_statuses.
 *  - Tab relation (notebook): AG Grid line items — row drag, pinned bottom
 *    summary row (sum/avg dari tab.summary.columns), domain-aware many2one
 *    options (onCellClicked refetch + filter), onCellValueChanged (autofill +
 *    compute API backend), tombol +Add (addLine), dan SummaryCard.
 *
 * Semua dependency disuntik via satu object `ctx` — hook/komponen ini murni
 * organisasi, TIDAK ada state internal, TIDAK ada perubahan perilaku.
 *
 * ATURAN: core frontend — WAJIB generik (no `if model_name ===`).
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST:
 * 1. Header tabs: semua field tampil 3 kolom; hidden_statuses & hide_when
 *    (field_config_rules) menyembunyikan field; field_props override properti.
 * 2. Notebook grid: +Add baris (add_line_guard & validasi baris sebelumnya),
 *    drag reorder → urutan lineItems ikut, pinned bottom row sum/avg benar.
 * 3. onCellValueChanged: edit nilai → state & summary refresh; many2one autofill
 *    (name/uom terisi); compute API backend (diskon/pajak/total) tetap jalan.
 * 4. Klik cell many2one → options ter-filter domain header & opsi terpilih
 *    baris lain disembunyikan; infinite scroll lanjut halaman.
 * 5. SummaryCard di bawah notebook: recompute & merge _computed_o2m_lines
 *    (tanpa menimpa nilai yang diedit manual).
 * ============================================================================
 */
import type { CSSProperties, ReactNode } from 'react';
import { Form, Row, Col, Spin, message } from 'antd';
import SummaryCard from '../../components/SummaryCard';
import { AgGridReact } from 'ag-grid-react';
import type { CellValueChangedEvent } from 'ag-grid-community';
import { themeBalham } from 'ag-grid-community';
import { modelApi, type ModelConfig } from '../../api/models';
import { renderField, M2O_PAGE_SIZE } from './formControls';

export type TabConfig = {
  key: string;
  label: string;
  fields?: string[];
  relation?: string;
  columns?: (string | { name: string; display_field?: string })[];
  read_only?: boolean;
  summary?: Record<string, unknown>;
};

type Ctx = {
  tabs: TabConfig[];
  form: any;
  handleFormChange: (changedValues?: Record<string, unknown>) => void;
  initialValues: Record<string, unknown>;
  apiModelName: string;
  recordId?: string;
  loadKey: number;
  config: ModelConfig;
  currentStatus?: string;
  setQuickView: (v: { modelName: string; recordId: number } | null) => void;
  isFieldDisabled: (fieldKey: string) => boolean;
  childConfigs: Record<string, ModelConfig>;
  lineItems: Record<string, Record<string, unknown>[]>;
  setLineItems: React.Dispatch<React.SetStateAction<Record<string, Record<string, unknown>[]>>>;
  columnFieldValues: Record<string, unknown>;
  isReadOnly: boolean;
  buildColumns: (relationField: string, columnFilter?: (string | { name: string; display_field?: string })[], tabReadOnly?: boolean, rowActions?: Array<{ label: string; actions?: Array<{ label: string; action?: string; wizard?: Record<string, unknown> }> }>) => any[];
  setAddingLine: React.Dispatch<React.SetStateAction<boolean>>;
  addLine: (relationField: string) => void;
  setMany2oneOptions: React.Dispatch<React.SetStateAction<Record<string, { value: number; label: string; uom?: string }[]>>>;
  setMany2oneMeta: React.Dispatch<React.SetStateAction<Record<string, { page: number; total: number; loading: boolean; params: Record<string, string> }>>>;
  setSummaryRevision: React.Dispatch<React.SetStateAction<number>>;
  handleNavigate: (targetModel: string, targetId: number) => void;
  summaryRevision: number;
  recordData?: Record<string, unknown> | undefined;
};

/** Build tab items (reusable for both header tabs and notebook tabs) */
export function buildTabItems(ctx: Ctx): Array<{ key: string; label: string; children: ReactNode }> {
  const {
    tabs, form, handleFormChange, initialValues, apiModelName, recordId, loadKey,
    config, currentStatus, setQuickView, isFieldDisabled, childConfigs, lineItems,
    setLineItems, columnFieldValues, isReadOnly, buildColumns, setAddingLine, addLine,
    setMany2oneOptions, setMany2oneMeta, setSummaryRevision, handleNavigate,
    summaryRevision, recordData,
  } = ctx;

  return tabs
    .filter((tab) => {
      // Tab opsional: hanya muncul kalau relasinya sudah punya data (mis. tab Cicilan)
      if ((tab as any)?.show_when_has_data) {
        return ((lineItems[(tab as any).relation] || []) as unknown[]).length > 0;
      }
      return true;
    })
    .map((tab) => ({
    key: tab.key,
    label: tab.label,
    children: tab.fields ? (
      <Form form={form} layout="vertical" onValuesChange={handleFormChange} initialValues={initialValues} key={`${apiModelName}-${recordId || 'new'}-${loadKey}`}>
        <Row gutter={16}>
          {tab.fields.length > 0 ? tab.fields.map((fieldName: string) => {
            const field = config?.fields?.[fieldName];
            if (!field) return null;
            // Skip field if hidden for current status
            if (currentStatus && Array.isArray((field as any)?.hidden_statuses)
                && (field as any).hidden_statuses.includes(currentStatus)) return null;
            // ── field_config_rules: hide_when (generic dari backend) ──
            const fieldRules = config?.field_config_rules?.[fieldName];
            if (fieldRules?.hide_when) {
              const shouldHide = Object.entries(fieldRules.hide_when).some(
                ([wf, val]) => form.getFieldValue(wf) === val,
              );
              if (shouldHide) return null;
            }
            // ── field_config_rules: field_props (override properti dinamis) ──
            let effectiveField = field as Record<string, unknown>;
            if (fieldRules?.field_props) {
              effectiveField = { ...effectiveField };
              for (const [prop, cfg] of Object.entries(fieldRules.field_props)) {
                if ((cfg as Record<string, unknown>).depends_on) {
                  const depVal = form.getFieldValue((cfg as Record<string, unknown>).depends_on as string);
                  if ((cfg as Record<string, unknown>)[depVal] !== undefined) {
                    (effectiveField as Record<string, unknown>)[prop] = (cfg as Record<string, unknown>)[depVal];
                  }
                }
              }
            }
            return (
              <Col span={8} key={fieldName}>
                {renderField(fieldName, effectiveField as any, {}, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(fieldName), form)}
              </Col>
            );
          }) : (
            <Col span={24}>
              <div style={{ padding: 16, color: '#999', textAlign: 'center' }}>
                No additional details configured.
              </div>
            </Col>
          )}
        </Row>
      </Form>
    ) : tab.relation ? (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ width: '100%', minHeight: 80 }}>
          {!childConfigs[tab.relation!] ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : (
          <>
          {(() => {
            // Compute pinned bottom row from columns config
            const columnsConfig = (tab.summary?.columns || {}) as Record<string, string>;
            const items = (lineItems[tab.relation!] || []) as Record<string, unknown>[];
            const hasAgg = Object.keys(columnsConfig).length > 0 && items.length > 0;
            const pinnedBottomRowData = hasAgg ? (() => {
              const row: Record<string, unknown> = { _rowNum: '∑' };
              const aggStyles: Record<string, CSSProperties> = {};
              for (const [field, func] of Object.entries(columnsConfig)) {
                const nums = items.map(it => Number(it[field]) || 0);
                if (nums.length === 0) continue;
                let val: number;
                if (func === 'sum') {
                  val = parseFloat(nums.reduce((a, b) => a + b, 0).toFixed(2));
                  aggStyles[field] = { fontWeight: 'bold' };
                } else if (func === 'avg') {
                  val = parseFloat((nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2));
                  aggStyles[field] = { textDecoration: 'underline' };
                } else {
                  continue;
                }
                row[field] = val;
              }
              row._aggStyles = aggStyles;
              return [row];
            })() : undefined;
            return (
          <AgGridReact
            key={`grid-${JSON.stringify(columnFieldValues)}`}
            rowData={(isReadOnly || tab.read_only) ? items : [...items, { _key: '_add_button', _isAddButton: true }]}
            columnDefs={buildColumns(tab.relation!, tab.columns, tab.read_only, (tab as any).row_actions)}
            getRowId={(params) => params.data._key}
            animateRows
            rowDragManaged
            postSortRows={(params) => {
              // +Add selalu di baris paling bawah — tidak ikut sort asc/desc
              const nodes = params.nodes;
              const addIdx = nodes.findIndex(
                (n) => (n.data as Record<string, unknown> | undefined)?._isAddButton
              );
              if (addIdx >= 0) {
                const [addNode] = nodes.splice(addIdx, 1);
                nodes.push(addNode);
              }
            }}
            onRowDragEnd={(params) => {
              // Sync state lineItems mengikuti urutan visual grid setelah drag
              const relationField = tab.relation!;
              const orderedKeys: string[] = [];
              params.api.forEachNode((node) => {
                const k = (node.data as Record<string, unknown> | undefined)?._key;
                if (k && k !== '_add_button') orderedKeys.push(k as string);
              });
              setLineItems((prev) => {
                const items = prev[relationField] || [];
                const byKey = new Map(items.map((it) => [it._key, it]));
                const reordered = orderedKeys
                  .map((k) => byKey.get(k))
                  .filter((it): it is Record<string, unknown> => !!it);
                return { ...prev, [relationField]: reordered };
              });
            }}
            onRowClicked={(params) => {
              if (params.data?._isAddButton && !isReadOnly && !tab.read_only) {
                setAddingLine(true);
                addLine(tab.relation!);
                setAddingLine(false);
              }
            }}
            onCellClicked={(params) => {
              // Refresh many2one options tiap ada klik cell many2one
              const childCfg = childConfigs[tab.relation!];
              const fieldName = params.colDef.field;
              const displayField = (params.colDef as any)?.displayField;
              if (childCfg?.fields && fieldName) {
                const fieldMeta = childCfg.fields[fieldName];
                if ((fieldMeta?.type === 'many2one' || fieldMeta?.type === 'many2many') && fieldMeta.relation) {
                  // domain: filter related records berdasarkan field header
                  // definisi di Many2OneField: domain={'vendor': 'vendor'}
                  const domain = (fieldMeta as any)?.domain as Record<string, string> | undefined;
                  const extraParams: Record<string, string> = {};
                  if (domain) {
                    Object.entries(domain).forEach(([relatedField, headerField]) => {
                      const isFormField = config?.fields?.[headerField] != null;
                      const headerVal = isFormField ? form.getFieldValue(headerField) : headerField;
                      if (headerVal != null) {
                        extraParams[relatedField] = String(headerVal);
                      }
                    });
                  }
                  modelApi.listRecords(fieldMeta.relation, 1, M2O_PAGE_SIZE, extraParams)
                    .then((response) => {
                      const opts = response.results.map((r) => ({
                        ...r,
                        value: r.id as number,
                        label: displayField
                          ? ((r[displayField] as string) || `#${r.id}`)
                          : ((r.name as string) || `#${r.id}`),
                      }));
                      const optKey = `${tab.relation!}.${fieldName}`;
                      setMany2oneOptions((prev) => ({
                        ...prev,
                        [optKey]: opts,
                      }));
                      setMany2oneMeta((prev) => ({
                        ...prev,
                        [optKey]: { page: 1, total: response.count, loading: false, params: extraParams },
                      }));
                    })
                    .catch(() => {});
                }
              }
            }}
            onCellValueChanged={(params: CellValueChangedEvent) => {
              if (params.newValue === params.oldValue) return;
              const relationField = tab.relation!;
              const childFields = childConfigs[relationField]?.fields;
              const lineKey = params.data._key;

              // 1. Apply edit immediately in state
              setLineItems((prev) => {
                const items = [...(prev[relationField] || [])];
                const idx = items.findIndex((item) => item._key === lineKey);
                if (idx < 0) return prev;
                items[idx] = { ...items[idx], [params.colDef.field!]: params.newValue };
                return { ...prev, [relationField]: items };
              });
              // Force parent compute (SummaryCard) agar summary refresh
              // setelah line value berubah — regardless of child compute result.
              setSummaryRevision((v) => v + 1);

              // 2. Many2One: auto-fill from related record
              const editedField = childFields?.[params.colDef.field!];
              const updatedLine = { ...params.data, [params.colDef.field!]: params.newValue };
              let autofilledLine: Record<string, unknown> = updatedLine;
              if (editedField?.type === 'many2one' && editedField.relation && params.newValue) {
                const relVal = params.newValue as Record<string, unknown>;
                const autofillMap = ((editedField as Record<string, unknown>)?.autofill || {}) as Record<string, string>;
                const id = (relVal.value ?? relVal.id) as number || 0;
                const name = (relVal.label ?? relVal.name) as string || `#${id}`;
                autofilledLine = {
                  ...updatedLine,
                  [params.colDef.field!]: { id, name },
                };
                Object.entries(autofillMap).forEach(([targetField, sourceField]) => {
                  const sourceVal = relVal[sourceField as string];
                  if (sourceVal != null && childFields?.[targetField]) {
                    // If source is a Many2One object {id, name}, extract the name string
                    if (typeof sourceVal === 'object' && sourceVal !== null && 'name' in (sourceVal as Record<string, unknown>)) {
                      autofilledLine![targetField] = (sourceVal as Record<string, unknown>).name as string;
                    } else {
                      autofilledLine![targetField] = sourceVal;
                    }
                  }
                });
                setLineItems((prev) => {
                  const items = [...(prev[relationField] || [])];
                  const idx = items.findIndex((item) => item._key === params.data._key);
                  if (idx < 0) return prev;
                  items[idx] = { ...items[idx], ...autofilledLine };
                  return { ...prev, [relationField]: items };
                });
              }
              // 3. Call backend compute API — single source of truth
              const childModelName = (config?.fields?.[relationField] as Record<string, string>)?.relation || '';
              if (childModelName) {
                const { _key, ...lineData } = autofilledLine || updatedLine!;
                modelApi.compute(childModelName, lineData).then((computed) => {
                  if (Object.keys(computed).length === 0) return;
                  setLineItems((prev) => {
                    const items = [...(prev[relationField] || [])];
                    const idx = items.findIndex((item) => item._key === params.data._key);
                    if (idx < 0) return prev;
                    items[idx] = { ...items[idx], ...computed };
                    return { ...prev, [relationField]: items };
                  });
                  // Force parent compute (SummaryCard) agar _compute_summary jalan
                  setSummaryRevision((v) => v + 1);
                }).catch((err: unknown) => {
                  const errMsg = (err as Record<string, unknown>)?.response?.data?.error || (err as Error)?.message || 'Compute error';
                  if (errMsg) message.error(errMsg as string);
                });
              }
            }}
            theme={themeBalham}
            defaultColDef={{ resizable: true, sortable: true, flex: 1, minWidth: 80,
              cellStyle: (p) => {
                if (!p.node?.rowPinned) return undefined;
                const s = (p.data as any)?._aggStyles?.[p.colDef.field!];
                return s || { fontWeight: 'bold' };
              },
            }}
            stopEditingWhenCellsLoseFocus
            singleClickEdit
            domLayout="autoHeight"
            pinnedBottomRowData={pinnedBottomRowData}
          />
          )})()}
          </>
          )}
        </div>
        {tab.summary && (
          <div style={{ borderTop: '2px solid #d9d9d9', paddingTop: 45 }}>
          <SummaryCard
            summary={tab.summary}
            lineItems={lineItems[tab.relation!] || []}
            fields={config.fields}
            form={form}
            modelName={apiModelName}
            readOnly={isReadOnly}
            relation={tab.relation}
            recordId={recordId ? Number(recordId) : undefined}
            recordData={recordData}
            onNavigate={handleNavigate}
            revision={summaryRevision}
            onComputedLines={(rel, computedLines) => {
              setLineItems((prev) => {
                const existing = [...(prev[rel] || [])];
                let changed = false;
                const updated = existing.map((item) => {
                  const match = computedLines.find(
                    (cl) => cl._key === item._key
                  );
                  if (!match) return item;
                  // Merge computed fields from backend (discount_amount, tax_amount, total, dll)
                  const merged = { ...item };
                  for (const [k, v] of Object.entries(match)) {
                    if (k !== '_key' && v !== undefined) {
                      merged[k] = v;
                    }
                  }
                  changed = true;
                  return merged;
                });
                return changed ? { ...prev, [rel]: updated } : prev;
              });
            }}
          />
          </div>
        )}
      </div>
    ) : null,
  }));
}
