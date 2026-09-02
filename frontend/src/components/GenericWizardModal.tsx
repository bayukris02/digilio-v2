import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Modal, Radio, Card, Row, Col, Space, Typography, Tag, InputNumber, Button, Select, DatePicker, Input, Spin, Alert, message } from 'antd';
import { HomeOutlined, FileTextOutlined, SendOutlined, BarChartOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import ProgressBar from './ProgressBar';
import { DATE_FORMAT } from '../utils/format';

const { Text } = Typography;
const { TextArea } = Input;

/** Icon name (dari config backend) → komponen antd — generic, tanpa nama model */
const MODE_ICONS: Record<string, React.ReactNode> = {
  HomeOutlined: <HomeOutlined />,
  FileTextOutlined: <FileTextOutlined />,
  SendOutlined: <SendOutlined />,
  BarChartOutlined: <BarChartOutlined />,
};

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

/** Config untuk mode `split` — bagi nilai field parent (source_field) menjadi
 *  N baris dengan tanggal bertahap (date_step). Nominal dihitung di backend
 *  saat confirm; tabel preview di sini hanya untuk pratinjau UX. */
interface WizardSplitConfig {
  source_label?: string;
  source_field: string;
  count_input: string;
  date_input: string;
  date_step?: 'month' | 'day';
  note_prefix?: string;
  currency?: string;
  status?: { label: string; color: string };
  /** Kolom tabel pratinjau — metadata-driven (no/date/number/text/status) */
  columns: WizardEditableColumn[];
}

interface WizardEditableColumn {
  key: string;
  label: string;
  type: 'no' | 'date' | 'number' | 'text' | 'status';
  /** true → sel diedit user (date picker/input number/input text) */
  editable?: boolean;
}

/** Config untuk mode `editable_rows` — tabel baris yang diisi user manual.
 *  Status payment & nomor urut otomatis; sisa tagihan wajib 0 saat confirm
 *  (divalidasi frontend & backend). */
interface WizardEditableRowsConfig {
  source_label?: string;
  source_field: string;
  title?: string;
  note_prefix?: string;
  currency?: string;
  status?: { label: string; color: string };
  columns: WizardEditableColumn[];
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
  split?: WizardSplitConfig;
  editable_rows?: WizardEditableRowsConfig;
}

interface WizardInput {
  key: string;
  label: string;
  type: string;
  default?: number | string;
  min?: number;
  max?: number;
  options?: { value: string; label: string }[];
  relation?: string;
  /** Query params tambahan saat fetch options many2one — value string bisa
   *  berisi placeholder `{record_id}` yang diganti id record aktif. */
  filter?: Record<string, string>;
  /** Field record hasil fetch yang dipakai sebagai value option (default: id). */
  value_field?: string;
  /** Field record hasil fetch yang dipakai sebagai label option (default: display_name). */
  label_field?: string;
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
  onConfirm: (mode: string, selectedLines: SelectedLine[], extraInputs?: Record<string, unknown>) => void;
  onCancel: () => void;
  /** Optional — untuk mode bertipe `table`: fetch data dari backend saat mode dipilih */
  onFetchTable?: (mode: string) => Promise<{ rows: Record<string, unknown>[] }>;
  /** Optional — label kolom line_selection (key → label) dari config child model */
  columnLabels?: Record<string, string>;
  /** Optional — id record parent aktif (untuk placeholder {record_id} di filter many2one) */
  recordId?: number | null;
  /** Optional — data record parent (untuk mode `split`: baca source_field) */
  recordData?: Record<string, unknown> | null;
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
              {mode.icon && MODE_ICONS[mode.icon]}
              {mode.label && (
                <Text strong style={{ marginLeft: mode.icon ? 6 : 0 }}>{mode.label}</Text>
              )}
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
  onFetch: (inp: WizardInput & { relation?: string }) => void;
}) {
  const relation = inp.relation || '';
  const cacheKey = relation + '::' + JSON.stringify(inp.filter || {});
  const opts = many2oneOptions[cacheKey] || [];

  useEffect(() => {
    if (relation && opts.length === 0) onFetch(inp);
  }, [cacheKey]);

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
      onFocus={() => onFetch(inp)}
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
  columnLabels?: Record<string, string>;
  onToggle: (id: number) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onQtyChange: (id: number, qty: number) => void;
  onEditableChange: (id: number, key: string, value: unknown) => void;
  onFetchMany2One: (inp: WizardInput & { relation?: string }) => void;
}

function LineSelector({
  items, selectedIds, columns, qtys, qtyLabel,
  editableColumns, editableValues, many2oneOptions, progressColumns = [], columnLabels = {},
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
              <th key={col} style={{ padding: '6px 8px', textAlign: 'left', textTransform: 'capitalize' }}>{columnLabels[col] ?? col}</th>
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
                    const opts = many2oneOptions[ec.relation + '::' + JSON.stringify((ec as WizardInput).filter || {})] || [];
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
                          onFocus={() => onFetchMany2One(ec as WizardInput & { relation?: string })}
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

/** Tabel baris generic untuk mode split & editable_rows — kolom & perilaku
 *  sepenuhnya dari config (metadata-driven), tanpa string khusus model. */
interface WizardEditableTableProps {
  columns: WizardEditableColumn[];
  rows: Record<string, unknown>[];
  currency?: string;
  status?: { label: string; color: string };
  notePrefix?: string;
  onCellChange?: (idx: number, key: string, value: unknown) => void;
  onRemoveRow?: (idx: number) => void;
}

function WizardEditableTable({
  columns,
  rows,
  currency = '',
  status,
  notePrefix = 'Term ke-',
  onCellChange,
  onRemoveRow,
}: WizardEditableTableProps) {
  const fmt = (v: number) => `${currency}${Number(v || 0).toLocaleString('id-ID')}`;
  return (
    <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid #e8e8e8', borderRadius: 6 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#fafafa', borderBottom: '1px solid #e8e8e8' }}>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{
                  padding: '8px 10px',
                  textAlign: c.type === 'number' ? 'right' : 'left',
                  minWidth: c.type === 'date' ? 170 : c.type === 'number' ? 140 : c.type === 'text' ? 160 : undefined,
                }}
              >
                {c.label}
              </th>
            ))}
            {onRemoveRow && <th style={{ padding: '8px 10px', width: 40 }} />}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length + (onRemoveRow ? 1 : 0)} style={{ padding: 16, textAlign: 'center', color: '#999' }}>
                Belum ada baris
              </td>
            </tr>
          )}
          {rows.map((r, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
              {columns.map((c) => {
                const val = r[c.key];
                const isEditable = !!onCellChange && c.editable;
                return (
                  <td
                    key={c.key}
                    style={{
                      padding: c.type === 'date' || c.type === 'number' || c.type === 'text' ? '4px 10px' : '6px 10px',
                      textAlign: c.type === 'number' ? 'right' : 'left',
                    }}
                  >
                    {c.type === 'no' ? idx + 1
                      : c.type === 'status' ? (status && <Tag color={status.color}>{status.label}</Tag>)
                      : c.type === 'date' ? (
                          isEditable ? (
                            <DatePicker
                              size="small"
                              style={{ width: '100%' }}
                              format={DATE_FORMAT}
                              value={val ? dayjs(val as string) : null}
                              onChange={(d) => onCellChange(idx, c.key, d ? d.format('YYYY-MM-DD') : '')}
                            />
                          ) : (
                            dayjs(val as string).format('DD-MMM-YYYY')
                          )
                        )
                      : c.type === 'number' ? (
                          isEditable ? (
                            <InputNumber
                              size="small"
                              min={0}
                              style={{ width: '100%' }}
                              value={Number(val) || 0}
                              onChange={(v) => onCellChange(idx, c.key, v ?? 0)}
                              formatter={(value) => {
                                if (value === undefined || value === null || value === '') return '';
                                return Number(value).toLocaleString('id-ID');
                              }}
                              parser={(value) => {
                                if (!value) return undefined as unknown as number;
                                return parseFloat(value.replace(/\./g, '').replace(',', '.'));
                              }}
                            />
                          ) : (
                            fmt(Number(val) || 0)
                          )
                        )
                      : c.type === 'text' ? (
                          isEditable ? (
                            <Input
                              size="small"
                              value={String(val ?? '')}
                              placeholder={`${notePrefix}${idx + 1}`}
                              onChange={(e) => onCellChange(idx, c.key, e.target.value)}
                            />
                          ) : (
                            String(val ?? '')
                          )
                        )
                      : String(val ?? '')}
                  </td>
                );
              })}
              {onRemoveRow && (
                <td style={{ padding: '4px 6px' }}>
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => onRemoveRow(idx)} />
                </td>
              )}
            </tr>
          ))}
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
  columnLabels,
  recordId,
  recordData,
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
  // Loading state tombol confirm — dicegah double-click selama onConfirm async berjalan
  const [confirming, setConfirming] = useState(false);
  const [extraInputValues, setExtraInputValues] = useState<Record<string, number | string>>(() => {
    const currentMode = config.modes.find((m) => m.value === selectedMode);
    const vals: Record<string, number | string> = {};
    currentMode?.inputs?.forEach((inp) => {
      if (inp.type === 'date' && inp.default === 'today') vals[inp.key] = dayjs().format('YYYY-MM-DD');
      else if (inp.default !== undefined) vals[inp.key] = inp.default;
      else if (inp.type === 'selection') vals[inp.key] = inp.options?.[0]?.value ?? '';
      else if (inp.type === 'date') vals[inp.key] = '';
      else if (inp.type === 'text') vals[inp.key] = '';
      else vals[inp.key] = 0;
    });
    return vals;
  });
  // Catatan per baris mode `split` (key: term_no) — direset tiap modal terbuka
  const [splitNotes, setSplitNotes] = useState<Record<number, string>>({});
  // Baris mode `editable_rows` (manual) — direset tiap modal terbuka
  const [manualRows, setManualRows] = useState<{ due_date: string; amount: number; note: string }[]>([]);

  const handleModeChange = (value: string) => {
    setSelectedMode(value);
    const newMode = config.modes.find((m) => m.value === value);
    const vals: Record<string, number | string> = {};
    newMode?.inputs?.forEach((inp) => {
      if (inp.type === 'date' && inp.default === 'today') vals[inp.key] = dayjs().format('YYYY-MM-DD');
      else if (inp.default !== undefined) vals[inp.key] = inp.default;
      else if (inp.type === 'selection') vals[inp.key] = inp.options?.[0]?.value ?? '';
      else if (inp.type === 'date') vals[inp.key] = '';
      else if (inp.type === 'text') vals[inp.key] = '';
      else vals[inp.key] = 0;
    });
    setExtraInputValues(vals);
    setSplitNotes({});
    setManualRows([{ due_date: '', amount: 0, note: '' }]);
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
  // Konfigurasi mode split (pratinjau baris terbagi) — di-capture ke const
  // lokal agar narrowing TypeScript tetap berlaku di dalam closure JSX
  const splitCfg = currentMode?.split;
  const manualCfg = currentMode?.editable_rows;

  // Reset catatan split & baris manual tiap modal dibuka
  useEffect(() => {
    if (visible) {
      setSplitNotes({});
      setManualRows([{ due_date: '', amount: 0, note: '' }]);
    }
  }, [visible]);

  // Baris pratinjau mode `split`: bagi source_field → count baris, tanggal
  // bertahap dari date_input. Nominal hanya preview — backend menghitung ulang
  // saat confirm (authoritative).
  const splitRows = useMemo(() => {
    if (!splitCfg) return [];
    const sourceVal = Number((recordData ?? {})[splitCfg.source_field] ?? 0);
    if (sourceVal <= 0) return [];
    const count = Number(extraInputValues[splitCfg.count_input] ?? 0);
    const dateStr = extraInputValues[splitCfg.date_input] as string | undefined;
    if (!count || count < 1 || !dateStr) return [];
    const base = Math.floor(sourceVal / count);
    const step = splitCfg.date_step || 'month';
    const rows: { term_no: number; due_date: dayjs.Dayjs; amount: number }[] = [];
    for (let i = 0; i < count; i++) {
      rows.push({
        term_no: i + 1,
        due_date: dayjs(dateStr).add(i, step),
        amount: i === count - 1 ? sourceVal - base * (count - 1) : base,
      });
    }
    return rows;
  }, [splitCfg, recordData, extraInputValues]);

  // ── Handler baris mode editable_rows (manual) ──
  const handleManualRowChange = (idx: number, key: string, value: unknown) => {
    setManualRows((prev) => prev.map((r, i) => (i === idx ? { ...r, [key]: value } : r)));
  };
  const handleAddManualRow = () => {
    setManualRows((prev) => [...prev, { due_date: '', amount: 0, note: '' }]);
  };
  const handleRemoveManualRow = (idx: number) => {
    setManualRows((prev) => prev.filter((_, i) => i !== idx));
  };

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

  const handleFetchMany2One = async (inp: WizardInput & { relation?: string }) => {
    const relation = inp.relation || '';
    if (!relation) return;
    const cacheKey = relation + '::' + JSON.stringify(inp.filter || {});
    if (many2oneOptions[cacheKey]) return; // already loaded
    try {
      const token = localStorage.getItem('access_token');
      // Query params tambahan (filter) — {record_id} diganti id record aktif
      const filterParams = Object.entries(inp.filter || {})
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v.replace('{record_id}', String(recordId ?? '')))}`)
        .join('&');
      const query = filterParams ? `&${filterParams}` : '';
      const resp = await fetch(`/api/models/${relation}/records/?limit=200${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) throw new Error('Fetch failed');
      const data = await resp.json();
      const opts = (data.results || []).map((r: Record<string, unknown>) => {
        // value: field tertentu (default id) — support {id} / {value} object
        const rawVal = inp.value_field ? r[inp.value_field] : r.id;
        const value = rawVal && typeof rawVal === 'object'
          ? Number((rawVal as { id?: unknown }).id ?? rawVal)
          : Number(rawVal);
        // label: field tertentu (default display_name)
        const rawLabel = inp.label_field ? r[inp.label_field] : (r as { display_name?: string }).display_name;
        const label = rawLabel && typeof rawLabel === 'object'
          ? String((rawLabel as { name?: unknown }).name ?? rawLabel)
          : String(rawLabel ?? `#${r.id}`);
        return { value, label };
      });
      setMany2oneOptions((prev) => ({ ...prev, [cacheKey]: opts }));
    } catch {
      // silently fail
    }
  };

  const handleConfirm = async (mode?: string) => {
    const m = mode || selectedMode;
    const modeCfg = config.modes.find((x) => x.value === m);
    if (modeCfg?.table) return; // mode tampilan tabel — read-only, tidak ada aksi
    // Validasi mode split: jumlah termin & tanggal pertama wajib valid
    if (modeCfg?.split) {
      const count = Number(extraInputValues[modeCfg.split.count_input] ?? 0);
      if (!count || count < 1) {
        message.warning('Isi jumlah termin (minimal 1).');
        return;
      }
      const dateStr = extraInputValues[modeCfg.split.date_input] as string | undefined;
      if (!dateStr) {
        message.warning('Pilih tanggal pertama.');
        return;
      }
      const sourceVal = Number((recordData ?? {})[modeCfg.split.source_field] ?? 0);
      if (sourceVal <= 0) {
        message.warning('Nilai sumber 0 — tidak bisa dibagi.');
        return;
      }
    }
    // Validasi mode editable_rows (manual): minimal 1 baris lengkap &
    // total harus sama dengan nilai sumber (sisa tagihan wajib 0)
    if (modeCfg?.editable_rows) {
      const sourceVal = Number((recordData ?? {})[modeCfg.editable_rows.source_field] ?? 0);
      const filled = manualRows.filter((r) => r.due_date && Number(r.amount) > 0);
      if (filled.length === 0) {
        message.warning('Tambah minimal 1 baris cicilan (tanggal & nominal wajib).');
        return;
      }
      const total = filled.reduce((s, r) => s + Number(r.amount), 0);
      if (Math.abs(total - sourceVal) > 0.01) {
        const currency = modeCfg.editable_rows.currency || '';
        const fmt = (v: number) => `${currency}${Number(v || 0).toLocaleString('id-ID')}`;
        message.warning(`Total cicilan harus sama dengan sisa tagihan (${fmt(sourceVal)}) — sisa tagihan wajib 0.`);
        return;
      }
    }
    const selectedLines = selectedIds.map((id) => ({
      id,
      qty: qtys[id] ?? 0,
      ...(editableValues[id] || {}),
    }));
    const payload: Record<string, unknown> = { ...extraInputValues };
    if (modeCfg?.split) {
      // Catatan per baris dikirim sebagai array (index 0 = termin 1)
      payload.notes = splitRows.map((r) => (
        splitNotes[r.term_no] || `${modeCfg.split?.note_prefix || 'Term ke-'}${r.term_no}`
      ));
    }
    if (modeCfg?.editable_rows) {
      // Baris manual dikirim apa adanya; backend memvalidasi ulang
      payload.rows = manualRows
        .filter((r) => r.due_date && Number(r.amount) > 0)
        .map((r, i) => ({
          due_date: r.due_date,
          amount: Number(r.amount),
          note: r.note || `${modeCfg.editable_rows?.note_prefix || 'Term ke-'}${i + 1}`,
        }));
    }
    setConfirming(true);
    try {
      await onConfirm(m, selectedLines, payload);
    } finally {
      setConfirming(false);
    }
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
          <Button onClick={() => loadTable(selectedMode)} loading={tableData.loading} disabled={tableData.loading}>Refresh</Button>
          <Button onClick={onCancel}>Cancel</Button>
        </Space>
      );
    }
    if (allModesShowTable) {
      return (
        <Space>
          {config.modes.map((mode) => (
            <Button key={mode.value} type="primary" loading={confirming} disabled={confirming} onClick={() => handleConfirm(mode.value)}>
              {mode.label}
            </Button>
          ))}
          <Button onClick={onCancel} disabled={confirming}>Cancel</Button>
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
      okText={allModesShowTable ? undefined : (currentMode?.split || currentMode?.editable_rows ? "Konfirmasi" : "Confirm")}
      cancelText="Cancel"
      width={currentMode?.split || currentMode?.editable_rows ? 760 : 640}
      destroyOnClose
      confirmLoading={confirming}
      cancelButtonProps={{ disabled: confirming }}
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
                        onChange={(v) => handleExtraInputChange(inp.key, v ?? null)}
                        many2oneOptions={many2oneOptions}
                        onFetch={handleFetchMany2One}
                      />
                    ) : inp.type === 'date' ? (
                      <DatePicker
                        style={{ width: '100%' }}
                        format={DATE_FORMAT}
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
                          value={(extraInputValues[inp.key] as number | undefined) ?? (typeof inp.default === 'number' ? inp.default : 0)}
                          onChange={(val) => handleExtraInputChange(inp.key, val)}
                          style={{ width: '100%' }}
                          formatter={(value) => {
                            if (value === undefined || value === null || value === '') return '';
                            return Number(value).toLocaleString('id-ID');
                          }}
                          parser={(value) => {
                            if (!value) return undefined as unknown as number;
                            return parseFloat(value.replace(/\./g, '').replace(',', '.'));
                          }}
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
              columnLabels={columnLabels}
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

        {splitCfg && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              Pratinjau
            </Text>
            {(() => {
              const sourceVal = Number((recordData ?? {})[splitCfg.source_field] ?? 0);
              const currency = splitCfg.currency || '';
              const fmt = (v: number) => `${currency}${Number(v || 0).toLocaleString('id-ID')}`;
              const total = splitRows.reduce((s, r) => s + r.amount, 0);
              const sisa = sourceVal - total;
              const prefix = splitCfg.note_prefix || 'Term ke-';
              const rows = splitRows.map((r) => ({
                term_no: r.term_no,
                due_date: r.due_date.format('YYYY-MM-DD'),
                amount: r.amount,
                note: splitNotes[r.term_no] || `${prefix}${r.term_no}`,
              }));
              return (
                <Space direction="vertical" size={10} style={{ width: '100%' }}>
                  <div>
                    <Text strong>{splitCfg.source_label || 'Nilai Sumber'}: </Text>
                    <Text strong style={{ color: '#1677ff' }}>{fmt(sourceVal)}</Text>
                  </div>
                  {sourceVal <= 0 && (
                    <Alert type="warning" showIcon message="Nilai sumber 0 — tidak bisa dibagi." />
                  )}
                  {splitRows.length === 0 ? (
                    <div style={{ padding: 12, textAlign: 'center', color: '#999', border: '1px dashed #d9d9d9', borderRadius: 6 }}>
                      Isi jumlah termin & tanggal pertama untuk melihat pratinjau
                    </div>
                  ) : (
                    <WizardEditableTable
                      columns={splitCfg.columns || []}
                      rows={rows}
                      currency={currency}
                      status={splitCfg.status}
                      notePrefix={prefix}
                      onCellChange={(idx, key, value) => {
                        if (key === 'note') {
                          const termNo = splitRows[idx]?.term_no;
                          if (termNo != null) setSplitNotes((prev) => ({ ...prev, [termNo]: String(value) }));
                        }
                      }}
                    />
                  )}
                  {splitRows.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text type="secondary">Total ({splitRows.length} baris)</Text>
                      <Text strong>{fmt(total)}</Text>
                    </div>
                  )}
                  {splitRows.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text strong>Sisa Tagihan setelah cicilan</Text>
                      <Text strong style={{ color: sisa <= 0 ? '#52c41a' : '#ff4d4f' }}>
                        {fmt(sisa)}
                      </Text>
                    </div>
                  )}
                </Space>
              );
            })()}
          </div>
        )}

        {manualCfg && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              {manualCfg.title || 'Baris'}
            </Text>
            {(() => {
              const sourceVal = Number((recordData ?? {})[manualCfg.source_field] ?? 0);
              const currency = manualCfg.currency || '';
              const fmt = (v: number) => `${currency}${Number(v || 0).toLocaleString('id-ID')}`;
              const total = manualRows.reduce((s, r) => s + (Number(r.amount) || 0), 0);
              const sisa = sourceVal - total;
              const prefix = manualCfg.note_prefix || 'Term ke-';
              return (
                <Space direction="vertical" size={10} style={{ width: '100%' }}>
                  <div>
                    <Text strong>{manualCfg.source_label || 'Sisa Tagihan'}: </Text>
                    <Text strong style={{ color: '#1677ff' }}>{fmt(sourceVal)}</Text>
                  </div>
                  {sourceVal <= 0 && (
                    <Alert type="warning" showIcon message="Nilai sumber 0 — tidak bisa membuat cicilan." />
                  )}
                  <WizardEditableTable
                    columns={manualCfg.columns || []}
                    rows={manualRows}
                    currency={currency}
                    status={manualCfg.status}
                    notePrefix={prefix}
                    onCellChange={handleManualRowChange}
                    onRemoveRow={handleRemoveManualRow}
                  />
                  <Button size="small" icon={<PlusOutlined />} onClick={handleAddManualRow}>Tambah Baris</Button>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">Total ({manualRows.length} baris)</Text>
                    <Text strong>{fmt(total)}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Sisa Tagihan setelah cicilan</Text>
                    <Text strong style={{ color: sisa <= 0 ? '#52c41a' : '#ff4d4f' }}>{fmt(sisa)}</Text>
                  </div>
                </Space>
              );
            })()}
          </div>
        )}
      </Space>
    </Modal>
  );
}
