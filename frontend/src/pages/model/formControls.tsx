/**
 * ============================================================================
 * formControls.tsx — Kontrol Form & Komponen Bantu ModelFormPage
 * ============================================================================
 * File ini berisi komponen UI murni (pure, props-based) yang sebelumnya
 * tinggal di ModelFormPage.tsx (Blok A) dan TIDAK bergantung pada state
 * halaman sama sekali. Dipisah agar ModelFormPage tetap fokus pada
 * orchestration (state, efek, handler, render layout).
 *
 * Isi file:
 *  - M2O_PAGE_SIZE          : konstanta pagination dropdown many2one (25/halaman)
 *  - SmartButton            : tombol pintar dengan count + label + hover color
 *  - Many2OneSelect         : dropdown many2one — fetch opsi dari related model,
 *                             dukung domain filter (refetch saat header berubah)
 *  - Many2OneWithAutofill   : Many2OneSelect + autofill field lain saat pilih
 *  - renderField            : render satu Form.Item sesuai tipe field dari config
 *                             (boolean/selection/date/monetary/integer/percentage/
 *                             text/many2one/char + virtual read-only)
 *  - Many2OneCellEditor     : cell editor AG Grid (Ant Select + infinite scroll)
 *
 * ATURAN: file ini core frontend — WAJIB generik. Dilarang hardcode
 * model-specific logic (`if model_name === ...`) di sini.
 *
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST setelah modifikasi file ini (dulu ModelFormPage.tsx):
 * ----------------------------------------------------------------------------
 * 1. Form edit — setiap tipe field render benar:
 *    - boolean (Switch), date (DatePicker format dd-mm-yyyy), monetary/float
 *      (InputNumber format Rp id-ID + currency), integer, percentage (%), text
 *      (TextArea), char, selection (radio utk discount_method, dropdown utk
 *      lainnya), many2one (dropdown), virtual (read-only borderless).
 * 2. Many2OneSelect:
 *    - dropdown load opsi dari API (loading spinner saat fetch).
 *    - search/filter opsi by ketikan; pilih & clear (allowClear).
 *    - tombol "view details" (ikon link) muncul saat ada nilai → buka QuickView.
 *    - domain filter: di model dgn domain (mis. Lokasi by Gudang di GR/DO/
 *      stock_in/stock_out) — ganti gudang → dropdown lokasi ikut ter-filter.
 * 3. Many2OneWithAutofill: pilih product → field uom/name terisi otomatis;
 *    clear pilihan → field autofill ikut kosong.
 * 4. SmartButton (SummaryCard): count, label, hover warna berubah, klik navigasi.
 * 5. Many2OneCellEditor (edit cell di notebook AG Grid):
 *    - edit kolom many2one → dropdown terbuka & bisa ketik cari.
 *    - infinite scroll: scroll bawah → opsi halaman berikutnya termuat.
 *    - pilih opsi → nilai masuk cell (label benar, bukan ID mentah), autofill
 *      kolom terkait jalan, lalu summary recompute.
 * 6. Regresi umum: new record, save, cancel, prev/next record, dirty-warning
 *    saat pindah halaman tanpa save — semua tetap normal.
 * ============================================================================
 */
import { useEffect, useState, useMemo, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { Form, Input, Select, DatePicker, Switch, InputNumber, Space, Button, Radio, message } from 'antd';
import { LinkOutlined } from '@ant-design/icons';
import { modelApi, type ModelConfig } from '../../api/models';
import { DATE_FORMAT } from '../../utils/format';

const { TextArea } = Input;

// Many2one dropdown pagination: fetch bertahap 25 per halaman
export const M2O_PAGE_SIZE = 25;

// ─── Smart Button Component ────────────────
interface SmartBtnProps {
  icon: React.ReactNode;
  count: number | string;
  label: string;
  color: string;
  onClick?: () => void;
}

export function SmartButton({ icon, count, label, color, onClick }: SmartBtnProps) {
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
export function Many2OneSelect({ value, onChange, modelName, placeholder, currentModel, onQuickView, disabled, domain, form }: {
  value?: number; onChange?: (v: number | undefined) => void; modelName: string; placeholder?: string; currentModel?: string; onQuickView?: (id: number) => void; disabled?: boolean; domain?: Record<string, string>; form?: any; required?: boolean;
}) {
  const [options, setOptions] = useState<{ value: number; label: string }[]>([]);
  const [loading, setLoading] = useState(false);

  // Domain: nilai header field terkait (mis. domain={'warehouse_id': 'warehouse'} →
  // lokasi ikut ter-filter saat gudang diganti). Form.useWatch memicu re-render
  // tiap form berubah; domainKey hanya berubah kalau nilai header yang dipakai
  // domain benar-benar berganti.
  const domainFormValues = Form.useWatch([], form);
  const domainKey = useMemo(() => {
    if (!domain || !form) return '';
    const resolved: Record<string, string> = {};
    Object.entries(domain).forEach(([relatedField, headerField]) => {
      const v = form.getFieldValue(headerField);
      if (v != null) resolved[relatedField] = String(v);
    });
    return JSON.stringify(resolved);
  }, [domain, domainFormValues, form]);

  const fetchOptions = useCallback(() => {
    if (!modelName) return;
    setLoading(true);
    const params: Record<string, string> = {};
    if (currentModel) params.model_ref = currentModel;
    if (domain && form) {
      Object.entries(domain).forEach(([relatedField, headerField]) => {
        const v = form.getFieldValue(headerField);
        if (v != null) params[relatedField] = String(v);
      });
    }
    modelApi.listRecords(modelName, undefined, undefined, params)
      .then((response) => {
        const records = response.results;
        const opts = records.map((r) => ({
          value: r.id as number,
          // display_name bisa berupa fallback '#id' (mis. product tanpa code) —
          // pakai field name kalau ada supaya tampil nama, bukan ID
          label: (() => {
            const dn = r.display_name as string;
            if (dn && !String(dn).startsWith('#')) return dn;
            return (r.name as string) || dn || `#${r.id}`;
          })(),
        }));
        setOptions(opts);
      })
      .catch(() => {
        message.error(`Failed to load ${modelName}`);
      })
      .finally(() => setLoading(false));
  }, [modelName, currentModel, domain, form, domainKey]);

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
export function Many2OneWithAutofill({ value, onChange, field, apiModelName, onQuickView, disabled }: {
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
export function renderField(
  key: string,
  field: ModelConfig['fields'][string],
  initialValues: Record<string, unknown>,
  currentModel?: string,
  onQuickView?: (modelName: string, recordId: number) => void,
  disabled?: boolean,
  form?: any,
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
      <Form.Item label={label} name={key} rules={required ? [{ required: true, message: `${label} wajib diisi` }] : []} extra={field.help_text ? <span style={{ fontSize: 12, fontStyle: 'italic', color: '#888' }}>{field.help_text}</span> : undefined}>
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
            domain={(field as any)?.domain}
            form={form}
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

export const Many2OneCellEditor = forwardRef<{ getValue: () => Record<string, unknown> | null }, Many2OneEditorProps>(
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
