import { useState, useEffect, useRef, useCallback } from 'react';
import { Modal, Radio, Card, Row, Col, Space, Typography, Tag, InputNumber, Button, Select, DatePicker, Input, Spin } from 'antd';
import dayjs from 'dayjs';
import ProgressBar from './ProgressBar';

const { Text } = Typography;
const { TextArea } = Input;

/** Option for one2many line selection — each row is a record from the parent's relation */
interface WizardLineItem {
  id?: number;
  _key?: string;
  product?: { value: number; label: string } | number | null;
  qty?: number;
  uom?: string;
  price?: number;
  [key: string]: unknown;
}

interface WizardTableColumn {
  key: string;
  label: string;
}

interface WizardMode {
  value: string;
  label: string;
  icon?: string;
  inputs?: WizardInput[];
  table?: {
    title?: string;
    columns: WizardTableColumn[];
  };
}

interface WizardInput {
  key: string;
  label: string;
  type: string;
  default?: number | string;
  min?: number;
  max?: number;
  options?: { value: string; label: string }[];
}

interface EditableColumnConfig {
  key: string;
  label: string;
  type: string;
  relation?: string;
  options?: { value: string; label: string }[];
}

interface LineSelectionConfig {
  relation: string;
  columns: string[];
  show_for_modes: string[];
  qty_label?: string;
  editable_columns?: EditableColumnConfig[];
  default_selected?: boolean;
  // Kolom yang dirender sebagai progress bar (ProgressBar) — config-driven,
  // default kosong → wizard lain (PO/SO/PR) tidak berubah
  progress_columns?: string[];
}

export interface WizardConfig {
  title: string;
  modes: WizardMode[];
  line_selection?: LineSelectionConfig;
}

export interface SelectedLine {
  id: number;
  qty: number;
  [key: string]: unknown;
}

interface GenericWizardModalProps {
  visible: boolean;
  config: WizardConfig;
  items: WizardLineItem[];
  onConfirm: (mode: string, selectedLines: SelectedLine[], extraInputs?: Record<string, number | string>) => void;
  onCancel: () => void;
  /** Optional — untuk mode bertipe `table`: fetch data dari backend saat mode dipilih */
  onFetchTable?: (mode: string) => Promise<{ rows: Record<string, unknown>[] }>;
}

function ModeCards({
  modes,
  selected,
  onChange,
}: {
  modes: WizardMode[];
  selected: string;
  onChange: (v: string) => void;
}) {
  return (
    <Radio.Group value={selected} onChange={(e) => onChange(e.target.value)}>
      <Space style={{ width: '100%' }}>
        {modes.map((mode) => (
          <Card
            key={mode.value}
            size="small"
            hoverable
            onClick={() => onChange(mode.value)}
            style={{
              cursor: 'pointer',
              border: selected === mode.value ? '2px solid #1677ff' : '1px solid #d9d9d9',
              background: selected === mode.value ? '#e6f4ff' : '#fff',
            }}
          >
            <Radio value={mode.value}>
              <Text strong>{mode.label}</Text>
            </Radio>
          </Card>
        ))}
      </Space>
    </Radio.Group>
  );
}

/** Wizard input for many2one field — Select dengan fetch dari API */
function Many2OneWizardInput({ inp, value, onChange, many2oneOptions, onFetch }: {
  inp: WizardInput & { relation?: string };
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  many2oneOptions: Record<string, { value: number; label: string }[]>;
  onFetch: (relation: string) => void;
}) {
  const relation = inp.relation || '';
  const opts = many2oneOptions[relation] || [];

  useEffect(() => {
    if (relation && opts.length === 0) onFetch(relation);
  }, [relation]);

  return (
    <Select
      style={{ width: '100%' }}
      value={value && value !== 0 ? value : undefined}
      onChange={(v) => onChange(v ?? undefined)}
      showSearch
      placeholder={`Pilih ${inp.label}`}
      options={opts}
      filterOption={(input, option) =>
        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
      }
      onFocus={() => onFetch(relation)}
      allowClear
    />
  );
}

interface LineSelectorProps {
  items: WizardLineItem[];
  selectedIds: number[];
  columns: string[];
  qtys: Record<number, number>;
  qtyLabel: string;
  editableColumns: EditableColumnConfig[];
  editableValues: Record<number, Record<string, unknown>>;
  many2oneOptions: Record<string, { value: number; label: string }[]>;
  progressColumns?: string[];
  onToggle: (id: number) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onQtyChange: (id: number, qty: number) => void;
  onEditableChange: (id: number, key: string, value: unknown) => void;
  onFetchMany2One: (relation: string) => void;
}

function LineSelector({
  items, selectedIds, columns, qtys, qtyLabel,
  editableColumns, editableValues, many2oneOptions, progressColumns = [],
  onToggle, onSelectAll, onDeselectAll, onQtyChange,
  onEditableChange, onFetchMany2One,
}: LineSelectorProps) {
  const displayValue = (item: WizardLineItem, col: string): string => {
    const val = item[col];
    if (val == null) return '';
    if (typeof val === 'object' && val !== null) {
      return (val as { label?: string; name?: string }).label || (val as { label?: string; name?: string }).name || `#${(val as { id?: number }).id}`;
    }
    return String(val);
  };

  const allSelected = items.length > 0 && selectedIds.length === items.length;

  return (
    <div style={{ maxHeight: 350, overflowY: 'auto', border: '1px solid #e8e8e8', borderRadius: 6 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: '#fafafa', borderBottom: '1px solid #e8e8e8' }}>
            <th style={{ padding: '6px 8px', width: 36, textAlign: 'center' }}>
              <input type="checkbox" checked={allSelected} onChange={(e) => e.target.checked ? onSelectAll() : onDeselectAll()} />
            </th>
            <th style={{ padding: '6px 8px', textAlign: 'left', width: 28 }}>#</th>
            {columns.map((col) => (
              <th key={col} style={{ padding: '6px 8px', textAlign: 'left', textTransform: 'capitalize' }}>{col}</th>
            ))}
            {editableColumns.map((ec) => (
              <th key={ec.key} style={{ padding: '6px 8px', textAlign: 'left', minWidth: 120 }}>{ec.label}</th>
            ))}
            <th style={{ padding: '6px 8px', textAlign: 'left', width: 80 }}>{qtyLabel}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => {
            const id = item.id ?? idx;
            const numId = Number(id);
            const checked = selectedIds.includes(numId);
            return (
              <tr
                key={item._key || item.id || idx}
                style={{
                  background: checked ? '#e6f4ff' : undefined,
                  borderBottom: '1px solid #f0f0f0',
                }}
              >
                <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                  <input type="checkbox" checked={checked} onChange={() => onToggle(numId)} />
                </td>
                <td style={{ padding: '6px 8px' }}>{idx + 1}</td>
                {columns.map((col) => (
                  <td key={col} style={{ padding: '6px 8px' }}>
                    {progressColumns.includes(col)
                      ? <ProgressBar value={Number(item[col])} />
                      : displayValue(item, col)}
                  </td>
                ))}
                {editableColumns.map((ec) => {
                  const val = editableValues[numId]?.[ec.key];
                  if (ec.type === 'many2one' && ec.relation) {
                    const opts = many2oneOptions[ec.relation] || [];
                    return (
                      <td key={ec.key} style={{ padding: '4px 8px' }} onClick={(e) => e.stopPropagation()}>
                        <Select
                          size="small"
                          style={{ width: '100%', minWidth: 120 }}
                          value={val as number | undefined}
                          onChange={(v) => onEditableChange(numId, ec.key, v)}
                          showSearch
                          placeholder={`Pilih ${ec.label}`}
                          options={opts}
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          onFocus={() => onFetchMany2One(ec.relation!)}
                          disabled={!checked}
                        />
                      </td>
                    );
                  }
                  // Default: InputNumber
                  return (
                    <td key={ec.key} style={{ padding: '4px 8px' }} onClick={(e) => e.stopPropagation()}>
                      <InputNumber
                        size="small"
                        min={0}
                        value={(val as number) ?? 0}
                        disabled={!checked}
                        onChange={(v) => onEditableChange(numId, ec.key, v ?? 0)}
                        style={{ width: 80 }}
                      />
                    </td>
                  );
                })}
                <td style={{ padding: '4px 8px' }} onClick={(e) => e.stopPropagation()}>
                  <InputNumber
                    size="small"
                    min={0}
                    value={qtys[numId] ?? 0}
                    disabled={!checked}
                    onChange={(val) => onQtyChange(numId, val ?? 0)}
                    style={{ width: 72 }}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function GenericWizardModal({
  visible,
  config,
  items,
  onConfirm,
  onCancel,
  onFetchTable,
}: GenericWizardModalProps) {
  const [selectedMode, setSelectedMode] = useState<string>(config.modes[0]?.value || '');
  const [selectedIds, setSelectedIds] = useState<number[]>(
    config.line_selection?.default_selected === false
      ? []
      : items.filter((item) => item.id != null).map((item) => Number(item.id))
  );
  const [qtys, setQtys] = useState<Record<number, number>>(() => {
    const q: Record<number, number> = {};
    items.forEach((item) => {
      if (item.id != null) q[Number(item.id)] = Number(item.qty ?? 0);
    });
    return q;
  });
  const [editableValues, setEditableValues] = useState<Record<number, Record<string, unknown>>>(() => {
    const ev: Record<number, Record<string, unknown>> = {};
    items.forEach((item) => {
      if (item.id != null) {
        ev[Number(item.id)] = {};
      }
    });
    return ev;
  });
  const [many2oneOptions, setMany2oneOptions] = useState<Record<string, { value: number; label: string }[]>>({});
  // State untuk mode bertipe `table` (read-only view)
  const [tableData, setTableData] = useState<{ rows: Record<string, unknown>[]; loading: boolean; error?: string }>({ rows: [], loading: false });
  const [extraInputValues, setExtraInputValues] = useState<Record<string, number | string>>(() => {
    const currentMode = config.modes.find((m) => m.value === selectedMode);
    const vals: Record<string, number | string> = {};
    currentMode?.inputs?.forEach((inp) => {
      if (inp.default !== undefined) vals[inp.key] = inp.default;
      else if (inp.type === 'selection') vals[inp.key] = inp.options?.[0]?.value ?? '';
      else if (inp.type === 'date' || inp.type === 'text') vals[inp.key] = '';
      else vals[inp.key] = 0;
    });
    return vals;
  });

  const handleModeChange = (value: string) => {
    setSelectedMode(value);
    const newMode = config.modes.find((m) => m.value === value);
    const vals: Record<string, number | string> = {};
    newMode?.inputs?.forEach((inp) => {
      if (inp.default !== undefined) vals[inp.key] = inp.default;
      else if (inp.type === 'selection') vals[inp.key] = inp.options?.[0]?.value ?? '';
      else if (inp.type === 'date' || inp.type === 'text') vals[inp.key] = '';
      else vals[inp.key] = 0;
    });
    setExtraInputValues(vals);
  };

  const itemsFingerprintRef = useRef('');
  const itemsFingerprint = items.map((i) => i.id).join(',');

  useEffect(() => {
    if (itemsFingerprint !== itemsFingerprintRef.current) {
      itemsFingerprintRef.current = itemsFingerprint;
      setSelectedMode(config.modes[0]?.value || '');
      const allIds = items.filter((item) => item.id != null).map((item) => Number(item.id));
      setSelectedIds(config.line_selection?.default_selected === false ? [] : allIds);
      const defaultQtys: Record<number, number> = {};
      items.forEach((item) => {
        if (item.id != null) defaultQtys[Number(item.id)] = Number(item.remaining_bill_qty ?? item.remaining_qty ?? item.qty ?? 0);
      });
      setQtys(defaultQtys);
      // Reset editable values
      const ev: Record<number, Record<string, unknown>> = {};
      items.forEach((item) => {
        if (item.id != null) ev[Number(item.id)] = {};
      });
      setEditableValues(ev);
    }
  }, [itemsFingerprint]);

  // Deteksi mode: semua mode punya line_selection = render sebagai footer buttons
  const allModesShowTable = config.line_selection?.show_for_modes?.length === config.modes.length;
  const showLines = config.line_selection?.show_for_modes?.includes(selectedMode) ?? false;
  const columns = config.line_selection?.columns || [];
  const qtyLabel = config.line_selection?.qty_label || 'Receive Qty';
  const editableColumns = config.line_selection?.editable_columns || [];
  const progressColumns = config.line_selection?.progress_columns || [];
  const currentMode = config.modes.find((m) => m.value === selectedMode);
  const extraInputs = currentMode?.inputs || [];
  // Konfigurasi mode tabel (read-only view) — di-capture ke const lokal agar
  // narrowing TypeScript tetap berlaku di dalam closure JSX
  const tableCfg = currentMode?.table;
  const tableTitle = tableCfg?.title || 'Data';
  const tableColumns = tableCfg?.columns || [];

  const handleExtraInputChange = (key: string, value: number | string | null) => {
    setExtraInputValues((prev) => ({ ...prev, [key]: value ?? 0 }));
  };

  const handleToggle = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((i) => i !== id);
      return [...prev, id];
    });
  };

  const handleSelectAll = () => {
    setSelectedIds(items.filter((item) => item.id != null).map((item) => Number(item.id)));
  };

  const handleDeselectAll = () => {
    setSelectedIds([]);
  };

  const handleQtyChange = (id: number, qty: number) => {
    setQtys((prev) => ({ ...prev, [id]: qty }));
  };

  const handleEditableChange = (id: number, key: string, value: unknown) => {
    setEditableValues((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), [key]: value },
    }));
  };

  const handleFetchMany2One = async (relation: string) => {
    if (many2oneOptions[relation]) return; // already loaded
    try {
      const token = localStorage.getItem('access_token');
      const resp = await fetch(`/api/models/${relation}/records/?limit=200`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) throw new Error('Fetch failed');
      const data = await resp.json();
      const opts = (data.results || []).map((r: { id: number; display_name?: string }) => ({
        value: r.id,
        label: r.display_name || `#${r.id}`,
      }));
      setMany2oneOptions((prev) => ({ ...prev, [relation]: opts }));
    } catch {
      // silently fail
    }
  };

  const handleConfirm = (mode?: string) => {
    const m = mode || selectedMode;
    const modeCfg = config.modes.find((x) => x.value === m);
    if (modeCfg?.table) return; // mode tampilan tabel — read-only, tidak ada aksi
    const selectedLines = selectedIds.map((id) => ({
      id,
      qty: qtys[id] ?? 0,
      ...(editableValues[id] || {}),
    }));
    onConfirm(m, selectedLines, extraInputValues);
  };

  // ── Mode tabel: fetch data dari backend via onFetchTable ──
  const loadTable = useCallback((modeValue: string) => {
    if (!onFetchTable) return;
    setTableData({ rows: [], loading: true, error: undefined });
    onFetchTable(modeValue)
      .then((res) => setTableData({ rows: res.rows || [], loading: false }))
      .catch(() => setTableData({ rows: [], loading: false, error: 'Gagal memuat data' }));
  }, [onFetchTable]);

  useEffect(() => {
    if (!visible || !currentMode?.table) return;
    loadTable(selectedMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMode, visible]);

  // Footer buttons
  const renderFooter = () => {
    if (currentMode?.table) {
      // Mode tampilan tabel — hanya Refresh + Cancel
      return (
        <Space>
          <Button onClick={() => loadTable(selectedMode)} disabled={tableData.loading}>Refresh</Button>
          <Button onClick={onCancel}>Cancel</Button>
        </Space>
      );
    }
    if (allModesShowTable) {
      return (
        <Space>
          {config.modes.map((mode) => (
            <Button key={mode.value} type="primary" onClick={() => handleConfirm(mode.value)}>
              {mode.label}
            </Button>
          ))}
          <Button onClick={onCancel}>Cancel</Button>
        </Space>
      );
    }
    // Backward compat: default footer
    return undefined;
  };

  return (
    <Modal
      title={<Text strong>{config.title}</Text>}
      open={visible}
      onOk={() => handleConfirm()}
      onCancel={onCancel}
      okText={allModesShowTable ? undefined : "Confirm"}
      cancelText="Cancel"
      width={640}
      destroyOnClose
      footer={renderFooter()}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {!allModesShowTable && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Mode</Text>
            <ModeCards modes={config.modes} selected={selectedMode} onChange={handleModeChange} />
          </div>
        )}

        {extraInputs.length > 0 && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Input</Text>
            <Row gutter={16}>
              {extraInputs.map((inp) => (
                <Col span={12} key={inp.key}>
                  <div style={{ marginBottom: 0 }}>
                    {inp.label && <Text style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>{inp.label}</Text>}
                    {inp.type === 'selection' && inp.options ? (
                      <Radio.Group
                        value={extraInputValues[inp.key] ?? inp.default ?? inp.options[0]?.value}
                        onChange={(e) => handleExtraInputChange(inp.key, e.target.value)}
                        optionType="button"
                        buttonStyle="solid"
                        options={inp.options}
                      />
                    ) : inp.type === 'many2one' ? (
                      <Many2OneWizardInput
                        inp={inp}
                        value={extraInputValues[inp.key] as number | undefined}
                        onChange={(v) => handleExtraInputChange(inp.key, v)}
                        many2oneOptions={many2oneOptions}
                        onFetch={handleFetchMany2One}
                      />
                    ) : inp.type === 'date' ? (
                      <DatePicker
                        style={{ width: '100%' }}
                        value={extraInputValues[inp.key] ? dayjs(extraInputValues[inp.key] as string) : null}
                        onChange={(d) => handleExtraInputChange(inp.key, d ? d.format('YYYY-MM-DD') : '')}
                      />
                    ) : inp.type === 'text' ? (
                      <TextArea
                        rows={3}
                        value={extraInputValues[inp.key] as string ?? ''}
                        onChange={(e) => handleExtraInputChange(inp.key, e.target.value)}
                      />
                    ) : (() => {
                      const isDpValue = inp.key === 'dp_value';
                      const dpMode = extraInputValues['dp_mode'];
                      const isPercentage = isDpValue && dpMode === 'percentage';
                      return (
                        <InputNumber
                          min={inp.min ?? 0}
                          max={isPercentage ? 100 : inp.max}
                          addonAfter={isPercentage ? '%' : undefined}
                          value={extraInputValues[inp.key] as number ?? (inp.default as number ?? 0)}
                          onChange={(val) => handleExtraInputChange(inp.key, val)}
                          style={{ width: '100%' }}
                        />
                      );
                    })()}
                  </div>
                </Col>
              ))}
            </Row>
          </div>
        )}

        {(allModesShowTable || showLines) && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              Pilih Barang
              <Tag style={{ marginLeft: 8 }}>{selectedIds.length} of {items.length} selected</Tag>
            </Text>
            <LineSelector
              items={items}
              selectedIds={selectedIds}
              columns={columns}
              qtys={qtys}
              qtyLabel={qtyLabel}
              editableColumns={editableColumns}
              editableValues={editableValues}
              many2oneOptions={many2oneOptions}
              progressColumns={progressColumns}
              onToggle={handleToggle}
              onSelectAll={handleSelectAll}
              onDeselectAll={handleDeselectAll}
              onQtyChange={handleQtyChange}
              onEditableChange={handleEditableChange}
              onFetchMany2One={handleFetchMany2One}
            />
          </div>
        )}

        {tableCfg && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              {tableTitle}
            </Text>
            {tableData.loading ? (
              <div style={{ textAlign: 'center', padding: 24 }}>
                <Spin />
              </div>
            ) : (
              <div style={{ maxHeight: 350, overflowY: 'auto', border: '1px solid #e8e8e8', borderRadius: 6 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#fafafa', borderBottom: '1px solid #e8e8e8' }}>
                      {tableColumns.map((c) => (
                        <th key={c.key} style={{ padding: '8px 10px', textAlign: 'left' }}>{c.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.rows.length === 0 ? (
                      <tr>
                        <td
                          colSpan={tableColumns.length}
                          style={{ padding: 16, textAlign: 'center', color: '#999' }}
                        >
                          {tableData.error || 'Tidak ada dokumen untuk milestone ini'}
                        </td>
                      </tr>
                    ) : (
                      tableData.rows.map((row, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                          {tableColumns.map((c) => (
                            <td key={c.key} style={{ padding: '8px 10px' }}>
                              {String(row[c.key] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Space>
    </Modal>
  );
}
