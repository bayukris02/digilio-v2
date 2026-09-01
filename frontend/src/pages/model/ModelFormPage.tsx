import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Typography, Card, Row, Col, Form, Button, Space, Spin,
  message, Breadcrumb, Steps, Tabs, Tag, Modal, List, Dropdown,
} from 'antd';
import {
  SaveOutlined, CloseOutlined, ArrowLeftOutlined, ArrowRightOutlined,
  PlusOutlined, DeleteOutlined, FileTextOutlined, MailOutlined,
  MoreOutlined, InboxOutlined, CheckOutlined, PrinterOutlined,
  DownloadOutlined, SendOutlined, EditOutlined, CopyOutlined,
  StopOutlined, UndoOutlined, HolderOutlined, DownOutlined,
} from '@ant-design/icons';
import { modelApi, type ModelConfig } from '../../api/models';
import { parseDate, formatDate, formatLastUpdate } from '../../utils/format';
import { modelNameToApi, apiToUrlName } from '../../config/urlModelMap';
import Chatter from '../../components/Chatter';
import QuickViewModal from '../../components/QuickViewModal';
import GenericWizardModal from '../../components/GenericWizardModal';
import ProgressBar from '../../components/ProgressBar';
import { SmartButton, renderField, Many2OneCellEditor } from './formControls';
import { useUnsavedChangesGuard } from './useUnsavedChangesGuard';
import { useFormChangeHandler } from './useFormChangeHandler';
import { useModelFormActions, collectRequiredErrors } from './useModelFormActions';
import { buildTabItems as renderSectionsBuildTabItems, type TabConfig } from './renderSections';
import type { ColDef, ICellRendererParams } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';
import { RichSelectModule } from 'ag-grid-enterprise';

ModuleRegistry.registerModules([AllCommunityModule, RichSelectModule]);

const { Title } = Typography;

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
  // Re-fetch record setelah aksi backend return `_action_type: 'refresh'`
  // (mis. aksi yang mengubah/regenerate baris notebook — supaya grid ikut reload)
  const [reloadKey, setReloadKey] = useState(0);

  // ── confirm_onchange: track previous field values + revert state ──
  const prevFieldValuesRef = useRef<Record<string, unknown>>({});
  const isRevertingRef = useRef(false);

  const {
    dirtyFlag,
    setDirtyFlag,
    lastSnapshotRef,
    computeDirty,
    syncSaveSnapshot,
    skipBlockerRef,
  } = useUnsavedChangesGuard({ form, lineItems, recordData });

  /** Callback untuk Form.onValuesChange — deteksi dirty + field onchange */
  const handleFormChange = useFormChangeHandler({
    form, config, setLineItems, lineItems, setSummaryRevision, childConfigs,
    computeDirty, setDirtyFlag, lastSnapshotRef, prevFieldValuesRef, isRevertingRef,
  });

  // ── Fetch model config (once per model) ──
  useEffect(() => {
    if (!apiModelName) return;

    // Reset state from previous model (e.g. GR → PO via breadcrumb)
    setConfig(null);
    setRecordData(null);
    setLineItems({});
    lineItemsOwnerRef.current = null;
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
    // Snapshot ikut di-reset supaya watcher lineItems tidak salah deteksi
    // dirty saat pindah record (lineItems dikosongkan dulu sebelum load)
    syncSaveSnapshot({});
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
          // Reload paksa notebook: reset line items + owner ref supaya baris
          // di-rebuild dari record terbaru (dipakai aksi `_action_type: 'refresh'`
          // yang mengubah/regenerate baris notebook, mis. Hitung Depresiasi).
          // Dilakukan SINI (setelah data baru diterima) — bareng setRecordData
          // dalam satu batch, jadi effect notebook rebuild dari data fresh.
          setLineItems({});
          lineItemsOwnerRef.current = null;
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
  }, [apiModelName, config, recordId, isNew, form, reloadKey]);

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
        // Autofill adalah populasi programmatic (bukan perubahan user) —
        // sync snapshot supaya tidak memicu false-positive "Perubahan belum
        // disimpan" (nilai autofill bisa beda dari record tersimpan, mis.
        // code/bill_method dari vendor vs None di PO).
        syncSaveSnapshot();
      }).catch(() => {
        // silent fail — autofill is best-effort
      });
    });
  }, [config, recordData, isNew, form, syncSaveSnapshot]);

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
    // Akumulasi line items dari SEMUA tab dulu (hindari closure stale saat
    // multi-tab: pakai setLineItems sekali di akhir, bukan per tab)
    const pendingLines: Record<string, Record<string, unknown>[]> = {};
    // Re-init line items jika record berubah (navigasi ◀▶ / buka record lain):
    // tanpa ini guard `!lineItems[relation]` memblokir reload dan notebook
    // tetap menampilkan baris record sebelumnya.
    const ownerId = recordData?.id != null ? Number(recordData.id) : null;
    const needReload = recordData != null && lineItemsOwnerRef.current !== ownerId;
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
      if (needReload) {
        const src = recordData?.[tab.relation];
        pendingLines[tab.relation] = (Array.isArray(src) ? src : []).map(
          (item: Record<string, unknown>) => ({
            ...item,
            _key: `line_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          }),
        );
      } else if (recordData?.[tab.relation] && !lineItems[tab.relation]) {
        pendingLines[tab.relation] = (recordData[tab.relation] as Record<string, unknown>[]).map(
          (item: Record<string, unknown>) => ({
            ...item,
            _key: `line_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          }),
        );
      }
    }
    // Set semua tab sekaligus + sync snapshot dengan nilai FINAL-nya
    // (setState async, jadi kirim nilai langsung supaya watcher lineItems
    // tidak salah deteksi dirty pas load)
    if (Object.keys(pendingLines).length > 0) {
      const nextLines = needReload ? pendingLines : { ...lineItems, ...pendingLines };
      setLineItems(nextLines);
      lineItemsOwnerRef.current = ownerId;
      syncSaveSnapshot(nextLines);
    }
  }, [config, recordData, lineItems, syncSaveSnapshot]);

  // ── Domain refetch: saat field header berubah, refetch many2one options ──
  // Watch seluruh form (bukan hardcode 'vendor') agar domain seperti
  // domain={'warehouse': 'warehouse'} ikut ter-refresh saat gudang diganti.
  const headerFormValues = Form.useWatch([], form);
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
  }, [headerFormValues, config, childConfigs]);

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
  // Record id yang jadi sumber lineItems saat ini — dipakai untuk reload
  // notebook saat pindah record via ◀▶ (tanpa ini, lineItems tidak ter-reset
  // karena guard `!lineItems[relation]` memblokir re-init).
  const lineItemsOwnerRef = useRef<number | null>(null);

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
    const field = config?.fields?.[fieldKey];
    if (!field) return false;
    const fieldStatuses = (field as Record<string, unknown>)?.editable_statuses as string[] | undefined;
    if (fieldStatuses) {
      // [] = never editable (model tanpa status / field read-only permanen)
      return !fieldStatuses.includes(currentStatus ?? '');
    }
    if (!currentStatus) return false;
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
    // Helper: terapkan response sukses (normalisasi + set form + toast)
    const applyActionSuccess = (result: Record<string, unknown>) => {
      if (result.error) {
        message.error(result.error as string);
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
    };

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
      // Konfirmasi dialog: backend minta user pilih Lanjut/Tidak sebelum action dijalankan
      if (result._action_type === 'confirm' && result.confirm_message) {
        Modal.confirm({
          title: 'Konfirmasi',
          content: result.confirm_message as string,
          okText: 'Lanjut',
          cancelText: 'Tidak',
          onOk: async () => {
            const res2 = await modelApi.postAction(apiModelName, currentRecordId!, actionName, { confirmed: true });
            applyActionSuccess(res2);
          },
        });
        return;
      }

      // Refresh: backend sudah mengubah record (termasuk baris notebook) —
      // re-fetch record supaya form & grid ikut reload. Reset lineItems
      // dilakukan di fetch effect (setelah data terbaru diterima), bukan di
      // sini — kalau di-reset dulu, effect notebook sempat rebuild dari
      // record lama (kosong) dan refetch tidak reload lagi.
      if (result._action_type === 'refresh') {
        setReloadKey((prev) => prev + 1);
        if (result.message) {
          message.success(result.message as string);
        } else {
          message.success(`${actionName} completed`);
        }
        return;
      }

      applyActionSuccess(result);
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

  const { goPrev, goNext, handleNavigate, handleSmartButtonClick, addLine, deleteLine, loadMoreMany2one } = useModelFormActions({
    navigate, basePath, apiModelName, recordId, currentIdx, recordIds,
    config, recordData, childConfigs, lineItems, setLineItems, setSummaryRevision,
    setWizardData, setWizardVisible, form, setMany2oneOptions,
    many2oneMeta, setMany2oneMeta,
  });

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
      // Selection: colored Tag badge (only when colors defined) + dropdown editor
      if (field.type === 'selection') {
        col.cellEditor = 'agSelectCellEditor';
        col.cellEditorParams = {
          values: (field.options || []).map((o: { value: string }) => o.value),
        };
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

  // Model yang menonaktifkan create (_allow_create=false) — jangan tampilkan form kosong
  if (isNew && config?.allow_create === false) {
    return (
      <Card style={{ margin: 24, textAlign: 'center', padding: 40 }}>
        <Title level={4}>Tidak bisa membuat record baru</Title>
        <Typography.Text type="secondary">
          Data {config.verbose_name_plural.toLowerCase()} dibuat otomatis dari proses Input Penjualan.
        </Typography.Text>
      </Card>
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

  const buildTabItems = (tabs: TabConfig[]) => renderSectionsBuildTabItems({
    tabs, form, handleFormChange, initialValues, apiModelName, recordId, loadKey,
    config, currentStatus, setQuickView, isFieldDisabled, childConfigs, lineItems,
    setLineItems, columnFieldValues, isReadOnly, buildColumns, setAddingLine, addLine,
    setMany2oneOptions, setMany2oneMeta, setSummaryRevision, handleNavigate,
    summaryRevision, recordData: recordData ?? undefined,
  });

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
              icon={<ArrowLeftOutlined />}
              loading={discarding}
              onClick={() => { setDiscarding(true); navigate(`${basePath}`); }}
            >
              Kembali
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
            {actionButtons.map((btn) => {
              const children = btn.children as Record<string, unknown>[] | undefined;
              // Split button: children ada → tombol utama + panah dropdown (Odoo-style)
              if (children?.length) {
                return (
                  <Space.Compact key={btn.label}>
                    <Button
                      variant="solid"
                      color={btn.color as 'green' | 'primary'}
                      icon={ICON_MAP[btn.icon as keyof typeof ICON_MAP]}
                      loading={actionLoading === btn.action}
                      onClick={() => handleAction(btn)}
                    >
                      {btn.label}
                    </Button>
                    <Dropdown
                      trigger={['click']}
                      menu={{
                        items: children.map((child) => ({
                          key: child.label as string,
                          label: child.label as string,
                          onClick: () => handleAction(child),
                        })),
                      }}
                    >
                      <Button variant="solid" color={btn.color as 'green' | 'primary'} icon={<DownOutlined />} />
                    </Dropdown>
                  </Space.Compact>
                );
              }
              return (
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
              );
            })}
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
          <Tabs items={headerTabs} onChange={() => syncSaveSnapshot()} />
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key), form)}</div>;
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key), form)}</div>;
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
                return <div key={key}>{renderField(key, effectiveField as any, initialValues, apiModelName, (mn, rid) => setQuickView({ modelName: mn, recordId: rid }), isFieldDisabled(key), form)}</div>;
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
          recordId={recordId ? Number(recordId) : null}
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
