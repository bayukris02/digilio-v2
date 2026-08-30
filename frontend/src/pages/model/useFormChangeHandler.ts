/**
 * ============================================================================
 * useFormChangeHandler — handler Form.onValuesChange (ModelFormPage)
 * ============================================================================
 * Menampung callback `handleFormChange` yang tadinya hidup di ModelFormPage:
 * deteksi dirty + efek deklaratif saat field berubah:
 *  - onchange           : reset target field saat source berubah (model config)
 *  - line_onchange      : reset field di SEMUA baris notebook
 *  - confirm_onchange   : konfirmasi modal sebelum mereset line items
 *  - populate_lines     : isi line items dari one2many record terkait (template)
 *
 * Parameter hook adalah dependency yang dipakai callback — semua disuntik
 * dari page (state/setter/ref). Hook murni organisasi: TIDAK ada perubahan
 * perilaku, TIDAK ada state internal baru.
 *
 * ATURAN: core frontend — WAJIB generik (no `if model_name ===`).
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST:
 * 1. Field dengan `onchange` (mis. ubah Tipe Dokumen/status) → field target
 *    ikut ter-reset ke default.
 * 2. Field dengan `line_onchange` (mis. discount_method di PO) → semua baris
 *    notebook ikut ter-reset.
 * 3. Field dengan `confirm_onchange` → saat ada line items: muncul modal
 *    konfirmasi; "OK" → baris di-reset; "Batal" → nilai balik ke semula.
 * 4. Field dengan `populate_lines` (mis. pilih Order Template) → line items
 *    terisi dari template; kalau sudah ada baris → konfirmasi dulu.
 * 5. Semua perubahan di atas tetap memicu indikator "Perubahan belum disimpan".
 * ============================================================================
 */
import { useCallback } from 'react';
import { Modal, message } from 'antd';
import type { FormInstance } from 'antd';
import { modelApi, type ModelConfig } from '../../api/models';

export function useFormChangeHandler(params: {
  form: FormInstance;
  config: ModelConfig | null;
  setLineItems: React.Dispatch<React.SetStateAction<Record<string, Record<string, unknown>[]>>>;
  lineItems: Record<string, Record<string, unknown>[]>;
  setSummaryRevision: React.Dispatch<React.SetStateAction<number>>;
  childConfigs: Record<string, ModelConfig>;
  computeDirty: () => boolean;
  setDirtyFlag: React.Dispatch<React.SetStateAction<boolean>>;
  lastSnapshotRef: React.MutableRefObject<string>;
  prevFieldValuesRef: React.MutableRefObject<Record<string, unknown>>;
  isRevertingRef: React.MutableRefObject<boolean>;
}) {
  const { form, config, setLineItems, lineItems, setSummaryRevision, childConfigs, computeDirty, setDirtyFlag, lastSnapshotRef, prevFieldValuesRef, isRevertingRef } = params;

  return useCallback((changedValues?: Record<string, unknown>) => {
    if (lastSnapshotRef.current) {
      setDirtyFlag(computeDirty());
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
      // populate_lines: saat many2one berubah → isi line items dari one2many
      // record terkait (template & sejenisnya). Konfigurasi generic dari backend:
      // config.field_config_rules[field].populate_lines = {target, source, mapping}
      Object.entries(changedValues).forEach(([fieldName, newValue]) => {
        const populate = config?.field_config_rules?.[fieldName]?.populate_lines as
          | { target?: string; source?: string; mapping?: Record<string, string> }
          | undefined;
        if (!populate?.target || !populate.source || !newValue || isRevertingRef.current) return;
        const fieldCfg = config.fields?.[fieldName] as { relation?: string } | undefined;
        const rel = fieldCfg?.relation;
        if (!rel) return;
        const target = populate.target;
        const source = populate.source;
        const mapping = populate.mapping || {};
        const doPopulate = () => {
          modelApi.getRecord(rel, Number(newValue)).then((record: unknown) => {
            const rec = record as Record<string, unknown>;
            const srcLines = Array.isArray(rec[source]) ? (rec[source] as Record<string, unknown>[]) : [];
            const childCfg = childConfigs[target];
            const items = srcLines.map((src) => {
              const item: Record<string, unknown> = {
                _key: `line_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
              };
              Object.entries(mapping).forEach(([srcField, tgtField]) => {
                item[tgtField] = src[srcField];
              });
              // default untuk field child yang tidak di-mapping (numerik → 0, boolean → false)
              if (childCfg) {
                Object.entries(childCfg.fields).forEach(([key, field]) => {
                  if (key === 'id' || key === '_key' || key in item) return;
                  const ft = (field as { type?: string }).type;
                  if (['float', 'monetary', 'integer'].includes(ft || '')) item[key] = 0;
                  else if (ft === 'boolean') item[key] = false;
                });
              }
              return item;
            });
            setLineItems((prev) => ({ ...prev, [target]: items }));
            setSummaryRevision((v) => v + 1);
            prevFieldValuesRef.current = { ...prevFieldValuesRef.current, [fieldName]: newValue };
            if (srcLines.length > 0) {
              message.success(`Baris diisi dari template: ${srcLines.length} item`);
            }
          }).catch(() => message.error('Gagal memuat data template'));
        };
        // Kalau sudah ada line items → konfirmasi dulu (mencegah data tertimpa)
        const existing = lineItems[target] || [];
        const hasReal = existing.filter((item) => !item._isAddButton).length > 0;
        if (hasReal) {
          Modal.confirm({
            title: 'Konfirmasi Perubahan',
            content: 'Mengganti template akan menimpa baris pesanan saat ini. Lanjutkan?',
            onOk: doPopulate,
            onCancel: () => {
              isRevertingRef.current = true;
              form.setFieldValue(fieldName, undefined);
              isRevertingRef.current = false;
            },
          });
        } else {
          doPopulate();
        }
      });
    }
  }, [form, config, setLineItems, lineItems, setSummaryRevision, computeDirty, childConfigs]);
}
