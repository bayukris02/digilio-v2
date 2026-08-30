/**
 * ============================================================================
 * useModelFormActions — handler aksi & line item (ModelFormPage) — Part 1
 * ============================================================================
 * Menampung handler yang tadinya hidup di ModelFormPage:
 *  - goPrev / goNext          : navigasi ◀▶ antar record (dari recordIds)
 *  - handleNavigate           : navigasi ke record (smart button / breadcrumb)
 *  - handleSmartButtonClick   : smart button → buka record anak / parent / wizard
 *  - addLine / deleteLine     : tambah/hapus baris notebook (add_line_guard +
 *                               validasi required baris sebelumnya)
 *  - loadMoreMany2one         : infinite scroll options many2one di cell editor
 *
 * Plus dua validator murni yang di-export agar dipakai page (handleAction):
 *  - isLineFieldEmpty(val)        : cek nilai "kosong" utk validasi required
 *  - collectRequiredErrors(...)   : kumpulkan error field required per baris
 *
 * Semua dependency disuntik dari page via params — hook murni organisasi,
 * TIDAK ada state internal baru, TIDAK ada perubahan perilaku.
 *
 * ATURAN: core frontend — WAJIB generik (no `if model_name ===`).
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST:
 * 1. ◀▶ prev/next antar record — urutan & boundary (pertama/terakhir).
 * 2. Smart button: 1 anak → langsung navigasi; banyak anak → modal pilihan;
 *    cocok many2one → navigasi parent; tanpa data → toast "Belum ada data".
 * 3. addLine: guard add_line_guard (header wajib) & validasi baris sebelumnya
 *    (pesan "Lengkapi kolom wajib pada baris sebelumnya"); baris baru dapat
 *    default (boolean false / numerik 0 / many2one null / '').
 * 4. deleteLine: baris terhapus, nomor urut & summary recompute ikut.
 * 5. loadMoreMany2one: scroll bawah dropdown cell editor → halaman berikutnya
 *    termuat, opsi yang sudah dipilih baris lain disembunyikan (allow_duplicate
 *    mengecualikan).
 * ============================================================================
 */
import { useCallback } from 'react';
import { message } from 'antd';
import { modelApi, type ModelConfig } from '../../api/models';
import { apiToUrlName } from '../../config/urlModelMap';
import { M2O_PAGE_SIZE } from './formControls';

// ── Validator murni (dipakai juga oleh handleAction di page) ──

/** Check if a value is considered "empty" for required-field validation */
export function isLineFieldEmpty(val: unknown): boolean {
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
export function collectRequiredErrors(
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

export function useModelFormActions(params: {
  navigate: (to: string, opts?: { replace?: boolean }) => void;
  basePath: string;
  apiModelName: string;
  recordId?: string;
  currentIdx: number;
  recordIds: number[];
  config: ModelConfig | null;
  recordData: Record<string, unknown> | null;
  childConfigs: Record<string, ModelConfig>;
  lineItems: Record<string, Record<string, unknown>[]>;
  setLineItems: React.Dispatch<React.SetStateAction<Record<string, Record<string, unknown>[]>>>;
  setSummaryRevision: React.Dispatch<React.SetStateAction<number>>;
  setWizardData: React.Dispatch<React.SetStateAction<{ model: string; records: { id: number; display_name: string; status?: string }[] } | null>>;
  setWizardVisible: React.Dispatch<React.SetStateAction<boolean>>;
  form: any;
  setMany2oneOptions: React.Dispatch<React.SetStateAction<Record<string, { value: number; label: string; uom?: string }[]>>>;
  many2oneMeta: Record<string, { page: number; total: number; loading: boolean; params: Record<string, string> }>;
  setMany2oneMeta: React.Dispatch<React.SetStateAction<Record<string, { page: number; total: number; loading: boolean; params: Record<string, string> }>>>;
}) {
  const {
    navigate, basePath, apiModelName, recordId, currentIdx, recordIds,
    config, recordData, childConfigs, lineItems, setLineItems, setSummaryRevision,
    setWizardData, setWizardVisible, form, setMany2oneOptions,
    many2oneMeta, setMany2oneMeta,
  } = params;

  // ── Prev/Next navigation ──
  const goPrev = useCallback(() => {
    if (currentIdx > 0) navigate(`${basePath}/${recordIds[currentIdx - 1]}`);
  }, [currentIdx, recordIds, basePath, navigate]);

  const goNext = useCallback(() => {
    if (currentIdx < recordIds.length - 1) navigate(`${basePath}/${recordIds[currentIdx + 1]}`);
  }, [currentIdx, recordIds, basePath, navigate]);

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

  return { goPrev, goNext, handleNavigate, handleSmartButtonClick, addLine, deleteLine, loadMoreMany2one };
}
