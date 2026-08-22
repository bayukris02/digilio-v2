import { useEffect, useState, useMemo, useCallback, useRef, forwardRef, useImperativeHandle, type ReactNode } from 'react';
import { useParams, useNavigate, useSearchParams, useLocation, useBlocker } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Typography, Card, Row, Col, Form, Input, Select, DatePicker, Switch,
  InputNumber, Button, Space, Spin, message, Breadcrumb, Steps, Tabs,
  Tag, Modal, List, Radio, Dropdown,
} from 'antd';
import {
  SaveOutlined, CloseOutlined, ArrowLeftOutlined, ArrowRightOutlined,
  PlusOutlined, DeleteOutlined, FileTextOutlined, MailOutlined,
  MoreOutlined, InboxOutlined, CheckOutlined, PrinterOutlined,
  DownloadOutlined, SendOutlined, EditOutlined, CopyOutlined,
  StopOutlined, UndoOutlined, LinkOutlined, HolderOutlined,
} from '@ant-design/icons';
import { modelApi, type ModelConfig } from '../../api/models';
import { DATE_FORMAT, parseDate, formatDate, formatLastUpdate } from '../../utils/format';
import { modelNameToApi, apiToUrlName } from '../../config/urlModelMap';
import Chatter from '../../components/Chatter';
import SummaryCard from '../../components/SummaryCard';
import QuickViewModal from '../../components/QuickViewModal';
import GenericWizardModal from '../../components/GenericWizardModal';
import ProgressBar from '../../components/ProgressBar';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, ICellRendererParams, CellValueChangedEvent } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry, themeBalham } from 'ag-grid-community';
import { RichSelectModule } from 'ag-grid-enterprise';

ModuleRegistry.registerModules([AllCommunityModule, RichSelectModule]);

const { TextArea } = Input;
const { Title } = Typography;

// Many2one dropdown pagination: fetch bertahap 25 per halaman
const M2O_PAGE_SIZE = 25;

// ─── Smart Button Component ────────────────
interface SmartBtnProps {
  icon: React.ReactNode;
  count: number | string;
  label: string;
  color: string;
  onClick?: () => void;
}

function SmartButton({ icon, count, label, color, onClick }: SmartBtnProps) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        background: hovered ? color : '#fff',
        border: `1px solid ${color}`,
        borderRadius: 5,
        padding: '3px 8px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
        minWidth: 78,
        userSelect: 'none',
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 4,
          background: hovered ? 'rgba(255,255,255,0.2)' : color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: hovered ? '#fff' : '#fff',
          fontSize: 14,
          flexShrink: 0,
          transition: 'background 0.15s',
        }}
      >
        {icon}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: hovered ? '#fff' : '#222',
            transition: 'color 0.15s',
          }}
        >
          {count}
        </span>
        <span
          style={{
            fontSize: 9,
            color: hovered ? 'rgba(255,255,255,0.85)' : '#888',
            transition: 'color 0.15s',
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
}

/** Select component for Many2One fields — fetches options from related model */
function Many2OneSelect({ value, onChange, modelName, placeholder, currentModel, onQuickView, disabled }: {
  value?: number; onChange?: (v: number | undefined) => void; modelName: string; placeholder?: string; currentModel?: string; onQuickView?: (id: number) => void; disabled?: boolean;
}) {
  const [options, setOptions] = useState<{ value: number; label: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchOptions = useCallback(() => {
    if (!modelName) return;
    setLoading(true);
    const params = currentModel ? { model_ref: currentModel } : undefined;
    modelApi.listRecords(modelName, undefined, undefined, params)
      .then((response) => {
        const records = response.results;
        const opts = records.map((r) => ({
          value: r.id as number,
          label: (r.display_name as string) || `#${r.id}`,
        }));
        setOptions(opts);
      })
      .catch(() => {
        message.error(`Failed to load ${modelName}`);
      })
      .finally(() => setLoading(false));
  }, [modelName, currentModel]);

  useEffect(() => { fetchOptions(); }, [fetchOptions]);

  return (
    <Space.Compact style={{ width: '100%' }}>
      <Select
        style={{ flex: 1 }}
        value={value}
        onChange={onChange}
        showSearch
        placeholder={placeholder || 'Select...'}
        loading={loading}
        options={options}
        filterOption={(input, option) =>
          (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
        }
        allowClear
        disabled={disabled}
        onDropdownVisibleChange={(open) => { if (open) fetchOptions(); }}
      />
      {value != null && onQuickView && (
        <Button
          size="small"
          type="default"
          icon={<LinkOutlined style={{ fontSize: 12 }} />}
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
            onQuickView(value);
          }}
          title="View details"
        />
      )}
    </Space.Compact>
  );
}

/** Many2OneSelect with autofill — fetches related record and sets form fields on change */
function Many2OneWithAutofill({ value, onChange, field, apiModelName, onQuickView, disabled }: {
  value?: number; onChange?: (v: number | undefined) => void;
  field: ModelConfig['fields'][string] & { autofill?: Record<string, string>; relation?: string };
  apiModelName?: string;
  onQuickView?: (id: number) => void;
  disabled?: boolean;
}) {
  const form = Form.useFormInstance();
  const handleChange = (newVal: number | undefined) => {
    if (newVal && field.autofill && field.relation) {
      modelApi.getRecord(field.relation, newVal).then((record) => {
        const rec = record as Record<string, unknown>;
        Object.entries(field.autofill!).forEach(([targetField, sourceField]) => {
          const val = rec[sourceField as string];
          if (val !== undefined) {
            form.setFieldValue(targetField, typeof val === 'object' && val !== null ? (val as Record<string, unknown>).id ?? val : val);
          }
        });
      }).catch(() => {
        message.error(`Failed to load ${field.relation} for autofill`);
      });
    } else if (field.autofill) {
      // Clear autofill fields when selection is cleared
      Object.keys(field.autofill).forEach((targetField) => {
        form.setFieldValue(targetField, undefined);
      });
    }
    onChange?.(newVal);
  };
  return (
    <Many2OneSelect
      value={value}
      onChange={handleChange}
      modelName={field.relation || ''}
      placeholder={field.placeholder || `Select ${field.label}`}
      currentModel={apiModelName}
      onQuickView={onQuickView}
      disabled={disabled}
    />
  );
}

/** Render field based on config type */
function renderField(
  key: string,
  field: ModelConfig['fields'][string],
  initialValues: Record<string, unknown>,
  currentModel?: string,
  onQuickView?: (modelName: string, recordId: number) => void,
  disabled?: boolean,
) {
  const label = field.label;
  const required = field.required;

  if (field.type === 'boolean') {
    return (
      <Form.Item label={label} name={key} valuePropName="checked">
        <Switch disabled={disabled} />
      </Form.Item>
    );
  }

  // Virtual field → read-only display (frontend-only, no DB column)
  if (field.virtual) {
    return (
      <Form.Item label={label} name={key}>
        <Input placeholder="-" variant="borderless" readOnly style={{ color: '#666', cursor: 'default' }} />
      </Form.Item>
    );
  }

  if (field.type === 'selection') {
    // Discount method → radio button instead of dropdown
    if (key === 'discount_method') {
      return (
        <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            disabled={disabled}
            options={field.options}
          />
        </Form.Item>
      );
    }
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        <Select
          placeholder={field.placeholder || `Select ${label}`}
          allowClear
          options={field.options}
          disabled={disabled}
        />
      </Form.Item>
    );
  }

  if (field.type === 'date') {
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true, message: `${label} wajib diisi` }] : []}>
        <DatePicker format={DATE_FORMAT} style={{ width: '100%' }} disabled={disabled} />
      </Form.Item>
    );
  }

  if (field.type === 'monetary' || field.type === 'float') {
    const max = (field as any).max;
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        <InputNumber
          style={{ width: '100%' }}
          min={0}
          {...(max != null ? { max } : {})}
          placeholder="0"
          disabled={disabled}
          formatter={(value) => {
            if (value === undefined || value === null || value === '') return '';
            return Number(value).toLocaleString('id-ID');
          }}
          parser={(value) => {
            if (!value) return undefined as unknown as number;
            return parseFloat(value.replace(/\./g, '').replace(',', '.'));
          }}
          addonAfter={field.currency || ''}
        />
      </Form.Item>
    );
  }

  if (field.type === 'integer') {
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        <InputNumber style={{ width: '100%' }} placeholder="0" disabled={disabled} />
      </Form.Item>
    );
  }

  if (field.type === 'percentage') {
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        <InputNumber
          style={{ width: '100%' }}
          min={0}
          max={100}
          placeholder="0"
          disabled={disabled}
          formatter={(value) => `${value}%`}
          parser={(value) => value?.replace('%', '') || undefined as unknown as number}
        />
      </Form.Item>
    );
  }

  if (field.type === 'text') {
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        <TextArea rows={3} placeholder={field.placeholder || `Enter ${label}`} disabled={disabled} />
      </Form.Item>
    );
  }

  // Many2One → Select with records from related model
  if (field.type === 'many2one') {
    const many2oneField = field as ModelConfig['fields'][string] & { autofill?: Record<string, string>; relation?: string };
    const hasAutofill = many2oneField.autofill && Object.keys(many2oneField.autofill).length > 0;
    return (
      <Form.Item label={label} name={key} rules={required ? [{ required: true }] : []}>
        {hasAutofill ? (
          <Many2OneWithAutofill
            field={many2oneField}
            apiModelName={currentModel}
            onQuickView={onQuickView ? (id) => onQuickView(many2oneField.relation!, id) : undefined}
            disabled={disabled}
          />
        ) : (
          <Many2OneSelect
            modelName={(field as Record<string, string>).relation || ''}
            placeholder={field.placeholder || `Select ${label}`}
            required={required}
            currentModel={currentModel}
            onQuickView={onQuickView ? (id) => onQuickView((field as Record<string, string>).relation!, id) : undefined}
            disabled={disabled}
          />
        )}
      </Form.Item>
    );
  }

  // Char (default)
  const charRules: Record<string, unknown>[] = required ? [{ required: true }] : [];
  if (field.min_length) {
    charRules.push({ min: field.min_length, message: `Min ${field.min_length} characters` });
  }
  return (
    <Form.Item label={label} name={key} rules={charRules}>
      <Input placeholder={field.placeholder || `Enter ${label}`} disabled={disabled} />
    </Form.Item>
  );
}

// ─── Many2One Cell Editor (AG Grid) ────────────────
// Dropdown pakai Ant Design Select: search bar selalu tampil,
// maksimal 5 opsi + footer hint untuk mencari data lain.
interface Many2OneEditorProps {
  value?: Record<string, unknown> | null;
  values?: Array<{ value: number; label?: string; name?: string }>;
  stopEditing?: () => void;
  // AG Grid React v35: nilai editor disinkronkan ke grid VIA prop ini
  // (proxy punya getValue() sendiri yang baca this.value — useImperativeHandle
  // TIDAK dipakai untuk commit)
  onValueChange?: (value: Record<string, unknown> | null) => void;
  // Infinite scroll: total record dari server + pemuat halaman berikutnya
  total?: number;
  onLoadMore?: () => Promise<Record<string, unknown>[]>;
}

const Many2OneCellEditor = forwardRef<{ getValue: () => Record<string, unknown> | null }, Many2OneEditorProps>(
  ({ value, values, stopEditing, onValueChange, total, onLoadMore }, ref) => {
    const allValues = values || [];
    const currentId = value && (value.value ?? value.id);
    const currentLabel = value && (value.label ?? value.name);
    // Simpan SELURUH object option (bukan cuma {value,label}) — autofill di
    // onCellValueChanged membaca field lain (mis. name → description) dari
    // object ini. Cari option penuh dari values kalau ada, fallback id/label.
    const currentOption = allValues.find((o) => o.value === Number(currentId));
    const [selected, setSelected] = useState<Record<string, unknown> | null>(
      currentOption ?? (currentId != null
        ? { value: Number(currentId), label: String(currentLabel ?? '') }
        : null),
    );
    // List lokal editor — AG Grid tidak re-render editor aktif saat props
    // berubah, jadi hasil onLoadMore di-append ke sini (bukan andalkan values)
    const [items, setItems] = useState<Record<string, unknown>[]>(allValues);
    // getValue baca dari ref — state React async, tidak bisa dibaca
    // langsung setelah setSelected (bug: klik tidak kepilih)
    const selectedRef = useRef(selected);
    const [search, setSearch] = useState('');
    const [open, setOpen] = useState(true);
    const selectRef = useRef<any>(null);
    const loadingRef = useRef(false);

    // AG Grid mencuri fokus setelah editor mount → search box tidak kebagian
    // ketikan. Fokuskan input Select secara eksplisit.
    useEffect(() => {
      const t = setTimeout(() => selectRef.current?.focus(), 60);
      return () => clearTimeout(t);
    }, []);

    const loadMore = async () => {
      if (loadingRef.current || !onLoadMore) return;
      loadingRef.current = true;
      const newOpts = await onLoadMore();
      loadingRef.current = false;
      if (newOpts.length) {
        setItems((prev) => {
          const seen = new Set(prev.map((o) => o.value));
          return [...prev, ...newOpts.filter((o) => !seen.has(o.value))];
        });
      }
    };

    const commit = (next: Record<string, unknown>) => {
      selectedRef.current = next;
      setSelected(next);
      // Sinkronkan nilai ke grid VIA onValueChange — ini satu-satunya cara
      // proxy AG Grid React v35 membaca nilai editor (getValue proxy = this.value)
      onValueChange?.(next);
      stopEditing?.();
    };

    useImperativeHandle(ref, () => ({
      getValue: () => selectedRef.current,
    }));

    const filtered = useMemo(() => {
      const q = search.trim().toLowerCase();
      if (!q) return items;
      return items.filter((o) =>
        String(o.label ?? o.name ?? '').toLowerCase().includes(q),
      );
    }, [items, search]);

    // Semua item yang sudah di-load ditampilkan; tinggi dropdown dibatasi
    // listHeight (≈5 baris) supaya bisa scroll, bukan slice 5.
    const visible = filtered;
    const hasMore = items.length < (total ?? items.length);
    // Pilihan saat ini WAJIB ada di daftar options — kalau tidak, Ant Select
    // tidak menemukan label-nya dan menampilkan ID mentah (placeholder ID)
    const options = selected && !visible.some((o) => o.value === Number(selected.value))
      ? [selected, ...visible]
      : visible;

    return (
      <Select
        ref={selectRef}
        autoFocus
        showSearch
        filterOption={false}
        open={open}
        onDropdownVisibleChange={(o) => setOpen(o)}
        style={{ width: '100%' }}
        popupMatchSelectWidth={false}
        dropdownStyle={{ minWidth: 300 }}
        listHeight={160}
        placeholder="Ketik untuk mencari..."
        value={selected ? Number(selected.value) : undefined}
        options={options.map((o) => ({ ...o, value: Number(o.value), label: String(o.label ?? o.name ?? '') }))}
        onSearch={(v) => setSearch(v)}
        onPopupScroll={(e) => {
          const el = e.target as HTMLElement;
          // Mentok di bawah → load halaman berikutnya
          if (el.scrollTop + el.clientHeight >= el.scrollHeight - 20) loadMore();
        }}
        onChange={(val, opt) => {
          const o = (Array.isArray(opt) ? opt[0] : opt) as Record<string, unknown> | undefined;
          if (o) commit({ ...o, value: Number(val) });
        }}
        notFoundContent={search ? 'Data tidak ditemukan' : 'Ketik untuk mencari data lain...'}
        dropdownRender={(menu) => (
          <div
            // Klik option di portal dropdown jangan sampai melepas fokus dari
            // input — kalau blur, AG Grid (stopEditingWhenCellsLoseFocus) stop
            // editing duluan dengan nilai lama → pilihan tidak masuk cell.
            onMouseDown={(e) => e.preventDefault()}
          >
            {menu}
            {hasMore && (
              <div style={{ padding: '6px 12px', color: '#999', fontSize: 12, borderTop: '1px solid #f0f0f0', textAlign: 'center' }}>
                Ketik untuk mencari data lain...
              </div>
            )}
          </div>
        )}
      />
    );
  },
);
Many2OneCellEditor.displayName = 'Many2OneCellEditor';

export default function ModelFormPage({
  modelName: propModelName,
  basePath: propBasePath,
  readOnly = false,
}: { modelName?: string; basePath?: string; readOnly?: boolean } = {}) {
  const { modelName: urlModelName, recordId } = useParams<{ modelName: string; recordId?: string }>();
  // modelName bisa di-override via prop (menu alias seperti Project Update);
  // fallback ke param URL = perilaku default tidak berubah
  const modelName = propModelName ?? urlModelName ?? '';
  // basePath: URL navigasi self (list/new/detail); default = /modelName (perilaku lama)
  const basePath = propBasePath ?? `/${modelName}`;
  const apiModelName = modelName ? modelNameToApi(modelName) : '';
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const fromModel = searchParams.get('from');
  const fromId = searchParams.get('fromId');

  const [form] = Form.useForm();

  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [addingLine, setAddingLine] = useState(false);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [recordData, setRecordData] = useState<Record<string, unknown> | null>(null);
  const [lineItems, setLineItems] = useState<Record<string, Record<string, unknown>[]>>({});
  // Revision counter untuk memaksa SummaryCard recompute setelah child compute
  const [summaryRevision, setSummaryRevision] = useState(0);
  const [childConfigs, setChildConfigs] = useState<Record<string, ModelConfig>>({});
  const [many2oneOptions, setMany2oneOptions] = useState<Record<string, { value: number; label: string; uom?: string }[]>>({});
  // Pagination state per many2one option list: page terakhir, total, loading
  const [many2oneMeta, setMany2oneMeta] = useState<Record<string, { page: number; total: number; loading: boolean; params: Record<string, string> }>>({});
  const [chatterKey, setChatterKey] = useState(0);
  const [recordIds, setRecordIds] = useState<number[]>([]);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [printPreviewHtml, setPrintPreviewHtml] = useState<string | null>(null);
  const [printPdfUrl, setPrintPdfUrl] = useState<string | null>(null);
  const [quickView, setQuickView] = useState<{ modelName: string; recordId: number } | null>(null);
  const [wizardVisible, setWizardVisible] = useState(false);
  const [wizardData, setWizardData] = useState<{ model: string; records: { id: number; display_name: string; status?: string }[] } | null>(null);
  const [parentRecord, setParentRecord] = useState<{ id: number; display_name: string; verbose_name: string } | null>(null);
  // ── Action wizard (modal with mode + line selection) ──
  const [actionWizardVisible, setActionWizardVisible] = useState(false);
  const [actionWizardBtn, setActionWizardBtn] = useState<Record<string, unknown> | null>(null);
  // ── Notebook tab navigation (action button `goto_tab`) ──
  const [activeNotebookKey, setActiveNotebookKey] = useState<string>();
  const notebookRef = useRef<HTMLDivElement>(null);
  const wizardItems = useMemo(() => {
    if (!actionWizardBtn) return [];
    const ls = (actionWizardBtn.wizard as any)?.line_selection;
    const rel = ls?.relation;
    return rel ? ((recordData as any)?.[rel] as any[]) || [] : [];
  }, [actionWizardBtn, recordData]);
  // Label kolom line_selection (key → label) dari config child model — dipakai
  // LineSelector sebagai header kolom (fallback: key mentah).
  const wizardColumnLabels = useMemo(() => {
    if (!actionWizardBtn) return undefined;
    const ls = (actionWizardBtn.wizard as any)?.line_selection;
    const rel = ls?.relation;
    const cols: string[] = ls?.columns || [];
    const childCfg = rel ? childConfigs[rel] : undefined;
    if (!childCfg?.fields) return undefined;
    const labels: Record<string, string> = {};
    cols.forEach((col) => {
      const f = childCfg.fields?.[col];
      if (f?.label) labels[col] = f.label;
    });
    return labels;
  }, [actionWizardBtn, childConfigs]);
  const printFrameRef = useRef<HTMLIFrameElement>(null);
  const isNew = recordId === 'new' || !recordId;
  // Force form remount on data load — ensures initialValues applied correctly
  const [loadKey, setLoadKey] = useState(0);

  // ── confirm_onchange: track previous field values + revert state ──
  const prevFieldValuesRef = useRef<Record<string, unknown>>({});
  const isRevertingRef = useRef(false);

  // ── Save status tracking ──
  const lastSnapshotRef = useRef<string>('');         // JSON form values saat terakhir save
  const [dirtyFlag, setDirtyFlag] = useState(false);

  // Helper: sync snapshot dari current form values
  const syncSaveSnapshot = useCallback(() => {
    const vals = form.getFieldsValue();
    lastSnapshotRef.current = JSON.stringify(vals);
    setDirtyFlag(false);
  }, [form]);

  /** Callback untuk Form.onValuesChange — deteksi dirty + field onchange */
  const handleFormChange = useCallback((changedValues?: Record<string, unknown>) => {
    if (lastSnapshotRef.current) {
      const current = JSON.stringify(form.getFieldsValue());
      setDirtyFlag(current !== lastSnapshotRef.current);
    }

    // onchange: reset target fields saat source field berubah
    // definisinya di model: SelectionField(..., onchange={'target_field': defaultValue})
    if (config && changedValues) {
      const updates: Record<string, unknown> = {};
      Object.entries(changedValues).forEach(([fieldName]) => {
        const fieldCfg = config.fields?.[fieldName];
        if (fieldCfg?.onchange) {
          Object.entries(fieldCfg.onchange as Record<string, unknown>).forEach(([target, value]) => {
            updates[target] = value;
          });
        }
      });
      if (Object.keys(updates).length > 0) {
        form.setFieldsValue(updates);
      }

      // line_onchange: reset line-level fields saat source field berubah
      // definisinya di model: SelectionField(..., line_onchange={'discount_amount': 0})
      Object.entries(changedValues).forEach(([fieldName]) => {
        const fieldCfg = config.fields?.[fieldName];
        if (fieldCfg?.line_onchange) {
          const lineUpdates = fieldCfg.line_onchange as Record<string, unknown>;
          setLineItems((prev) => {
            const updated: Record<string, Record<string, unknown>[]> = {};
            for (const [rel, items] of Object.entries(prev)) {
              updated[rel] = items.map((item) => ({
                ...item,
                ...lineUpdates,
              }));
            }
            return updated;
          });
        }
      });

      // confirm_onchange: jika field berubah dan ada line items → konfirmasi dulu
      // definisinya di model: Many2OneField(..., confirm_onchange={message, reset_relations})
      Object.entries(changedValues).forEach(([fieldName, newValue]) => {
        const fieldCfg = config.fields?.[fieldName];
        const confirmCfg = fieldCfg?.confirm_onchange as Record<string, unknown> | undefined;
        if (!confirmCfg || isRevertingRef.current) return;
        const oldValue = prevFieldValuesRef.current[fieldName];
        if (oldValue === newValue || oldValue === undefined) return;
        const resetRels = (confirmCfg.reset_relations as string[]) || [];
        const hasLines = resetRels.some((rel: string) => {
          const items = lineItems[rel] || [];
          return items.filter((item) => !item._isAddButton).length > 0;
        });
        if (!hasLines) return;
        Modal.confirm({
          title: 'Konfirmasi Perubahan',
          content: (confirmCfg.message as string) || 'Mengubah nilai ini akan mereset data baris. Lanjutkan?',
          onOk: () => {
            setLineItems((prev) => {
              const updated = { ...prev };
              resetRels.forEach((rel: string) => { updated[rel] = []; });
              return updated;
            });
            setSummaryRevision((v) => v + 1);
            prevFieldValuesRef.current = { ...prevFieldValuesRef.current, [fieldName]: newValue };
          },
          onCancel: () => {
            isRevertingRef.current = true;
            form.setFieldValue(fieldName, oldValue);
            isRevertingRef.current = false;
          },
        });
      });
    }
  }, [form, config, setLineItems, lineItems, setSummaryRevision]);

  // ── Block navigation when there are unsaved changes ──
  // useBlocker intercepts route changes (menu, breadcrumb, prev/next, discard)
  // so we can warn the user before data could be lost.
  // skipBlockerRef: bypass blocker utk navigasi SAH setelah save sukses
  // (setDirtyFlag(false) async, jadi blocker harus cek ref, bukan state).
  const skipBlockerRef = useRef(false);
  const location = useLocation();
  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }) =>
        !skipBlockerRef.current && dirtyFlag && currentLocation.pathname !== nextLocation.pathname,
      [dirtyFlag],
    ),
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      Modal.confirm({
        title: 'Perubahan Belum Disimpan',
        content: 'Ada perubahan yang belum disimpan. Yakin ingin meninggalkan halaman ini?',
        okText: 'Ya, Tinggalkan',
        cancelText: 'Tetap di Sini',
        onOk: () => blocker.proceed(),
        onCancel: () => blocker.reset(),
      });
    }
  }, [blocker]);

  // Reset bypass setelah navigasi selesai (pathname berubah)
  useEffect(() => {
    skipBlockerRef.current = false;
  }, [location.pathname]);

  // ── Fetch model config (once per model) ──
  useEffect(() => {
    if (!apiModelName) return;

    // Reset state from previous model (e.g. GR → PO via breadcrumb)
    setConfig(null);
    setRecordData(null);
    setLineItems({});
    setCurrentStep(0);
    setChildConfigs({});
    setMany2oneOptions({});
    setParentRecord(null);
    setChatterKey((c) => c + 1);
    setRecordIds([]);
    setCurrentIdx(-1);
    // Reset save status
    lastSnapshotRef.current = '';
    setDirtyFlag(false);

    setLoading(true);
    modelApi.getConfig(apiModelName)
      .then((cfg) => {
        setConfig(cfg);
      })
      .catch((err) => {
        message.error('Failed to load: ' + (err?.message || ''));
      });
  }, [apiModelName]);

  // ── Reset child line items when navigating to a different record within same model ──
  useEffect(() => {
    setLineItems({});
    setChildConfigs({});
    setMany2oneOptions({});
  }, [recordId]);

  // ── Init prevFieldValuesRef for confirm_onchange fields when config loads ──
  useEffect(() => {
    if (!config) return;
    const initial: Record<string, unknown> = {};
    Object.entries(config.fields || {}).forEach(([key, field]) => {
      if ((field as any).confirm_onchange) {
        initial[key] = form.getFieldValue(key);
      }
    });
    prevFieldValuesRef.current = initial;
  }, [config, form]);

  // ── Fetch record or set defaults ──
  useEffect(() => {
    if (!apiModelName || !config) return;

    if (!isNew && recordId) {
      let ignore = false;
      setLoading(true);
      modelApi.getRecord(apiModelName, Number(recordId))
        .then((record) => {
          if (ignore) return;
          // Normalize many2one value — keep dates as raw strings for initialValues
          Object.entries(config.fields).forEach(([key, field]) => {
            if (field.type === 'many2one' && record[key] && typeof record[key] === 'object') {
              record[key] = (record[key] as Record<string, unknown>)?.id ?? null;
            }
          });
          setRecordData(record);
          setLoadKey((prev) => prev + 1);
          // Explicitly set form fields — form instance from Form.useForm()
          // persists across key changes, so initialValues won't re-apply
          const formValues: Record<string, unknown> = {};
          Object.entries(config.fields).forEach(([key, field]) => {
            if (field.type === 'date' && record[key]) {
              formValues[key] = parseDate(record[key] as string);
            } else if (field.type === 'many2one' && typeof record[key] === 'object') {
              formValues[key] = (record[key] as Record<string, unknown>)?.id ?? null;
            } else {
              formValues[key] = record[key] ?? undefined;
            }
          });
          form.setFieldsValue(formValues);
          syncSaveSnapshot();
          if (record.status && config.fields.status?.options) {
            const idx = config.fields.status.options.findIndex(
              (o) => o.value === record.status,
            );
            if (idx >= 0) setCurrentStep(idx);
          }
          setLoading(false);
        })
        .catch((err) => {
          if (ignore) return;
          message.error('Failed to load: ' + (err?.message || ''));
          setLoading(false);
        });
      return () => { ignore = true; };
    } else {
      // Set default from field config
      const defaults: Record<string, unknown> = {};
      Object.entries(config.fields).forEach(([key, field]) => {
        if (field.default !== undefined && field.default !== null) {
          defaults[key] = field.default;
        }
        // Auto-fill Many2One ke User dengan current user
        if (field.type === 'many2one' && field.relation === 'settings.user' && defaults[key] === undefined) {
          if ((config as any)._current_user_id) {
            defaults[key] = (config as any)._current_user_id;
          }
        }
      });
      setRecordData(defaults);
      setLoadKey((prev) => prev + 1);
      syncSaveSnapshot();
      setLoading(false);
    }
  }, [apiModelName, config, recordId, isNew, form]);

  // ── After record loaded, populate autofill virtual fields from related records ──
  useEffect(() => {
    if (!config || !recordData || isNew) return;
    Object.entries(config.fields).forEach(([key, field]) => {
      if (field.type !== 'many2one') return;
      const m2o = field as ModelConfig['fields'][string] & { autofill?: Record<string, string>; relation?: string };
      if (!m2o.autofill || !m2o.relation) return;
      const relId = recordData[key];
      if (!relId) return;
      const relIdNum = typeof relId === 'object' && relId !== null
        ? (relId as Record<string, unknown>).id as number
        : Number(relId);
      if (!relIdNum) return;
      modelApi.getRecord(m2o.relation, relIdNum).then((relRecord) => {
        const rec = relRecord as Record<string, unknown>;
        const values: Record<string, unknown> = {};
        Object.entries(m2o.autofill!).forEach(([targetField, sourceField]) => {
          const val = rec[sourceField as string];
          if (val !== undefined) {
            values[targetField] = typeof val === 'object' && val !== null
              ? (val as Record<string, unknown>).id ?? val
              : val;
          }
        });
        form.setFieldsValue(values);
      }).catch(() => {
        // silent fail — autofill is best-effort
      });
    });
  }, [config, recordData, isNew, form]);

  // ── Fetch record IDs for ◀▶ navigation (once per model) ──
  useEffect(() => {
    if (!apiModelName || isNew) return;
    modelApi.listRecords(apiModelName, 1, 0).then((response) => {
      const ids = response.results.map((r) => Number(r.id));
      setRecordIds(ids);
      setCurrentIdx(ids.findIndex((id) => id === Number(recordId)));
    }).catch(() => {
      // silent fail — navigasi opsional
    });
  }, [apiModelName, isNew]);

  // ── Update currentIdx on ◀▶ navigation ──
  useEffect(() => {
    if (recordIds.length > 0 && recordId) {
      setCurrentIdx(recordIds.findIndex((id) => id === Number(recordId)));
    }
  }, [recordId, recordIds]);

  // ── Fetch child model configs for relation tabs + init line items + many2one options ──
  useEffect(() => {
    if (!config?.form_view?.notebook) return;
    const relationTabs = config.form_view.notebook.filter(
      (tab: { relation?: string }) => tab.relation,
    );
    for (const tab of relationTabs) {
      const fieldMeta = config.fields?.[tab.relation];
      if (fieldMeta?.type === 'one2many' && fieldMeta.relation) {
        // Fetch child config only once
        if (!childConfigs[tab.relation]) {
          modelApi.getConfig(fieldMeta.relation).then((cfg) => {
            setChildConfigs((prev) => ({ ...prev, [tab.relation]: cfg }));
            // Also pre-fetch many2one options for this child model
            const m2oFields = Object.entries(cfg.fields).filter(
              ([, f]) => f.type === 'many2one' && (f as Record<string, string>).relation,
            );
            for (const [fKey, fMeta] of m2oFields) {
              const relName = (fMeta as Record<string, string>).relation;
              if (!relName) continue;
              // Check if notebook column config has display_field for this field
              const tabColumn = Array.isArray(tab.columns)
                ? (tab.columns as any[]).find((c) => typeof c === 'object' && c.name === fKey)
                : undefined;
              const displayField = (tabColumn as any)?.display_field;
              // domain: filter pre-fetch options berdasarkan field header
              const domain = (fMeta as any)?.domain as Record<string, string> | undefined;
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
              modelApi.listRecords(relName, undefined, undefined, extraParams).then((response) => {
                const opts = response.results.map((r) => ({
                  ...r,  // spread all fields (price, description, uom, etc.) for autofill
                  value: r.id as number,
                  label: displayField
                    ? ((r[displayField] as string) || `#${r.id}`)
                    : ((r.name as string) || `#${r.id}`),
                }));
                setMany2oneOptions((prev) => ({
                  ...prev,
                  [`${tab.relation}.${fKey}`]: opts,
                }));
              }).catch(() => {});
            }
          }).catch(() => {});
        }
      }
      // Init line items if recordData has one2many data
      if (recordData?.[tab.relation] && !lineItems[tab.relation]) {
        const items = (recordData[tab.relation] as Record<string, unknown>[]).map(
          (item: Record<string, unknown>) => ({
            ...item,
            _key: `line_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          }),
        );
        setLineItems((prev) => ({ ...prev, [tab.relation]: items }));
      }
    }
  }, [config, recordData]);

  // ── Domain refetch: saat header field berubah, refetch many2one options ──
  const headerFieldForDomain = Form.useWatch('vendor', form);
  useEffect(() => {
    if (!config || !Object.keys(childConfigs).length) return;
    const tabs = config?.form_view?.notebook || [];
    tabs.forEach((tab: { relation?: string; columns?: any[] }) => {
      if (!tab.relation) return;
      const childCfg = childConfigs[tab.relation];
      if (!childCfg?.fields) return;
      Object.entries(childCfg.fields).forEach(([fKey, fMeta]: [string, any]) => {
        if (fMeta.type !== 'many2one' || !fMeta.relation || !fMeta.domain) return;
        const domain = fMeta.domain as Record<string, string>;
        const extraParams: Record<string, string> = {};
        Object.entries(domain).forEach(([relatedField, headerField]) => {
          const isFormField = config?.fields?.[headerField] != null;
          const headerVal = isFormField ? form.getFieldValue(headerField) : headerField;
          if (headerVal != null) {
            extraParams[relatedField] = String(headerVal);
          }
        });
        if (!Object.keys(extraParams).length) return;
        const tabColumn = Array.isArray(tab.columns)
          ? tab.columns.find((c: any) => typeof c === 'object' && c.name === fKey)
          : undefined;
        const displayField = (tabColumn as any)?.display_field;
        modelApi.listRecords(fMeta.relation, undefined, undefined, extraParams).then((response) => {
          const opts = response.results.map((r: any) => ({
            ...r,
            value: r.id as number,
            label: displayField
              ? ((r[displayField] as string) || `#${r.id}`)
              : ((r.name as string) || `#${r.id}`),
          }));
          setMany2oneOptions((prev) => ({
            ...prev,
            [`${tab.relation}.${fKey}`]: opts,
          }));
        }).catch(() => {});
      });
    });
  }, [headerFieldForDomain, config, childConfigs]);

  // ── Stepper steps from status field ──
  const stepperSteps = useMemo(() => {
    if (!config?.fields?.status?.options) return [];
    // Status eksplisit per step: hanya step AKTIF yang menyala (process),
    // step lain non-aktif (wait) — tidak ada centang finish, biar tidak ambigu
    // posisi dokumen sekarang (mis. draft lewat ≠ centang, tetap terlihat non-aktif).
    return config.fields.status.options.map((o, idx) => ({
      title: o.label,
      status: idx === currentStep ? ('process' as const) : ('wait' as const),
    }));
  }, [config, currentStep]);

  // ── Form fields (exclude virtual/technical) ──
  const formFields = useMemo(() => {
    if (!config) return [];
    return Object.entries(config.fields).filter(
      ([key, f]) =>
        f.type !== 'one2many' &&
        key !== 'created_at' &&
        key !== 'updated_at' &&
        key !== 'is_deleted',
    );
  }, [config]);

  // ── Field yang dirender di form (header tabs/fields) ──
  // Dipakai saat save: many2one yang TIDAK dirender (mis. purchase_request di PO)
  // tidak boleh di-null-kan — kalau dikirim null, relasi antar dokumen terputus.
  // null = header tidak didefinisikan → semua formFields dirender.
  const renderedFormKeys = useMemo(() => {
    if (!config?.form_view?.header) return null;
    const keys = config.form_view.header.tabs
      ? config.form_view.header.tabs.flatMap((tab: { fields?: string[] }) => tab.fields || [])
      : (config.form_view.header.fields || []);
    return new Set(keys);
  }, [config]);

  // ── Smart buttons from form_view config ──
  const smartButtons = useMemo(() => {
    if (!config?.form_view?.header?.smart_buttons) return [];
    return config.form_view.header.smart_buttons;
  }, [config]);

  // ── Display field for title: reference > name > code ──
  const displayField = useMemo(() => {
    if (!config?.fields) return null;
    for (const key of ['reference', 'name', 'code']) {
      if (config.fields[key]) return key;
    }
    return null;
  }, [config]);

  const displayValue = Form.useWatch(displayField || '', form);

  // Watch semua form values untuk trigger re-render column_config_rules
  const allFormValues = Form.useWatch([], form);

  // ── Generic: collect field values untuk column_config_rules ──
  // Watch semua field yg digunakan di column_config_rules (dari backend)
  // agar buildColumns bisa re-render saat nilai berubah
  const columnFieldValues = useMemo(() => {
    const vals: Record<string, any> = {};
    const rules = config?.column_config_rules;
    if (!rules) return vals;
    const fields = new Set<string>();
    Object.values(rules).forEach((relRules: any) => {
      Object.values(relRules).forEach((rule: any) => {
        Object.keys(rule.hide_when || {}).forEach(f => fields.add(f));
        Object.keys(rule.readonly_when || {}).forEach(f => fields.add(f));
        Object.keys(rule.editable_when || {}).forEach(f => fields.add(f));
      });
    });
    fields.forEach(f => { vals[f] = form.getFieldValue(f); });
    return vals;
  }, [config, allFormValues]);

  // ── Ref to avoid stale closure in effects ──
  const lineItemsRef = useRef(lineItems);
  lineItemsRef.current = lineItems;

  // ── Initial values for form fields (from fetched record or defaults) ──
  const initialValues = useMemo(() => {
    if (!config) return {};
    if (!recordData) return {};
    const values: Record<string, unknown> = {};
    Object.entries(config.fields).forEach(([key, field]) => {
      if (field.type === 'date' && recordData[key]) {
        values[key] = parseDate(recordData[key] as string);
      } else if (field.type === 'many2one' && recordData[key] && typeof recordData[key] === 'object') {
        values[key] = (recordData[key] as Record<string, unknown>)?.id ?? null;
      } else {
        values[key] = recordData[key] ?? undefined;
      }
    });
    return values;
  }, [recordData, config]);

  // ── Icon name → Ant Design component map ──
  const ICON_MAP: Record<string, React.ReactNode> = {
    FileTextOutlined: <FileTextOutlined />,
    MailOutlined: <MailOutlined />,
    CheckOutlined: <CheckOutlined />,
    MoreOutlined: <MoreOutlined />,
    PrinterOutlined: <PrinterOutlined />,
    DownloadOutlined: <DownloadOutlined />,
    SendOutlined: <SendOutlined />,
    EditOutlined: <EditOutlined />,
    CopyOutlined: <CopyOutlined />,
    StopOutlined: <StopOutlined />,
    UndoOutlined: <UndoOutlined />,
    SaveOutlined: <SaveOutlined />,
    CloseOutlined: <CloseOutlined />,
  };

  // ── Action buttons from config, filtered by states ──
  const actionButtons = useMemo(() => {
    const all = config?.form_view?.header?.actions ?? [];
    if (!recordData) return [];
    const currentStatus = recordData?.status as string | undefined;
    if (!currentStatus) return all;
    return all.filter((btn: Record<string, unknown>) => {
      const states = btn.states as string[] | undefined;
      if (!states || states.length === 0) return true;
      return states.includes(currentStatus);
    });
  }, [config, recordData]);

  // ── Editable / read-only mode ──
  const currentStatus = recordData?.status as string | undefined;
  const stateConfig = currentStatus ? (config?.states as Record<string, {allow_edit?: boolean}> | undefined)?.[currentStatus] : undefined;
  // readOnly prop (menu alias seperti Project Update) digabung dengan status config
  const isReadOnly = readOnly || (!!currentStatus && stateConfig?.allow_edit === false);

  // Per-field editable check: field punya editable_statuses sendiri?
  const isFieldDisabled = useCallback((fieldKey: string) => {
    if (!currentStatus) return false;
    const field = config?.fields?.[fieldKey];
    if (!field) return false;
    const fieldStatuses = (field as Record<string, unknown>)?.editable_statuses as string[] | undefined;
    if (fieldStatuses) {
      return !fieldStatuses.includes(currentStatus);
    }
    return isReadOnly;
  }, [config, currentStatus, isReadOnly]);

  // ── Handle action button click ──
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const handleAction = useCallback(async (btn: Record<string, unknown>) => {
    const actionName = btn.action as string;
    if (!actionName) return;
    if (!recordData && !isNew) {
      message.warning('Record is still loading, please wait');
      setActionLoading(null);
      return;
    }
    setActionLoading(actionName);

    // ── If action has goto_tab, switch notebook tab instead of wizard/API ──
    const gotoTab = btn.goto_tab as string | undefined;
    if (gotoTab) {
      setActiveNotebookKey(gotoTab);
      // Scroll notebook card into view after tab switch
      setTimeout(() => {
        notebookRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
      setActionLoading(null);
      return;
    }

    // ── If action has wizard config, show modal instead of calling API directly ──
    const wizardCfg = btn.wizard as Record<string, unknown> | undefined;
    if (wizardCfg) {
      setActionWizardBtn(btn);
      setActionWizardVisible(true);
      setActionLoading(null);
      return;
    }

    // Local variable — bisa berubah setelah create record
    let currentRecordId = recordId ? Number(recordId) : null;

    // ── Save form data first (only if editable) ──
    const currentStatus = recordData?.status as string;
    const stateConfig = config?.states?.[currentStatus] as Record<string, unknown> | undefined;
    const canEdit = stateConfig?.allow_edit !== false;

    if (canEdit) {
      const saveKey = 'save_before_action';
      message.loading({ content: 'Saving data...', key: saveKey });
      try {
        const values = await form.validateFields();
        const prepared = { ...values };
        // Convert undefined values from cleared fields → null for API
        // (hanya field yang dirender di form; field tersembunyi seperti
        // purchase_request TIDAK dikirim null → relasi antar dokumen terjaga)
        Object.entries(config?.fields || {}).forEach(([key, field]) => {
          if (field.type === 'many2one' && prepared[key] === undefined
              && (renderedFormKeys === null || renderedFormKeys.has(key))) {
            prepared[key] = null;
          }
        });
        // Include fields not wrapped in Form.Item
        formFields.forEach(([key]) => {
          if (!(key in prepared)) {
            const v = form.getFieldValue(key);
            if (v !== undefined) {
              prepared[key] = v;
            } else if (config?.fields?.[key]?.type === 'many2one'
                       && (renderedFormKeys === null || renderedFormKeys.has(key))) {
              prepared[key] = null;
            }
          }
        });
        // Date conversion
        Object.entries(config?.fields || {}).forEach(([key, field]) => {
          if (field.type === 'date' && prepared[key] && typeof (prepared[key] as Record<string, unknown>)?.format === 'function') {
            prepared[key] = (prepared[key] as { format: (f: string) => string }).format('YYYY-MM-DD');
          }
          if (field.type === 'many2one' && prepared[key] && typeof prepared[key] === 'object') {
            prepared[key] = (prepared[key] as Record<string, unknown>)?.id ?? null;
          }
        });
        // ── Validate required fields on all child lines before save+action ──
        let hasLineErrors = false;
        Object.entries(lineItems).forEach(([fieldName, items]) => {
          if (items.length === 0) return;
          const childCfg = childConfigs[fieldName];
          const fMeta = config?.fields?.[fieldName];
          const inverseField = fMeta?.type === 'one2many' ? (fMeta as Record<string, string>).inverse_field : undefined;
          const errors = collectRequiredErrors(items, childCfg as Record<string, unknown>, inverseField);
          if (errors.length > 0) {
            hasLineErrors = true;
            errors.forEach((err) => {
              message.error(`"${childConfigs[fieldName]?.label || fieldName}" baris ${err.row}: ${err.label} wajib diisi`);
            });
          }
        });
        if (hasLineErrors) {
          setActionLoading(null);
          message.error({ content: 'Lengkapi kolom wajib pada semua baris', key: saveKey });
          return;
        }

        // Append one2many line items to payload (sama kayak manual save)
        Object.entries(lineItems).forEach(([fieldName, items]) => {
          prepared[fieldName] = items
            .filter((item) => !item._isAddButton)
            .map((item) => {
            const { _key, ...rest } = item;
            const childCfg = childConfigs[fieldName];
            if (childCfg?.fields) {
              const m2oKeys = Object.entries(childCfg.fields)
                .filter(([, f]) => f.type === 'many2one')
                .map(([k]) => k);
              m2oKeys.forEach((k) => {
                const v = rest[k];
                if (v && typeof v === 'object') {
                  const id = (v as Record<string, unknown>).value ?? (v as Record<string, unknown>).id;
                  if (id != null) {
                    rest[k] = { id: Number(id) };
                  }
                }
              });
            }
            return rest;
          });
        });

        if (isNew) {
          // Create record dulu, baru action
          const created = await modelApi.createRecord(apiModelName, prepared);
          currentRecordId = created?.id as number;
          setRecordIds([currentRecordId]);
        } else {
          await modelApi.updateRecord(apiModelName, currentRecordId!, prepared);
        }
        setChatterKey((prev) => prev + 1);
        queryClient.invalidateQueries({ queryKey: ['model-records'] });
        message.success({ content: 'Data tersimpan', key: saveKey, duration: 1 });
        syncSaveSnapshot();
      } catch {
        message.error({ content: 'Gagal menyimpan, aksi dibatalkan', key: saveKey });
        setActionLoading(null);
        return;
      }
    }

    // ── Execute action ──
    try {
      const result = await modelApi.postAction(apiModelName, currentRecordId!, actionName);

      // Handle error response
      if (result.error) {
        message.error(result.error as string);
        setActionLoading(null);
        return;
      }

      if (result._action_type === 'print_preview' && result.url) {
        try {
          const token = localStorage.getItem('access_token');
          const resp = await fetch(result.url as string, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          setPrintPreviewHtml(await resp.text());
          setPrintPdfUrl((result.pdf_url as string) ?? null);
          return;
        } catch (e) {
          message.error('Failed to load print preview');
        }
      }
      if (result._action_type === 'redirect' && result.url) {
        window.open(result.url as string, '_blank');
        return;
      }
      // Handle open_record: navigate to child record created by action
      if (result._action_type === 'open_record') {
        const targetModel = result.model as string;
        const targetId = result.record_id as number;
        if (targetModel && targetId) {
          const urlName = apiToUrlName(targetModel);
          navigate(`/${urlName}/${targetId}?from=${apiModelName}&fromId=${recordId}`);
          if (result.message) message.success(result.message as string);
        }
        return;
      }
      // Convert dates + normalize many2one before setting form values
      if (config) {
        Object.entries(config.fields).forEach(([key, field]) => {
          if (field.type === 'date' && result[key]) {
            result[key] = parseDate(result[key] as string);
          }
          if (field.type === 'many2one' && result[key] && typeof result[key] === 'object') {
            result[key] = (result[key] as Record<string, unknown>)?.id ?? null;
          }
        });
      }
      // Remove action metadata keys before setting form
      const recordData = { ...result };
      delete recordData._action_type;
      delete recordData.message;
      delete recordData.url;
      form.setFieldsValue(recordData);
      setRecordData(recordData);
      syncSaveSnapshot();
      // Navigate to the new ID if this was a new record
      if (isNew && currentRecordId) {
        navigate(`${basePath}/${currentRecordId}`, { replace: true });
      }
      // Update stepper step from response status
      if (recordData.status && config?.fields?.status?.options) {
        const idx = config.fields.status.options.findIndex(
          (o) => o.value === recordData.status,
        );
        if (idx >= 0) setCurrentStep(idx);
      }
      // Refresh chatter log
      setChatterKey((prev) => prev + 1);
      if (result.message) {
        message.success(result.message as string);
      } else {
        message.success(`${actionName} completed`);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || (err as Error)?.message || 'Action failed';
      message.error(msg);
    } finally {
      setActionLoading(null);
    }
  }, [apiModelName, recordId, isNew, form, config, recordData, lineItems, childConfigs, modelName, navigate]);

  // ── Action wizard confirm — called from GenericWizardModal ──
  const handleWizardConfirm = useCallback(async (mode: string, selectedLines: Record<string, unknown>[], extraInputs?: Record<string, number>) => {
    if (!actionWizardBtn) return;
    const actionName = actionWizardBtn.action as string;
    if (!actionName) return;
    let currentRecordId = recordId ? Number(recordId) : null;
    if (!currentRecordId && !isNew) return;

    // Save form + execute action with wizard data
    try {
      const currentStatus = recordData?.status as string;
      const stateConfig = config?.states?.[currentStatus] as Record<string, unknown> | undefined;
      const canEdit = stateConfig?.allow_edit !== false;

      const prepared: Record<string, unknown> = {};
      if (canEdit) {
        const values = await form.validateFields();
        Object.assign(prepared, values);
        // Convert undefined many2one → null
        Object.entries(config?.fields || {}).forEach(([key, field]) => {
          if (field.type === 'many2one' && prepared[key] === undefined) prepared[key] = null;
        });
        // Convert dates
        Object.entries(config?.fields || {}).forEach(([key, field]) => {
          if (field.type === 'date' && prepared[key] && typeof (prepared[key] as Record<string, unknown>)?.format === 'function') {
            prepared[key] = (prepared[key] as { format: (f: string) => string }).format('YYYY-MM-DD');
          }
        });
        // Append line items
        Object.entries(lineItems).forEach(([fieldName, items]) => {
          prepared[fieldName] = items.filter((i) => !i._isAddButton).map((item) => {
            const { _key, ...rest } = item;
            return rest;
          });
        });
      }

      // Save or create
      if (isNew) {
        const created = await modelApi.createRecord(apiModelName, prepared);
        currentRecordId = created?.id as number;
      } else if (canEdit) {
        await modelApi.updateRecord(apiModelName, currentRecordId!, prepared);
      }

      // Execute action with wizard data
      const extraData: Record<string, unknown> = { mode, selected_lines: selectedLines, line_id: (actionWizardBtn as any)?.rowId ?? null, ...(extraInputs || {}) };

      // Helper: handle response sukses setelah action berhasil
      const finishWizardAction = (res: Record<string, unknown>) => {
        if (res.error) {
          message.error(res.error as string);
          return;
        }
        // Sukses — tutup wizard
        setActionWizardVisible(false);
        queryClient.invalidateQueries({ queryKey: ['model-records'] });
        // Reset dirty flag + bypass blocker sebelum navigate agar navigasi sah tidak ditahan
        syncSaveSnapshot();
        skipBlockerRef.current = true;
        // Handle response
        if (res._action_type === 'open_record') {
          const targetModel = res.model as string;
          const targetId = res.record_id as number;
          if (targetModel && targetId) {
            navigate(`/${apiToUrlName(targetModel)}/${targetId}?from=${apiModelName}&fromId=${recordId}`);
          }
        } else {
          navigate(`${basePath}/${currentRecordId}`, { replace: isNew });
        }
        if (res.message) message.success(res.message as string);
      };

      const result = await modelApi.postAction(apiModelName, currentRecordId!, actionName, extraData);

      // Konfirmasi dialog: backend minta user pilih Lanjut/Tidak sebelum action dijalankan
      if (result._action_type === 'confirm' && result.confirm_message) {
        Modal.confirm({
          title: 'Konfirmasi',
          content: result.confirm_message as string,
          okText: 'Lanjut',
          cancelText: 'Tidak',
          onOk: async () => {
            const res2 = await modelApi.postAction(apiModelName, currentRecordId!, actionName, { ...extraData, confirmed: true });
            finishWizardAction(res2);
          },
        });
        return;
      }

      finishWizardAction(result);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || (err as Error)?.message || 'Action failed';
      message.error(msg);
    }
  }, [actionWizardBtn, apiModelName, config, form, isNew, lineItems, basePath, navigate, recordData, recordId]);

  // ── Fetch data tabel untuk mode wizard bertipe `table` (read-only view) ──
  const handleFetchWizardTable = useCallback(async (mode: string) => {
    if (!actionWizardBtn) return { rows: [] };
    const actionName = actionWizardBtn.action as string;
    if (!actionName) return { rows: [] };
    const currentRecordId = recordId ? Number(recordId) : null;
    if (!currentRecordId) return { rows: [] };
    const extraData: Record<string, unknown> = {
      mode,
      line_id: (actionWizardBtn as any)?.rowId ?? null,
    };
    const result = await modelApi.postAction(apiModelName, currentRecordId, actionName, extraData);
    if (result.error) throw new Error(result.error as string);
    return { rows: ((result as Record<string, unknown>).rows as Record<string, unknown>[]) || [] };
  }, [actionWizardBtn, apiModelName, recordId]);

  // ── Prev/Next navigation ──
  const goPrev = useCallback(() => {
    if (currentIdx > 0) navigate(`${basePath}/${recordIds[currentIdx - 1]}`);
  }, [currentIdx, recordIds, basePath, navigate]);
  const goNext = useCallback(() => {
    if (currentIdx < recordIds.length - 1) navigate(`${basePath}/${recordIds[currentIdx + 1]}`);
  }, [currentIdx, recordIds, basePath, navigate]);

  // ── Fetch parent record for breadcrumb chain ──
  useEffect(() => {
    if (!fromModel || !fromId) return;
    setParentRecord(null);

    // Fetch parent config for verbose name
    modelApi.getConfig(fromModel).then((cfg) => {
      // Fetch parent record for display name
      modelApi.getRecord(fromModel, Number(fromId)).then((record) => {
        const displayName = String(record.reference || record.name || record.code || `#${fromId}`);
        setParentRecord({
          id: Number(fromId),
          display_name: displayName,
          verbose_name: cfg.verbose_name_plural || cfg.verbose_name,
        });
      }).catch(() => {});
    }).catch(() => {});
  }, [fromModel, fromId]);

  // ── Smart button click handler ──
  // Navigasi ke child record dari summary card
  const handleNavigate = useCallback((targetModel: string, targetId: number) => {
    const urlName = apiToUrlName(targetModel);
    navigate(`/${urlName}/${targetId}`);
  }, [navigate]);

  const handleSmartButtonClick = useCallback((btn: { label: string; model?: string }) => {
    if (!btn.model) return;
    const previews = (recordData as Record<string, unknown>)?._smart_button_previews as
      Record<string, { id: number; display_name: string; status?: string }[]> | undefined;
    const children = previews?.[btn.model];

    if (children && children.length > 0) {
      // Ada record anak — navigasi
      if (children.length === 1) {
        const child = children[0];
        const urlName = apiToUrlName(btn.model);
        navigate(`/${urlName}/${child.id}?from=${apiModelName}&fromId=${recordId}`);
      } else {
        setWizardData({ model: btn.model, records: children });
        setWizardVisible(true);
      }
      return;
    }

    // Cek apakah smart button model cocok dengan Many2OneField di record ini
    // (navigasi ke parent record — misal GR → Purchase Order)
    if (config?.fields) {
      const m2oMatch = Object.entries(config.fields).find(
        ([, f]) => f.type === 'many2one' && f.relation === btn.model
      );
      if (m2oMatch) {
        const [fieldName] = m2oMatch;
        const parentVal = (recordData as Record<string, unknown>)?.[fieldName];
        // Many2One bisa berupa {id: 60, name: '...'} atau langsung number
        const parentId = parentVal && typeof parentVal === 'object'
          ? (parentVal as Record<string, unknown>).id as number
          : parentVal as number;
        if (parentId) {
          const urlName = apiToUrlName(btn.model || '');
          navigate(`/${urlName}/${parentId}`);
          return;
        }
      }
    }

    message.info('Belum ada data terkait');
  }, [recordData, apiModelName, recordId, navigate, config]);

  // ── One2Many line item helpers ──
  const addLine = useCallback((relationField: string) => {
    const childCfg = childConfigs[relationField];

    // ── add_line_guard: pastikan field header wajib sudah diisi sebelum add line ──
    // definisinya di notebook tab: { ..., add_line_guard: ['vendor', 'payment_method'] }
    const notebookTabs = config?.form_view?.notebook || [];
    const tab = notebookTabs.find((t: { relation?: string }) => t.relation === relationField);
    const guardFields = (tab as any)?.add_line_guard as string[] | undefined;
    if (guardFields && guardFields.length > 0) {
      for (const gf of guardFields) {
        const val = form.getFieldValue(gf);
        if (!val) {
          const fieldLabel = config?.fields?.[gf]?.label || gf;
          message.warning(`Isi ${fieldLabel} terlebih dahulu`);
          return;
        }
      }
    }

    // ── Validate required fields on last line before adding new one ──
    const items = lineItems[relationField] || [];
    if (items.length > 0) {
      const fieldMeta = config?.fields?.[relationField];
      const inverseField = fieldMeta?.type === 'one2many' ? (fieldMeta as Record<string, string>).inverse_field : undefined;
      const errors = collectRequiredErrors(items, childCfg as Record<string, unknown>, inverseField);
      if (errors.length > 0) {
        const fieldList = [...new Set(errors.map((e) => e.label))].join(', ');
        message.warning(`Lengkapi kolom wajib pada baris sebelumnya: ${fieldList}`);
        return;
      }
    }
    const newKey = `line_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const newItem: Record<string, unknown> = { _key: newKey };
    if (childCfg) {
      Object.entries(childCfg.fields).forEach(([key, field]) => {
        if (key === 'id' || key === 'created_at' || key === 'updated_at' || key === 'is_deleted') return;
        if (field.default !== undefined && field.default !== null) {
          newItem[key] = field.default;
        } else if (field.type === 'boolean') {
          newItem[key] = false;
        } else if (['float', 'monetary', 'integer'].includes(field.type)) {
          newItem[key] = 0;
        } else if (field.type === 'many2one') {
          newItem[key] = null;  // null = native AG Grid "Select an option" placeholder
        } else {
          newItem[key] = '';
        }
      });
    }
    setLineItems((prev) => ({
      ...prev,
      [relationField]: [...(prev[relationField] || []), newItem],
    }));
  }, [childConfigs, lineItems, config, form]);

  const deleteLine = useCallback((relationField: string, key: string) => {
    setLineItems((prev) => ({
      ...prev,
      [relationField]: (prev[relationField] || []).filter((item) => item._key !== key),
    }));
    setSummaryRevision((v) => v + 1);
  }, [setSummaryRevision]);

  // ── Required field validators for child lines ──

  /** Check if a value is considered "empty" for required-field validation */
  function isLineFieldEmpty(val: unknown): boolean {
    if (val === null || val === undefined) return true;
    if (typeof val === 'string' && val.trim() === '') return true;
    // Many2One: AG Grid stores as {value, label} or {id, name}
    if (typeof val === 'object' && !(val as Record<string, unknown>)?.value && !(val as Record<string, unknown>)?.id) {
      return true;
    }
    return false;
  }

  /** Collect missing required field errors for ALL non-add-button lines.
   *  Returns [{ key, label }] per missing field.
   *  @param inverseField — if provided, skip this field (e.g. the FK/inverse back-link auto-set by backend) */
  function collectRequiredErrors(
    items: Record<string, unknown>[],
    childCfg: Record<string, unknown>,
    inverseField?: string
  ): { key: string; label: string; row: number }[] {
    const errors: { key: string; label: string; row: number }[] = [];
    const childFields = (childCfg as any)?.fields as Record<string, any> | undefined;
    if (!childFields) return errors;
    const requiredFields = Object.entries(childFields)
      .filter(([k, f]) => f.required && k !== inverseField)
      .map(([k, f]) => ({ key: k, label: f.label || k }));
    if (requiredFields.length === 0) return errors;
    items.filter((item) => !item._isAddButton).forEach((item, idx) => {
      requiredFields.forEach(({ key, label }) => {
        if (isLineFieldEmpty(item[key])) {
          errors.push({ key, label, row: idx + 1 });
        }
      });
    });
    return errors;
  }

  /**
   * Load halaman berikutnya options many2one (infinite scroll).
   * Mengembalikan options baru agar editor bisa append ke list lokalnya.
   */
  const loadMoreMany2one = useCallback(async (
    relationField: string,
    fieldName: string,
    displayField?: string,
    allowDuplicate?: boolean,
  ): Promise<Record<string, unknown>[]> => {
    const key = `${relationField}.${fieldName}`;
    const meta = many2oneMeta[key];
    const childCfg = childConfigs[relationField];
    const fieldMeta = childCfg?.fields?.[fieldName];
    if (!meta || !fieldMeta?.relation || meta.loading) return [];
    if (meta.page * M2O_PAGE_SIZE >= meta.total) return [];
    setMany2oneMeta((prev) => ({ ...prev, [key]: { ...prev[key], loading: true } }));
    try {
      const response = await modelApi.listRecords(fieldMeta.relation, meta.page + 1, M2O_PAGE_SIZE, meta.params);
      let opts: Record<string, unknown>[] = response.results.map((r) => ({
        ...r,
        value: r.id as number,
        label: displayField
          ? ((r[displayField] as string) || `#${r.id}`)
          : ((r.name as string) || `#${r.id}`),
      }));
      // Filter: sembunyikan yang sudah dipilih di baris lain (sama seperti awal)
      if (!allowDuplicate) {
        const selectedIds = new Set(
          (lineItems[relationField] || [])
            .filter((item) => !item._isAddButton && item[fieldName]?.id)
            .map((item) => (item[fieldName] as Record<string, unknown>).id as number),
        );
        opts = opts.filter((o) => !selectedIds.has(o.value as number));
      }
      // Merge ke state parent (dedupe by value)
      setMany2oneOptions((prev) => {
        const existing = prev[key] || [];
        const seen = new Set(existing.map((o) => o.value));
        const merged = [...existing, ...opts.filter((o) => !seen.has(o.value as number))];
        return { ...prev, [key]: merged as { value: number; label: string; uom?: string }[] };
      });
      setMany2oneMeta((prev) => ({
        ...prev,
        [key]: { ...prev[key], page: meta.page + 1, total: response.count, loading: false },
      }));
      return opts;
    } catch {
      setMany2oneMeta((prev) => ({ ...prev, [key]: { ...prev[key], loading: false } }));
      return [];
    }
  }, [many2oneMeta, childConfigs, lineItems]);

  /** Build AG Grid column defs from child model config, excluding FK/audit fields */
  const buildColumns = useCallback((relationField: string, columnFilter?: (string | {name: string; display_field?: string})[], tabReadOnly?: boolean, rowActions?: Array<{label: string; actions?: Array<{label: string; action?: string; wizard?: Record<string, unknown>}>}>): ColDef[] => {
    const childCfg = childConfigs[relationField];
    if (!childCfg?.fields) return [];
    // Build column metadata from mixed columnFilter (string | {name, display_field})
    const columnNames = new Set<string>();
    const columnMeta: Record<string, {display_field?: string}> = {};
    if (Array.isArray(columnFilter)) {
      columnFilter.forEach((c) => {
        const name = typeof c === 'string' ? c : c.name;
        columnNames.add(name);
        if (typeof c === 'object' && c.display_field) {
          columnMeta[name] = {display_field: c.display_field};
        }
      });
    }
    const cols: ColDef[] = [];
    // Drag handle column — pindah urutan baris via drag & drop
    // Nomor # dihitung dari posisi ARRAY (lineItems) supaya recompute
    // mengikuti urutan data setelah drag (sync di onRowDragEnd).
    if (!(isReadOnly || tabReadOnly)) {
      cols.push({
        headerName: '',
        field: '_drag',
        width: 40,
        minWidth: 40,
        maxWidth: 40,
        flex: 0,
        sortable: false,
        resizable: false,
        editable: false,
        // rowDrag callback: row +Add tidak draggable → grip default AG Grid tidak dirender
        rowDrag: (params) => !(params.data as Record<string, unknown> | undefined)?._isAddButton,
        cellRenderer: (params: ICellRendererParams) => {
          if (params.data?._isAddButton || params.node?.rowPinned) return null;
          return <HolderOutlined style={{ color: '#999', cursor: 'grab' }} />;
        },
      });
    }
    // Row number column — atau tombol "+ Add" untuk baris add-button
    cols.push({
      headerName: '#',
      field: '_rowNum',
      width: 60,
      cellRenderer: (params: ICellRendererParams) => {
        if (params.data?._isAddButton) {
          return <Button type="dashed" size="small" icon={<PlusOutlined />} loading={addingLine} style={{ width: '100%', border: 'none', color: '#1890ff', fontWeight: 500 }}>Add</Button>;
        }
        if (params.node?.rowPinned) return <span style={{ fontWeight: 'bold' }}>{params.data?._rowNum ?? ''}</span>;
        const items = (lineItems[relationField] || []) as Record<string, unknown>[];
        const idx = items.findIndex((it) => it._key === params.data._key);
        return <span style={{ fontWeight: 'bold' }}>{(idx >= 0 ? idx : (params.node?.rowIndex ?? 0)) + 1}</span>;
      },
      editable: false,
      sortable: false,
      resizable: false,
    });
    Object.entries(childCfg.fields).forEach(([key, field]) => {
      // Skip FK inverse field, id, audit
      if (key === 'id' || key === 'created_at' || key === 'updated_at' || key === 'is_deleted') return;
      const fieldMeta = config?.fields?.[relationField];
      if (fieldMeta?.type === 'one2many' && key === (fieldMeta as Record<string, string>).inverse_field) return;
      // Skip if columnFilter is provided and this field isn't in it
      if (columnFilter && !columnNames.has(key)) return;
      // Check field-level editable_statuses first, fallback to form-level
      const fieldEditable = Array.isArray((field as any)?.editable_statuses)
        ? (field as any).editable_statuses.includes(currentStatus)
        : !(isReadOnly || tabReadOnly);
      // Check field-level hidden_statuses — skip column if status is in hidden list
      const fieldHidden = Array.isArray((field as any)?.hidden_statuses)
        ? (field as any).hidden_statuses.includes(currentStatus)
        : false;
      if (fieldHidden) return;
      const col: ColDef = {
        headerName: field.required ? `${field.label || key} *` : (field.label || key),
        field: key,
        editable: (params: any) => {
          if (params.data?._isAddButton) return false;
          return fieldEditable && !field.depends;
        },
        cellStyle: (params: any) => {
          if (params.data?._isAddButton) return undefined;
          if (params.node?.rowPinned) return undefined;
          if (!fieldEditable || field.depends)
            return { backgroundColor: '#f5f5f5' };
          return undefined;
        },
      };
      if (['monetary', 'float', 'integer'].includes(field.type)) {
        col.type = 'numericColumn';
      }
      if (field.type === 'monetary') {
        col.valueFormatter = (params) => {
          if (params.value == null) return '';
          return `Rp ${Number(params.value).toLocaleString('id-ID')}`;
        };
        col.valueParser = (params) => {
          if (!params.newValue) return 0;
          const cleaned = String(params.newValue).replace(/[^0-9.,]/g, '').replace(/\./g, '');
          return parseFloat(cleaned.replace(',', '.')) || 0;
        };
      }
      if (field.type === 'percentage') {
        // Progress bar 0–100% (merah → hijau) untuk field berflag progress
        if ((field as Record<string, unknown>).progress) {
          col.cellRenderer = (params: ICellRendererParams) => (
            <ProgressBar value={params.value as number | null | undefined} />
          );
        }
        col.valueFormatter = (params) => {
          if (params.value == null) return '';
          return `${params.value}%`;
        };
        col.valueParser = (params) => {
          if (params.newValue == null) return 0;
          const val = parseFloat(String(params.newValue).replace(/[^0-9.]/g, ''));
          if (isNaN(val)) return 0;
          return Math.min(100, val);
        };
      }
      // Date: tampilkan DD-MMM-YYYY, editor pakai date picker bawaan (string-safe)
      if (field.type === 'date') {
        col.cellDataType = 'dateString';
        col.valueFormatter = (params) => {
          if (!params.value) return '';
          return formatDate(params.value);
        };
        col.cellEditor = 'agDateStringCellEditor';
        col.cellEditorParams = {
          parseValue: (value: string) => {
            if (!value) return null;
            const d = parseDate(value);
            return d ? d.format('YYYY-MM-DD') : value;
          },
        };
      }
      // Selection: colored Tag badge (only when colors defined)
      if (field.type === 'selection') {
        const fieldColors = (childCfg.fields[key] as Record<string, unknown>)?.colors as Record<string, string> | undefined;
        if (fieldColors) {
          col.cellRenderer = (params: ICellRendererParams) => {
            const label = field.options?.find(
              (o: { value: string; label: string }) => o.value === params.value,
            )?.label || params.value;
            const color = fieldColors[params.value as string] || 'default';
            return <Tag color={color}>{label}</Tag>;
          };
        }
      }
      // Many2One: show display name, rich select editor with search
      if (field.type === 'many2one') {
        // Store display_field from notebook column config (dipakai juga di onLoadMore)
        const colMeta = columnMeta[key];
        if (colMeta?.display_field) {
          (col as any).displayField = colMeta.display_field;
        }
        col.editable = (params: any) => {
          if (params.data?._isAddButton) return false;
          return !isReadOnly;
        };
        col.cellRenderer = (params: ICellRendererParams) => {
          const val = params.value;
          if (typeof val === 'object' && val?.name) return val.name;
          if (typeof val === 'object' && val?.label) return val.label;
          return val ?? '';
        };
        // Sort berdasarkan nilai yang TAMPIL (name/label), bukan object/id —
        // defaultComparator AG Grid tidak bisa membandingkan object {id, name}
        col.comparator = (a: unknown, b: unknown) => {
          const name = (v: unknown) => {
            if (typeof v === 'object' && v && 'name' in (v as Record<string, unknown>)) {
              return String((v as Record<string, unknown>).name);
            }
            if (typeof v === 'object' && v && 'label' in (v as Record<string, unknown>)) {
              return String((v as Record<string, unknown>).label);
            }
            return v == null ? '' : String(v);
          };
          return name(a).localeCompare(name(b), 'id');
        };
        col.cellEditor = Many2OneCellEditor;
        col.cellEditorParams = {
          values: (many2oneOptions[`${relationField}.${key}`] || []).filter((opt) => {
            // Field dengan allow_duplicate=True → boleh pilih nilai yang sama di baris lain
            if (field.allow_duplicate) return true;
            // Hide options already selected in other lines of the same relation
            const record = opt as Record<string, unknown>;
            const selectedIds = new Set(
              (lineItems[relationField] || [])
                .filter((item) => !item._isAddButton && item[key]?.id)
                .map((item) => (item[key] as Record<string, unknown>).id as number),
            );
            return !selectedIds.has(record.value as number);
          }),
          // Infinite scroll: total dari server + pemuat halaman berikutnya
          total: many2oneMeta[`${relationField}.${key}`]?.total,
          onLoadMore: () => loadMoreMany2one(
            relationField,
            key,
            (colMeta?.display_field as string) || undefined,
            !!field.allow_duplicate,
          ),
        };
      }
      // ── Generic: column config rules dari backend ──
      // column_config_rules mendefinikan hide/readonly berdasarkan field value
      const columnRules = config?.column_config_rules?.[relationField];
      const rule = columnRules?.[key];
      if (rule?.hide_when) {
        const shouldHide = Object.entries(rule.hide_when).some(
          ([field, value]) => columnFieldValues[field] === value,
        );
        if (shouldHide) col.hide = true;
      }
      if (rule?.readonly_when) {
        const shouldReadonly = Object.entries(rule.readonly_when).some(
          ([field, value]) => columnFieldValues[field] === value,
        );
        if (shouldReadonly) {
          col.editable = false;
          col.cellStyle = (params: any) => {
            if (params.data?._isAddButton) return undefined;
            if (params.node?.rowPinned) return undefined;
            return { backgroundColor: '#f5f5f5' };
          };
        }
      }
      if (rule?.editable_when) {
        const shouldEditable = Object.entries(rule.editable_when).some(
          ([field, value]) => columnFieldValues[field] === value,
        );
        if (shouldEditable) {
          col.editable = (params: any) => {
            if (params.data?._isAddButton) return false;
            return !isReadOnly;
          };
          col.cellStyle = (params: any) => {
            if (params.data?._isAddButton) return undefined;
            if (params.node?.rowPinned) return undefined;
            if (isReadOnly) return { backgroundColor: '#f5f5f5' };
            return undefined;
          };
        }
      }
      cols.push(col);
    });
    // Action column with delete button (only in edit mode)
    const gridReadOnly = isReadOnly || tabReadOnly;
    if (!gridReadOnly) {
      cols.unshift({
        headerName: 'Action',
        field: '_action',
        width: 60,
        minWidth: 60,
        flex: 0,
        cellRenderer: (params: ICellRendererParams) => {
          if (params.data?._isAddButton || params.node?.rowPinned) return null;
          return (
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={deletingKey === params.data._key}
            onClick={() => { setDeletingKey(params.data._key); deleteLine(relationField, params.data._key); setDeletingKey(null); }}
          />
          );
        },
        editable: false,
        sortable: false,
        resizable: false,
      });
    }
    // ── Row actions column — config-driven dari notebook tab (row_actions) ──
    if (rowActions && rowActions.length > 0) {
      const actions = rowActions[0]?.actions || [];
      cols.push({
        headerName: 'Action',
        field: '_row_actions',
        width: 170,
        minWidth: 170,
        flex: 0,
        cellRenderer: (params: ICellRendererParams) => {
          if (params.data?._isAddButton || params.node?.rowPinned) return null;
          const openAction = (a: { label: string; action?: string; wizard?: Record<string, unknown> }) => {
            setActionWizardBtn({ label: a.label, action: a.action || '', wizard: a.wizard as Record<string, unknown>, rowId: params.data?.id ?? null });
            setActionWizardVisible(true);
          };
          // 1 action → button langsung (wizard multi-mode); >1 → dropdown
          if (actions.length === 1) {
            return (
              <Button
                size="small"
                type="primary"
                ghost
                style={{ fontSize: 11, padding: '0 8px', height: 22, lineHeight: '20px' }}
                onClick={() => openAction(actions[0])}
              >
                {rowActions[0]?.label || 'Action'}
              </Button>
            );
          }
          return (
            <Dropdown
              trigger={['click']}
              menu={{
                items: actions.map((a) => ({
                  key: a.label,
                  label: a.label,
                  onClick: () => openAction(a),
                })),
              }}
            >
              <Button size="small" type="primary" ghost style={{ fontSize: 11, padding: '0 8px', height: 22, lineHeight: '20px' }}>
                {rowActions[0]?.label || 'Action'}
              </Button>
            </Dropdown>
          );
        },
        editable: false,
        sortable: false,
        resizable: false,
      });
    }
    return cols;
  }, [childConfigs, config, deleteLine, many2oneOptions, many2oneMeta, loadMoreMany2one, isReadOnly, columnFieldValues, lineItems]);

  // ── Save handler ──
  const onSave = async () => {
    try {
      const values = await form.validateFields();
      // Convert dayjs objects to YYYY-MM-DD strings before sending
      const prepared = { ...values };
      // Convert undefined values from cleared fields → null for API
      // (hanya field yang dirender di form; field tersembunyi seperti
      // purchase_request TIDAK dikirim null → relasi antar dokumen terjaga)
      Object.entries(config?.fields || {}).forEach(([key, field]) => {
        if (field.type === 'many2one' && prepared[key] === undefined
            && (renderedFormKeys === null || renderedFormKeys.has(key))) {
          prepared[key] = null;
        }
      });
      // Include fields rendered without Form.Item (e.g. SummaryCard fields)
      // validateFields only returns fields with Form.Item wrappers
      if (config?.fields) {
        formFields.forEach(([key]) => {
          if (!(key in prepared)) {
            const v = form.getFieldValue(key);
            if (v !== undefined) {
              prepared[key] = v;
            } else if (config?.fields?.[key]?.type === 'many2one'
                       && (renderedFormKeys === null || renderedFormKeys.has(key))) {
              prepared[key] = null;
            }
          }
        });
      }
      Object.entries(config?.fields || {}).forEach(([key, field]) => {
        if (field.type === 'date' && prepared[key] && typeof (prepared[key] as Record<string, unknown>)?.format === 'function') {
          prepared[key] = (prepared[key] as { format: (f: string) => string }).format('YYYY-MM-DD');
        }
      });
      // ── Validate required fields on all child lines before save ──
      let hasLineErrors = false;
      Object.entries(lineItems).forEach(([fieldName, items]) => {
        if (items.length === 0) return;
        const childCfg = childConfigs[fieldName];
        const fMeta = config?.fields?.[fieldName];
        const inverseField = fMeta?.type === 'one2many' ? (fMeta as Record<string, string>).inverse_field : undefined;
        const errors = collectRequiredErrors(items, childCfg as Record<string, unknown>, inverseField);
        if (errors.length > 0) {
          hasLineErrors = true;
          errors.forEach((err) => {
            message.error(`"${childConfigs[fieldName]?.label || fieldName}" baris ${err.row}: ${err.label} wajib diisi`);
          });
        }
      });
      if (hasLineErrors) {
        setSaving(false);
        return;
      }
      setSaving(true);
      // Append one2many line items to payload
      Object.entries(lineItems).forEach(([fieldName, items]) => {
        prepared[fieldName] = items
          .filter((item) => !item._isAddButton)
          .map((item) => {
          const { _key, ...rest } = item;
          // Convert "id|name" strings → {id} for backend many2one fields
          const childCfg = childConfigs[fieldName];
          if (childCfg?.fields) {
            const m2oKeys = Object.entries(childCfg.fields)
              .filter(([, f]) => f.type === 'many2one')
              .map(([k]) => k);
            m2oKeys.forEach((k) => {
              const v = rest[k];
              if (v && typeof v === 'object') {
                // Handle {value, label} (raw editor) or {id, name} (processed / API)
                const id = (v as Record<string, unknown>).value ?? (v as Record<string, unknown>).id;
                if (id != null) {
                  rest[k] = { id: Number(id) };
                }
              }
            });
          }
          return rest;
        });
      });
      if (isNew) {
        const result = await modelApi.createRecord(apiModelName, prepared);
        syncSaveSnapshot();
        skipBlockerRef.current = true;
        message.success('Berhasil dibuat');
        navigate(`${basePath}/${result?.id || recordId}`);
      } else {
        const result = await modelApi.updateRecord(apiModelName, Number(recordId), prepared);
        // Normalize response dates & many2one
        if (config) {
          Object.entries(config.fields).forEach(([key, field]) => {
            if (field.type === 'date' && result[key]) {
              result[key] = parseDate(result[key] as string);
            }
            if (field.type === 'many2one' && result[key] && typeof result[key] === 'object') {
              result[key] = (result[key] as Record<string, unknown>)?.id ?? null;
            }
          });
        }
        form.setFieldsValue(result);
        setRecordData(result);
        syncSaveSnapshot();
        message.success('Berhasil disimpan');
      }
      queryClient.invalidateQueries({ queryKey: ['model-records'] });
      setChatterKey((prev) => prev + 1); // refresh chatter logs
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) {
        return;
      }
      // Try to extract backend error message from Axios response
      const axiosErr = err as Record<string, unknown>;
      const backendMsg = (axiosErr?.response as Record<string, unknown>)?.data as Record<string, unknown>;
      const msg = typeof backendMsg?.error === 'string' ? backendMsg.error : (err as Error)?.message || '';
      message.error(msg || 'Gagal menyimpan');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config || (!recordData && !isNew)) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  // ── Header fields = fields that go into the main card body ──
  const headerFieldKeys = new Set(
    config?.form_view?.header?.tabs
      ? config.form_view.header.tabs.flatMap((tab: { fields?: string[] }) => tab.fields || [])
      : (config?.form_view?.header?.fields || [])
  );

  // ── Notebook & Header tabs from form_view config ──
  const notebook = config?.form_view?.notebook || [];
  const notebookFieldKeys = new Set(
    notebook.flatMap((tab: { fields?: string[] }) => tab.fields || []),
  );
  const headerTabsList = config?.form_view?.header?.tabs || [];

  // Main card: fields from header.fields, or all fields if header not defined
  const mainFields = headerFieldKeys.size > 0
    ? formFields.filter(([key]) => headerFieldKeys.has(key))
    : formFields;

  // ── Build tab items (reusable for both header tabs and notebook tabs) ──
  const buildTabItems = (tabs: Array<{ key: string; label: string; fields?: string[]; relation?: string; columns?: (string | {name: string; display_field?: string})[]; read_only?: boolean; summary?: Record<string, unknown> }>) => {
    return tabs.map((tab) => ({
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
                  {renderField(fieldName, effectiveField as any, {}, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(fieldName))}
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
                const aggStyles: Record<string, React.CSSProperties> = {};
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
                  if (fieldMeta?.type === 'many2one' && fieldMeta.relation) {
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
  };

  const notebookTabs = buildTabItems(notebook);
  const headerTabs = buildTabItems(headerTabsList);

  // ── Group main fields into 3 columns ──
  const col1 = mainFields.filter((_, i) => i % 3 === 0);
  const col2 = mainFields.filter((_, i) => i % 3 === 1);
  const col3 = mainFields.filter((_, i) => i % 3 === 2);

  return (
    <div
      style={
        printPreviewHtml
          ? { display: 'flex', flexDirection: 'column', height: '100vh', gap: 0 }
          : { display: 'flex', flexDirection: 'column', gap: 12 }
      }
    >
      {/* ═══ HEADER ═══ */}
      {!printPreviewHtml && (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
        }}
      >
        {/* Row 1: Breadcrumb | ◀▶ (right, above stepper) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Breadcrumb
            items={[
              ...(parentRecord && fromModel
                ? [
                    {
                      title: (
                        <a
                          href={`/${fromModel.replace(/\./g, '-')}`}
                          style={{ fontSize: 11 }}
                          onClick={(e) => { e.preventDefault(); navigate(`/${fromModel.replace(/\./g, '-')}`); }}
                        >
                          {parentRecord.verbose_name}
                        </a>
                      ),
                    },
                    {
                      title: (
                        <a
                          href={`/${apiToUrlName(fromModel)}/${parentRecord.id}`}
                          style={{ fontSize: 11 }}
                          onClick={(e) => { e.preventDefault(); navigate(`/${apiToUrlName(fromModel)}/${parentRecord.id}`); }}
                        >
                          {parentRecord.display_name}
                        </a>
                      ),
                    },
                  ]
                : []),
              {
                title: (
                  <a
                    href={`${basePath}`}
                    style={{ fontSize: 11 }}
                    onClick={(e) => { e.preventDefault(); navigate(`${basePath}`); }}
                  >
                    {config.verbose_name_plural}
                  </a>
                ),
              },
              {
                title: (
                  <span style={{ fontSize: 11, fontWeight: 500 }}>
                    {isNew ? `Buat ${config.verbose_name}` : (recordData?.display_name as string) || `#${recordId}`}
                  </span>
                ),
              },
              ...(printPreviewHtml
                ? [{ title: <span style={{ fontSize: 11 }}>Print Preview</span> }]
                : []),
            ]}
            style={{ fontSize: 11 }}
          />
          {/* ── Save Status + Navigation (right group) ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Save Status Indicator */}
            <span
              style={{
                fontSize: 11,
                color: saving || actionLoading ? '#1677ff'
                  : dirtyFlag ? '#faad14' : '#555',
                whiteSpace: 'nowrap',
                userSelect: 'none',
                transition: 'opacity 0.15s',
              }}
            >
              {saving || actionLoading ? (
                <>○ Menyimpan...</>
              ) : dirtyFlag ? (
                <>⚠ Perubahan belum disimpan</>
              ) : recordData?.updated_at ? (
                <>{formatLastUpdate(recordData.updated_at as string, (recordData.updated_by as Record<string, unknown> | undefined)?.name as string)}</>
              ) : (
                <></>
              )}
            </span>
            <Space size={2}>
            <Button
              size="small"
              variant="outlined"
              color="primary"
              icon={<ArrowLeftOutlined />}
              title="Previous record"
              disabled={currentIdx <= 0}
              onClick={goPrev}
            />
            <span
              style={{
                fontSize: 11,
                color: '#666',
                padding: '0 4px',
                userSelect: 'none',
              }}
            >
              {isNew ? '-' : `${currentIdx + 1}/${recordIds.length}`}
            </span>
            <Button
              size="small"
              variant="outlined"
              color="primary"
              icon={<ArrowRightOutlined />}
              title="Next record"
              disabled={currentIdx >= recordIds.length - 1}
              onClick={goNext}
            />
          </Space>
          </div>{/* /right group */}
        </div>

        {/* Row 2: Title | Save/Discard */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Title level={4} style={{ margin: 0, lineHeight: 1.4 }}>
            {isNew ? (
              <>Buat {config.verbose_name}</>
            ) : (
              <>
                {config.verbose_name} — {typeof displayValue === 'object' && displayValue
                  ? (displayValue as Record<string, unknown>)?.name as string || `#${recordId}`
                  : displayValue || `#${recordId}`}
              </>
            )}
          </Title>
          {!isReadOnly && (
          <Space size={6} style={{ marginLeft: 'auto' }}>
            <Button icon={<SaveOutlined />} type="primary" onClick={onSave} loading={saving}>
              Simpan
            </Button>
            <Button
              variant="solid"
              color="danger"
              icon={<CloseOutlined />}
              loading={discarding}
              onClick={() => { setDiscarding(true); navigate(`${basePath}`); }}
            >
              Batal
            </Button>
          </Space>
          )}
        </div>

        {/* Row 3: Action buttons | Stepper (sticky on scroll) */}
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            background: '#f0f2f5',
            padding: '8px 0 0',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Space size={4}>
            {actionButtons.map((btn) => (
              <Button
                key={btn.label}
                variant="solid"
                color={btn.color as 'green' | 'primary'}
                icon={ICON_MAP[btn.icon as keyof typeof ICON_MAP]}
                loading={actionLoading === btn.action}
                onClick={() => handleAction(btn)}
              >
                {btn.label}
              </Button>
            ))}
          </Space>
          {stepperSteps.length > 0 && (
            <div style={{ flex: 1, maxWidth: 480, marginLeft: 'auto' }}>
              <Steps
                current={currentStep}
                items={stepperSteps}
                size="small"
              />
            </div>
          )}
        </div>
      </div>
      )}
      {/* /sticky header */}

      {/* ═══ FORM CARD (hidden saat print preview) ═══ */}
      {!printPreviewHtml && (
      <Card
        styles={{
          header: {
            borderBottom: '1px solid #e8e8e8',
            padding: '8px 12px',
            minHeight: 44,
          },
          body: { padding: 16 },
        }}
        title={
          <Space size={6}>
            <InboxOutlined style={{ fontSize: 13, color: '#666' }} />
            <span>Data Terkait {config.verbose_name}</span>
          </Space>
        }
        extra={
          smartButtons.length > 0 && (
            <Space size={6}>
              {smartButtons.map((btn: { label: string; count?: number; model?: string; color?: string; icon?: string }) => {
                const autoCount = (recordData as Record<string, unknown>)?._smart_button_counts as Record<string, number> | undefined;
                const actualCount = btn.model && autoCount?.[btn.model] !== undefined ? autoCount[btn.model] : btn.count;
                return (
                  <SmartButton
                    key={btn.label}
                    icon={ICON_MAP[btn.icon || ''] || <FileTextOutlined />}
                    count={actualCount ?? 0}
                    label={btn.label}
                    color='#8c8c8c'
                    onClick={() => handleSmartButtonClick(btn)}
                  />
                );
              })}
            </Space>
          )
        }
      >
        {headerTabsList.length > 0 ? (
          <Tabs items={headerTabs} />
        ) : (
        <Form form={form} layout="vertical" initialValues={initialValues} onValuesChange={handleFormChange} key={`${apiModelName}-${recordId || 'new'}-${loadKey}`}>
          <Row gutter={16}>
            <Col span={8}>
              {col1.map(([key, field]) => {
                if (currentStatus && Array.isArray((field as any)?.hidden_statuses)
                    && (field as any).hidden_statuses.includes(currentStatus)) return null;
                const fieldRules = config?.field_config_rules?.[key];
                if (fieldRules?.hide_when) {
                  const shouldHide = Object.entries(fieldRules.hide_when).some(
                    ([wf, val]) => form.getFieldValue(wf) === val,
                  );
                  if (shouldHide) return null;
                }
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key))}</div>;
              })}
            </Col>
            <Col span={8}>
              {col2.map(([key, field]) => {
                if (currentStatus && Array.isArray((field as any)?.hidden_statuses)
                    && (field as any).hidden_statuses.includes(currentStatus)) return null;
                const fieldRules = config?.field_config_rules?.[key];
                if (fieldRules?.hide_when) {
                  const shouldHide = Object.entries(fieldRules.hide_when).some(
                    ([wf, val]) => form.getFieldValue(wf) === val,
                  );
                  if (shouldHide) return null;
                }
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key))}</div>;
              })}
            </Col>
            <Col span={8}>
              {col3.map(([key, field]) => {
                if (currentStatus && Array.isArray((field as any)?.hidden_statuses)
                    && (field as any).hidden_statuses.includes(currentStatus)) return null;
                const fieldRules = config?.field_config_rules?.[key];
                if (fieldRules?.hide_when) {
                  const shouldHide = Object.entries(fieldRules.hide_when).some(
                    ([wf, val]) => form.getFieldValue(wf) === val,
                  );
                  if (shouldHide) return null;
                }
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key))}</div>;
              })}
            </Col>
          </Row>
        </Form>
        )}
      </Card>
      )}

      {/* ═══ NOTEBOOK CARD — only for models with line items ═══ */}
      {!printPreviewHtml && notebookTabs.length > 0 && (
      <Card
        ref={notebookRef}
        styles={{
          body: { padding: 16 },
        }}
      >
        <Tabs
          activeKey={notebookTabs.some((t) => t.key === activeNotebookKey) ? activeNotebookKey : notebookTabs[0]?.key}
          onChange={(key) => setActiveNotebookKey(key)}
          items={notebookTabs}
        />
      </Card>
      )}

      {/* ═══ CHATTER ═══ */}
      {!printPreviewHtml && recordId && !isNew && (
        <Chatter
          key={chatterKey}
          modelName={apiModelName}
          recordId={Number(recordId)}
          fields={config.fields}
        />
      )}

      {/* ═══ PRINT PREVIEW ═══ */}
      {printPreviewHtml && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display:'flex', gap:8, marginBottom:12 }}>
            <Button onClick={() => { setPrintPreviewHtml(null); setPrintPdfUrl(null); }}>
              ← Back to Form
            </Button>
            <Button type="primary" onClick={() => printFrameRef.current?.contentWindow?.print()}>
              🖨 Print
            </Button>
            <Button
              onClick={async () => {
                try {
                  const token = localStorage.getItem('access_token');
                  const url = printPdfUrl;
                  if (!url) { message.error('PDF URL not available'); return; }
                  const resp = await fetch(url, {
                    headers: { 'Authorization': `Bearer ${token}` },
                  });
                  const blob = await resp.blob();
                  const blobUrl = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = blobUrl;
                  a.download = 'document.pdf';
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(blobUrl);
                } catch (e) {
                  message.error('Failed to download PDF');
                }
              }}
            >
              ⬇ Download PDF
            </Button>
          </div>
          <iframe
            ref={printFrameRef}
            srcDoc={printPreviewHtml}
            style={{ flex: 1, border:'1px solid #d9d9d9', borderRadius:6, minHeight: 0 }}
          />
        </div>
      )}

      {/* ═══ QUICK VIEW MODAL ═══ */}
      <QuickViewModal
        visible={!!quickView}
        modelName={quickView?.modelName || ''}
        recordId={quickView?.recordId || 0}
        onClose={() => setQuickView(null)}
        onOpenFullForm={quickView ? (() => {
          const urlName = apiToUrlName(quickView.modelName);
          if (urlName) {
            navigate(`/${urlName}/${quickView.recordId}`);
          }
        }) : undefined}
      />

      {/* ═══ ACTION WIZARD — mode + line selection ── */}
      {actionWizardBtn && (
        <GenericWizardModal
          visible={actionWizardVisible}
          config={actionWizardBtn.wizard as any}
          items={wizardItems}
          columnLabels={wizardColumnLabels}
          onConfirm={handleWizardConfirm}
          onFetchTable={handleFetchWizardTable}
          onCancel={() => { setActionWizardVisible(false); setActionWizardBtn(null); }}
        />
      )}

      {/* ═══ SMART BUTTON WIZARD — pilih record anak ═══ */}
      <Modal
        title="Select Record"
        open={wizardVisible}
        onCancel={() => setWizardVisible(false)}
        footer={null}
        width={420}
      >
        <List
          dataSource={wizardData?.records || []}
          renderItem={(item) => {
            const st = item.status || '';
            const statusColors = config?.fields?.status?.colors as Record<string, string> | undefined;
            return (
              <List.Item
                key={item.id}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  setWizardVisible(false);
                  const urlName = apiToUrlName(wizardData?.model || '');
                  navigate(`/${urlName}/${item.id}?from=${apiModelName}&fromId=${recordId}`);
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <span style={{ fontWeight: 500 }}>{item.display_name}</span>
                  {st && (
                    <Tag color={statusColors?.[st] || 'default'} style={{ fontSize: 10, lineHeight: '16px' }}>
                      {st.toUpperCase()}
                    </Tag>
                  )}
                </div>
              </List.Item>
            );
          }}
        />
      </Modal>
    </div>
  );
}
