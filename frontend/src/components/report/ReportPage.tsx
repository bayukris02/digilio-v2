import { useState, type ReactNode } from 'react';
import { Typography, Space, Button, Card, Row, Col, Table, Input, Select, DatePicker, Switch, ConfigProvider } from 'antd';
import { ReloadOutlined, DownloadOutlined, FilterOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
import type { Dayjs } from 'dayjs';
import { DATE_FORMAT } from '../../utils/format';
import { exportXlsx, numCell } from '../../utils/exportExcel';
import { fmtDateTime, fmtReportDate } from '../../utils/reportFormat';
import type {
  ReportBooleanFilter,
  ReportColumn,
  ReportDateFilter,
  ReportDateRangeFilter,
  ReportExportConfig,
  ReportFilter,
  ReportPeriodFilter,
  ReportPreset,
  ReportSelectFilter,
  ReportSummaryCell,
  ReportTextFilter,
} from './types';

/**
 * Tampilan tabel bergaya lembar kerja (mirip Excel).
 * Aturan wajib: SATU baris data = SATU baris tabel. Teks TIDAK boleh membungkus
 * (`white-space: nowrap`) — kalau kolom lebih lebar dari layar, shell memunculkan
 * scrollbar horizontal (lihat `scroll={{ x: 'max-content' }}` di Table).
 * Semua aturan memakai prefix `.rpt-sheet` — tidak ada style per-halaman.
 */
const sheetCss = `
.rpt-sheet .ant-table-cell {
  white-space: nowrap !important;
  vertical-align: middle;
}
.rpt-sheet .ant-table-summary > tr > th,
.rpt-sheet .ant-table-summary > tr > td {
  background: #fafafa;
}
`;

/** Tombol Filter (oranye) — gaya seragam di semua report. */
const filterBtnStyle = { background: '#fa8c16', borderColor: '#fa8c16', color: '#fff' } as const;

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/**
 * STANDAR UI REPORT (metadriven) — lihat docs/report-ui-standard.md
 *
 * Struktur WAJIB setiap report:
 *   header  : judul + subtitle opsional + [filter place:'header'] [Export Excel] [Refresh]
 *             + "Data per: …" (italic, dari prop fetchedAt)
 *   card 1  : filter — grid 4 kolom (select/date/daterange/period/boolean/text)
 *   card 2  : tabel — kolom + baris Total, keduanya dari metadata halaman
 *
 * Halaman report HANYA mendefinisikan metadata: title, filters[], columns[],
 * summaryCells[], exportConfig, query (dataSource), fetchedAt. Layout, CSS,
 * loading, format tanggal, dan isi file Excel ditangani shell ini.
 */
export type ReportPageProps<T extends object> = {
  title: string;
  /** Baris kecil di bawah judul: ringkasan filter yang sedang aktif. */
  subtitle?: ReactNode;
  /** Catatan tambahan di bawah subtitle (mis. warning data). */
  notice?: ReactNode;
  /**
   * Waktu data terakhir diambil dari server (epoch ms — mis. `query.dataUpdatedAt`).
   * Ditampilkan kecil di bawah tombol Refresh: "Data per: 11-Sep-2026 14:05".
   */
  fetchedAt?: number | null;
  filters?: ReportFilter[];
  loading: boolean;
  refreshing?: boolean;
  onRefresh: () => void;
  /** Metadata kolom — otomatis jadi kolom antd + header/isi export Excel. */
  columns: ReportColumn<T>[];
  dataSource: T[];
  /** Kunci baris: nama field (default 'id') atau fungsi (row, index). */
  rowKey?: string | ((row: T, index: number) => string);
  /** Baris Total ringkasan (opsional); kolomnya dihitung via colSpan. */
  summaryCells?: ReportSummaryCell[];
  /** Opsi export Excel — header & body diturunkan dari `columns`. */
  exportConfig?: ReportExportConfig;
  expandable?: TableProps<T>['expandable'];
  emptyText?: ReactNode;
  /** Lebar konten — default 90% dari area kerja (responsif); isi `maxWidth` hanya bila perlu batas atas. */
  maxWidth?: number;
};

const labelStyle = { fontSize: 12 } as const;
const labelRowStyle = { display: 'flex', alignItems: 'center', gap: 6, minHeight: 22 } as const;
const controlRowStyle = { marginTop: 4 } as const;

/** Chip preset tanggal — ditampilkan sebaris dengan label filter-nya. */
function PresetChips({
  presets,
  activePreset,
  onClick,
}: {
  presets: ReportPreset[];
  activePreset?: string;
  onClick: (p: ReportPreset) => void;
}) {
  return (
    <>
      {presets.map((p) => (
        <Button
          key={p.key}
          size="small"
          type={activePreset === p.key ? 'primary' : 'default'}
          onClick={() => onClick(p)}
        >
          {p.label}
        </Button>
      ))}
    </>
  );
}

function FilterPresets({ filter }: { filter: ReportFilter }) {
  if (filter.type === 'date' && filter.presets?.length) {
    const p = filter.presets;
    return (
      <PresetChips
        presets={p}
        activePreset={filter.activePreset}
        onClick={(preset) => {
          filter.onPresetClick?.(preset);
          filter.onChange(preset.value() as Dayjs | null);
        }}
      />
    );
  }
  if (filter.type === 'daterange' && filter.presets?.length) {
    const p = filter.presets;
    return (
      <PresetChips
        presets={p}
        activePreset={filter.activePreset}
        onClick={(preset) => {
          filter.onPresetClick?.(preset);
          filter.onChange(preset.value() as [Dayjs | null, Dayjs | null] | null);
        }}
      />
    );
  }
  return null;
}

function FilterControl({
  filter,
  editingKey,
  setEditingKey,
}: {
  filter: ReportFilter;
  editingKey: string | null;
  setEditingKey: (k: string | null) => void;
}) {
  if (filter.type === 'select') {
    const f = filter as ReportSelectFilter;
    return (
      <Select
        size="small"
        style={{ width: '100%' }}
        allowClear={f.allowClear ?? !f.multiple}
        showSearch={f.showSearch || f.serverSearch}
        mode={f.multiple ? 'multiple' : undefined}
        optionFilterProp={f.serverSearch ? undefined : 'label'}
        filterOption={f.serverSearch ? false : undefined}
        placeholder={f.placeholder}
        value={f.value}
        options={f.options}
        loading={f.loading}
        notFoundContent={f.notFoundContent}
        onSearch={f.onSearch}
        onChange={(v, o) => f.onChange(v, o)}
      />
    );
  }

  if (filter.type === 'date') {
    const f = filter as ReportDateFilter;
    return (
      <DatePicker
        size="small"
        style={{ width: '100%' }}
        format={DATE_FORMAT}
        value={f.value}
        allowClear={f.allowClear ?? false}
        disabled={f.disabled}
        disabledDate={f.disabledDate}
        onChange={(d) => f.onChange(d as Dayjs | null)}
      />
    );
  }

  if (filter.type === 'daterange') {
    const f = filter as ReportDateRangeFilter;
    return (
      <RangePicker
        size="small"
        style={{ width: '100%' }}
        format={DATE_FORMAT}
        value={f.value}
        allowClear={f.allowClear ?? true}
        disabledDate={f.disabledDate}
        onChange={(dates) => f.onChange(dates as [Dayjs | null, Dayjs | null] | null)}
      />
    );
  }

  if (filter.type === 'period') {
    const f = filter as ReportPeriodFilter;
    const options = [
      ...f.options.map((o) => ({ value: o.key, label: o.label })),
      { value: 'custom', label: f.customLabel ?? 'Kustom…' },
    ];
    const picking = f.value === 'custom' && editingKey === f.key;
    const single = f.mode === 'date';
    const shown = f.value === 'custom' ? f.range : f.resolvedRange;
    const from = shown?.[0];
    const to = single ? from : shown?.[1];
    return (
      // Wrapper relative + info/picker absolute → tinggi sel tetap = tinggi Select,
      // jadi posisi kontrol tidak bergeser dan tetap sejajar tombol Export/Refresh.
      <div style={{ position: 'relative' }}>
        <Select
          size="small"
          style={{ width: '100%' }}
          value={f.value}
          options={options}
          onChange={(v) => {
            setEditingKey(v === 'custom' ? f.key : null);
            f.onChange({ key: v as string, range: v === 'custom' ? f.range : null });
          }}
        />
        {f.value !== 'custom' || !picking ? null : (
          <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: 4, width: '100%', zIndex: 10 }}>
            {single ? (
              <DatePicker
                size="small"
                style={{ width: '100%' }}
                format={DATE_FORMAT}
                value={f.range?.[0] ?? null}
                allowClear={false}
                disabledDate={f.disabledDate}
                onChange={(d) => {
                  f.onChange({ key: 'custom', range: d ? [d as Dayjs, null] : null });
                  if (d) setEditingKey(null);
                }}
              />
            ) : (
              <RangePicker
                size="small"
                style={{ width: '100%' }}
                format={DATE_FORMAT}
                value={f.range}
                allowClear={false}
                disabledDate={f.disabledDate}
                onChange={(dates) => {
                  const r = dates as [Dayjs | null, Dayjs | null] | null;
                  f.onChange({ key: 'custom', range: r });
                  if (r?.[0] && r?.[1]) setEditingKey(null);
                }}
              />
            )}
          </div>
        )}
        {/* Info rentang tanggal efektif — semua opsi (preset & kustom), italic */}
        {picking || !from || !to ? null : (
          <div
            onClick={f.value === 'custom' ? () => setEditingKey(f.key) : undefined}
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: 2,
              whiteSpace: 'nowrap',
              cursor: f.value === 'custom' ? 'pointer' : 'default',
            }}
            title={f.value === 'custom' ? 'Klik untuk ubah rentang tanggal' : undefined}
          >
            <Text type="secondary" style={{ ...labelStyle, fontStyle: 'italic' }}>
              {single
                ? `Per ${fmtReportDate(from.format('YYYY-MM-DD'))}`
                : `${fmtReportDate(from.format('YYYY-MM-DD'))} s/d ${fmtReportDate(to.format('YYYY-MM-DD'))}`}
            </Text>
          </div>
        )}
      </div>
    );
  }

  if (filter.type === 'boolean') {
    const f = filter as ReportBooleanFilter;
    return <Switch size="small" checked={f.value} onChange={f.onChange} />;
  }

  const f = filter as ReportTextFilter;
  return (
    <Input
      size="small"
      style={{ width: '100%' }}
      value={f.value}
      placeholder={f.placeholder}
      allowClear={f.allowClear ?? true}
      onChange={(e) => f.onChange(e.target.value)}
    />
  );
}

/** Metadata kolom → kolom antd (render menerima row). */
function toAntdColumns<T extends object>(columns: ReportColumn<T>[]): TableProps<T>['columns'] {
  return columns.map((c) => ({
    key: c.key,
    title: c.title,
    dataIndex: c.dataIndex,
    width: c.width,
    align: c.align,
    render: c.render ? (_: unknown, row: T) => c.render?.(row) : undefined,
  })) as TableProps<T>['columns'];
}

/** Nilai sel untuk export Excel — angka dibulatkan seperti tampilan. */
function exportCell<T extends object>(c: ReportColumn<T>, row: T): string | number {
  const raw = c.export && typeof c.export === 'object'
    ? c.export.value(row)
    : c.dataIndex
      ? (row as Record<string, unknown>)[c.dataIndex]
      : '';
  if (raw == null) return '';
  if (typeof raw === 'number') return numCell(raw);
  return String(raw);
}

export default function ReportPage<T extends object>({
  title,
  subtitle,
  notice,
  fetchedAt,
  filters,
  loading,
  refreshing,
  onRefresh,
  columns,
  dataSource,
  rowKey = 'id',
  summaryCells,
  exportConfig,
  expandable,
  emptyText,
  maxWidth,
}: ReportPageProps<T>) {
  const headerFilters = (filters ?? []).filter((f) => f.place === 'header');
  const cardFilters = (filters ?? []).filter((f) => f.place !== 'header');
  /** Key filter periode yang sedang dalam mode pilih tanggal (dropdown = 'custom'). */
  const [editingKey, setEditingKey] = useState<string | null>(null);
  /** Show/hide card filter — card tabel ikut naik saat disembunyikan. */
  const [showFilters, setShowFilters] = useState(true);

  /** Export Excel: header + isi diturunkan dari metadata kolom. */
  const onExport = () => {
    if (!exportConfig) return;
    const cols = columns.filter((c) => c.export !== false);
    exportXlsx({
      filename: exportConfig.filename(),
      sheetName: exportConfig.sheetName ?? title,
      rows: [
        [title],
        ...(exportConfig.meta ?? []),
        [],
        cols.map((c) => c.title),
        ...dataSource.map((row) => cols.map((c) => exportCell(c, row))),
      ],
      colWidths: cols.map((c) => (c.width ? Math.max(10, Math.round(c.width / 8)) : 20)),
    });
  };

  const summary = summaryCells?.length
    ? () => (
        <Table.Summary.Row>
          {summaryCells.map((c, i) => (
            <Table.Summary.Cell key={i} index={i} colSpan={c.colSpan ?? 1} align={c.align}>
              {c.value}
            </Table.Summary.Cell>
          ))}
        </Table.Summary.Row>
      )
    : undefined;

  return (
    <div style={{ padding: 16 }}>
      {/* Lebar 90% dari area kerja (responsif terhadap zoom/ukuran layar). */}
      <div style={{ width: '90%', margin: '0 auto', ...(maxWidth ? { maxWidth } : null) }}>
        {/* Header — judul sejajar dengan filter header + tombol aksi.
            marginBottom dilebihkan kalau ada filter header (info tanggal italic di bawahnya). */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: headerFilters.length || fetchedAt ? 30 : 12,
          }}
        >
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {title}
            </Title>
            {subtitle ? (
              <Text type="secondary" style={labelStyle}>
                {subtitle}
              </Text>
            ) : null}
            {notice}
          </div>
          <div style={{ position: 'relative' }}>
            <Space align="center">
              {headerFilters.map((f) => (
                <Space key={f.key} size={4} align="center">
                  <Text strong style={labelStyle}>
                    {f.label}:
                  </Text>
                  <div style={{ width: f.width ?? 200 }}>
                    <FilterControl filter={f} editingKey={editingKey} setEditingKey={setEditingKey} />
                  </div>
                </Space>
              ))}
              {exportConfig ? (
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={onExport}
                  disabled={!dataSource.length}
                >
                  Export Excel
                </Button>
              ) : null}
              <Button size="small" icon={<ReloadOutlined spin={refreshing} />} onClick={onRefresh} loading={refreshing}>
                Refresh
              </Button>
              {/* Toggle card filter: sembunyikan → card tabel otomatis naik. */}
              {cardFilters.length ? (
                <Button
                  size="small"
                  icon={<FilterOutlined />}
                  onClick={() => setShowFilters((v) => !v)}
                  style={filterBtnStyle}
                >
                  Filter
                </Button>
              ) : null}
            </Space>
            {/* Info waktu data diambil (db) — di bawah tombol Refresh, tidak menggeser posisi tombol */}
            {fetchedAt ? (
              <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 2, whiteSpace: 'nowrap' }}>
                <Text type="secondary" style={{ ...labelStyle, fontStyle: 'italic' }}>
                  Data per: {fmtDateTime(fetchedAt)}
                </Text>
              </div>
            ) : null}
          </div>
        </div>

        {/* Card 1 — Filter: grid 4 kolom (date range = 2 kolom). Bisa disembunyikan via tombol Filter. */}
        {cardFilters.length && showFilters ? (
          <Card size="small" style={{ marginBottom: 12 }}>
            <Row gutter={[12, 10]}>
              {cardFilters.map((f) => (
                <Col key={f.key} span={(f.cols ?? 1) * 6}>
                  <div style={labelRowStyle}>
                    <Text strong style={labelStyle}>
                      {f.label}:
                    </Text>
                    <FilterPresets filter={f} />
                  </div>
                  <div style={controlRowStyle}>
                    <FilterControl filter={f} editingKey={editingKey} setEditingKey={setEditingKey} />
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        ) : null}

        {/* Card 2 — Tabel gaya lembar kerja (mirip Excel): garis kisi penuh + teks membungkus.
            Semua gaya dari shell ini (token + .rpt-sheet), bukan per-halaman. */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small" styles={{ body: { padding: 8 } }}>
            <style>{sheetCss}</style>
            <ConfigProvider
              theme={{
                components: {
                  Table: {
                    cellPaddingBlockSM: 4,
                    cellPaddingInlineSM: 8,
                    headerBg: '#f2f2f2',
                    headerColor: '#1f1f1f',
                    headerSplitColor: 'transparent',
                    headerBorderRadius: 0,
                    borderColor: '#d9d9d9',
                  },
                },
              }}
            >
              <div className="rpt-sheet">
                <Table<T>
                  size="small"
                  bordered
                  rowKey={rowKey as TableProps<T>['rowKey']}
                  columns={toAntdColumns(columns)}
                  dataSource={dataSource}
                  pagination={false}
                  scroll={{ x: 'max-content' }}
                  summary={summary}
                  expandable={expandable}
                  locale={emptyText ? { emptyText } : undefined}
                />
              </div>
            </ConfigProvider>
          </Card>
        )}
      </div>
    </div>
  );
}
