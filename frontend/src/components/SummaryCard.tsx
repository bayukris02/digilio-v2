import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { Card, Typography, InputNumber, Divider, Spin, Form } from 'antd';
import type { FormInstance } from 'antd';
import type { FieldConfig } from '../api/models';
import { modelApi } from '../api/models';

const { Text } = Typography;

interface SummaryConfig {
  columns?: Record<string, string>;
  subtotal?: string;
  inputs?: string[];
  lines?: string[];
  compute_deps?: string[];
  grand_total?: string;
  after_grand_total?: string[];
  child_details?: {
    label: string;
    data_key: string;
    model: string;
  };
}

interface SummaryCardProps {
  summary: Record<string, unknown>;
  lineItems: Record<string, unknown>[];
  fields: Record<string, FieldConfig>;
  form: FormInstance;
  modelName: string;
  readOnly?: boolean;
  relation?: string;
  recordId?: number;
  recordData?: Record<string, unknown>;
  onNavigate?: (modelName: string, recordId: number) => void;
  /** Callback dengan per-line computed data dari backend (_computed_o2m_lines) */
  onComputedLines?: (relation: string, lines: Record<string, unknown>[]) => void;
  /** Increment untuk memaksa recompute dari luar (misal setelah child compute) */
  revision?: number;
}

/** Format IDR currency */
function fmtIDR(val: number | undefined | null): string {
  if (val == null || isNaN(Number(val))) return 'Rp 0';
  return `Rp ${Number(val).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function SummaryCard({ summary: rawSummary, lineItems, fields, form, modelName, readOnly, relation, recordId, recordData, onNavigate, onComputedLines, revision = 0 }: SummaryCardProps) {
  const summary = rawSummary as unknown as SummaryConfig;

  // Skip render if no subtotal and no grand_total (columns-only mode)
  const hasCard = !!(summary.subtotal || summary.grand_total);

  // Local state for input fields (synced to form)
  const [rates, setRates] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    if (summary.inputs) {
      for (const name of summary.inputs) {
        initial[name] = Number(form.getFieldValue(name)) || 0;
      }
    }
    return initial;
  });

  // Computed results from backend API
  const [computed, setComputed] = useState<Record<string, number>>({});
  const [computing, setComputing] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Watch compute_deps field values supaya summary re-trigger saat header field berubah
  const computeDeps = summary.compute_deps || [];
  const allFormValues = Form.useWatch([], form);

  // Format line items for API payload
  const formattedLines = useMemo(() => {
    return (lineItems || []).map((item) => {
      const cleaned: Record<string, unknown> = {};
      Object.entries(item).forEach(([key, val]) => {
        if (key !== 'id') {
          // Keep _key so backend can return it in _computed_o2m_lines for matching
          cleaned[key] = typeof val === 'object' && val !== null && 'id' in val
            ? { id: (val as Record<string, unknown>).id }
            : val;
        }
      });
      return cleaned;
    });
  }, [lineItems]);

  // Ref to avoid circular trigger: onComputedLines → lineItems → formattedLines → triggerCompute → compute → onComputedLines
  const formattedLinesRef = useRef(formattedLines);
  formattedLinesRef.current = formattedLines;

  // Call compute API with debounce
  const triggerCompute = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setComputing(true);
      try {
        const payload: Record<string, unknown> = {
          ...rates,
          [relation || 'order_lines']: formattedLinesRef.current,
        };
        // Kirim record ID agar compute endpoint bisa load dari DB
        // (diperlukan untuk computed fields yang query cross-model seperti dp_amount)
        if (recordId != null) {
          payload.id = recordId;
        }
        // Don't send computed fields as inputs
        // Note: fields in BOTH lines AND inputs are editable — keep their values
        const inputSet = new Set(summary.inputs || []);
        if (summary.subtotal) payload[summary.subtotal] = undefined;
        if (summary.grand_total) payload[summary.grand_total] = undefined;
        if (summary.lines) {
          for (const name of summary.lines) {
            // Jangan clear field yang juga di inputs (editable, bukan computed)
            if (!inputSet.has(name)) {
              payload[name] = undefined;
            }
          }
        }
        if (summary.after_grand_total) {
          for (const name of summary.after_grand_total) {
            payload[name] = undefined;
          }
        }
        // Include compute_deps from form (header fields yang dibutuhkan compute)
        if (summary.compute_deps) {
          for (const dep of summary.compute_deps) {
            const val = form.getFieldValue(dep);
            if (val !== undefined) payload[dep] = val;
          }
        }
        const result = await modelApi.compute(modelName, payload);
        setComputed(result as Record<string, number>);

        // Forward per-line computed data ke parent untuk update line items table
        const computedLines = (result as Record<string, unknown>)?._computed_o2m_lines as
          Record<string, Record<string, unknown>[]> | undefined;
        if (computedLines && relation && onComputedLines) {
          // computedLines: { order_lines: [{_key, total, discount_amount, ...}, ...] }
          for (const [rel, lines] of Object.entries(computedLines)) {
            onComputedLines(rel, lines);
          }
        }
      } catch {
        // Silently fail
      } finally {
        setComputing(false);
      }
    }, 300);
  }, [rates, modelName, summary, allFormValues, revision]);

  // Trigger compute whenever rates or lines change
  useEffect(() => {
    triggerCompute();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [triggerCompute]);

  // Re-sync from form when field values change externally
  useEffect(() => {
    if (summary.inputs) {
      for (const name of summary.inputs) {
        const val = Number(form.getFieldValue(name)) || 0;
        setRates((prev) => (prev[name] !== val ? { ...prev, [name]: val } : prev));
      }
    }
  }, [form, summary.inputs]);

  const handleRateChange = (fieldName: string, value: number | null) => {
    const v = value ?? 0;
    setRates((prev) => ({ ...prev, [fieldName]: v }));
    form.setFieldsValue({ [fieldName]: v });
  };

  const subtotal = summary.subtotal ? (computed[summary.subtotal] ?? 0) : 0;
  const grandTotal = summary.grand_total ? (computed[summary.grand_total] ?? 0) : 0;
  const fieldCfg = (name: string) => fields[name];

  // ── Build combined ordered display list (lines + inputs, interleaved) ──
  // Jika field ada di BOTH lines dan inputs → render sebagai input (editable) di posisi lines
  const displayItems = useMemo(() => {
    const inputSet = new Set(summary.inputs || []);
    const items: { fieldName: string; isInput: boolean }[] = [];

    // Gunakan lines untuk posisi — jika juga di inputs, render sebagai input
    (summary.lines || []).forEach((fn: string) => {
      items.push({ fieldName: fn, isInput: inputSet.has(fn) });
    });

    // Tambah input yang tidak tercantum di lines (ditempel di akhir)
    (summary.inputs || []).forEach((fn: string) => {
      if (!items.some(i => i.fieldName === fn)) {
        items.push({ fieldName: fn, isInput: true });
      }
    });
    return items;
  }, [summary.lines, summary.inputs]);

  // ── Early return: no card needed if no subtotal/grand_total ──
  if (!hasCard) return null;

  const hasLines = !!(summary.lines && summary.lines.length > 0);
  const hasInputs = !!(summary.inputs && summary.inputs.length > 0);
  const hasDisplayItems = displayItems.length > 0;
  const hasAfterGrandTotal = !!(summary.after_grand_total && summary.after_grand_total.length > 0);

  return (
    <Card
      size="small"
      style={{ width: '50%', marginLeft: 'auto' }}
      styles={{
        header: {
          borderBottom: '1px solid #e8e8e8',
          padding: '6px 12px',
          minHeight: 36,
          fontSize: 13,
        },
        body: { padding: '8px 12px' },
      }}
      title={
        <span style={{ fontSize: 13 }}>
          Summary {computing && <Spin size="small" style={{ marginLeft: 6 }} />}
        </span>
      }
    >
      {/* Subtotal */}
      {summary.subtotal && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <Text style={{ fontSize: 12, minWidth: 80 }}>
            {fieldCfg(summary.subtotal)?.label || 'Subtotal'}
          </Text>
          <Text strong style={{ fontSize: 12 }}>
            {fmtIDR(subtotal)}
          </Text>
        </div>
      )}

      {/* Display items — interleaved: lines (read-only) + inputs (editable) in config order */}
      {hasDisplayItems && displayItems.map(({ fieldName, isInput }) => {
        const cfg = fieldCfg(fieldName);
        if (!cfg) return null;
        if (isInput) {
          // Editable input (InputNumber)
          return (
            <div key={fieldName} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <Text style={{ fontSize: 12, minWidth: 80 }}>{cfg.label || fieldName}</Text>
              <InputNumber
                size="small"
                disabled={readOnly}
                min={0}
                max={100}
                style={{ width: 100 }}
                value={rates[fieldName] ?? 0}
                onChange={(v) => handleRateChange(fieldName, v)}
                formatter={(v) => v != null ? `${v}` : ''}
                parser={(v) => parseFloat(v || '0')}
              />
            </div>
          );
        }
        // Read-only computed display
        const val = computed[fieldName] ?? 0;
        const isNegative = Number(val) < 0;
        return (
          <div
            key={fieldName}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
              color: isNegative ? '#ff4d4f' : undefined,
            }}
          >
            <Text style={{ fontSize: 12, minWidth: 80, color: isNegative ? '#ff4d4f' : undefined }}>
              {cfg?.label || fieldName}
            </Text>
            <Text style={{ fontSize: 12, color: isNegative ? '#ff4d4f' : undefined }}>
              {fmtIDR(val)}
            </Text>
          </div>
        );
      })}

      {/* Divider before grand total — only if something above it */}
      {(summary.subtotal || hasDisplayItems) && summary.grand_total && (
        <Divider style={{ margin: '6px 0' }} />
      )}

      {/* Grand Total */}
      {summary.grand_total && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong style={{ fontSize: 13, minWidth: 80 }}>
            {fieldCfg(summary.grand_total)?.label || 'Grand Total'}
          </Text>
          <Text strong style={{ fontSize: 14, color: '#1677ff' }}>
            {fmtIDR(grandTotal)}
          </Text>
        </div>
      )}

      {/* Child Details — daftar bill downstream (DP, Regular) yg bisa diklik */}
      {summary.child_details && recordData && (
        <>
          <Divider style={{ margin: '6px 0' }} />
          {(recordData[summary.child_details.data_key] as Array<{id: number; label: string; ref: string; amount: number}>)?.map((item) => (
            <div
              key={item.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 4,
                cursor: 'pointer',
              }}
              onClick={() => onNavigate?.(summary.child_details!.model, item.id)}
            >
              <Text style={{ fontSize: 12, minWidth: 80 }}>
                {item.label}{' '}
                <Typography.Link style={{ fontSize: 12 }}>{item.ref}</Typography.Link>
              </Text>
              <Text style={{ fontSize: 12 }}>
                {fmtIDR(item.amount)}
              </Text>
            </div>
          ))}
        </>
      )}

      {/* After Grand Total — fields yang muncul di bawah grand total (due_amount) */}
      {hasAfterGrandTotal && <Divider style={{ margin: '6px 0' }} />}
      {hasAfterGrandTotal && summary.after_grand_total!.map((fieldName) => {
        const cfg = fieldCfg(fieldName);
        // Pakai computed (dari compute API) dulu, fallback ke recordData (initial render)
        const val = computed[fieldName] ?? (recordData as Record<string, unknown>)?.[fieldName] ?? 0;
        // Sembunyikan setelah_grand_total hanya jika ada child_details config tapi datanya kosong
        const childItems = summary.child_details
          ? ((recordData as Record<string, unknown>)?.[summary.child_details.data_key] as Array<unknown>)
          : undefined;
        if (summary.child_details && (!childItems || childItems.length === 0)) return null;
        return (
          <div
            key={fieldName}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
            }}
          >
            <Text strong style={{ fontSize: 12, minWidth: 80 }}>
              {cfg?.label || fieldName}
            </Text>
            <Text strong style={{ fontSize: 12 }}>
              {fmtIDR(val)}
            </Text>
          </div>
        );
      })}
    </Card>
  );
}
