import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Tag, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { stockLedgerApi } from '../../api/report';
import type { StockLedgerRow } from '../../api/report';
import { modelApi } from '../../api/models';
import { fmtQty, fmtReportDate } from '../../utils/reportFormat';
import ReportPage from '../../components/report/ReportPage';
import type { ReportColumn, ReportFilter, ReportPreset, ReportSummaryCell } from '../../components/report/types';

const { Text } = Typography;

/** Warna label per jenis sumber pergerakan (konsisten dgn Stock Card). */
const labelColor: Record<string, string> = {
  'Penerimaan (GR)': 'green',
  'Pengiriman (DO)': 'red',
  'Transfer Masuk': 'cyan',
  'Transfer Keluar': 'volcano',
  Penyesuaian: 'purple',
};

/** Blok tanggal di masa depan (stok masa depan tidak mungkin). */
const notFuture = (d: Dayjs) => d.isAfter(dayjs().endOf('day'));

/** Preset periode — dibaca ulang saat diklik supaya tanggal relatif tetap segar. */
const PERIOD_PRESETS: ReportPreset[] = [
  { key: 'today', label: 'Hari Ini', value: () => [dayjs().startOf('day'), dayjs().endOf('day')] },
  {
    key: 'last_7_days',
    label: '7 Hari',
    value: () => [dayjs().subtract(6, 'day').startOf('day'), dayjs().endOf('day')],
  },
  {
    key: 'this_month',
    label: 'Bulan Ini',
    value: () => [dayjs().startOf('month'), dayjs().endOf('month')],
  },
  { key: 'all', label: 'Semua', value: () => null },
];

/**
 * Stock Ledger — daftar mentah pergerakan stok (+masuk / −keluar) per produk & lokasi.
 * Route: /inventory.stock_ledger
 *
 * Layout/UI memakai standar <ReportPage /> (2 card: filter 4 kolom + tabel);
 * halaman ini hanya mendefinisikan metadata filter, kolom, dan export.
 */
export default function StockLedgerPage() {
  const [period, setPeriod] = useState('all');
  const [customRange, setCustomRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [warehouseIds, setWarehouseIds] = useState<number[]>([]);
  const [sourceModels, setSourceModels] = useState<string[]>([]);
  const [productSearch, setProductSearch] = useState('');

  /** Periode efektif: preset periode, atau range manual saat "Kustom". */
  const range = useMemo(() => {
    if (period === 'custom') return customRange;
    const preset = PERIOD_PRESETS.find((p) => p.key === period);
    return preset ? (preset.value() as [Dayjs | null, Dayjs | null] | null) : null;
  }, [period, customRange]);

  // ── Sumber filter ──
  const warehousesQuery = useQuery({
    queryKey: ['model-records', 'inventory.warehouse'],
    queryFn: () => modelApi.listRecords('inventory.warehouse', 1, 100),
    staleTime: 60 * 1000,
  });
  const warehouseOptions = useMemo(
    () =>
      (warehousesQuery.data?.results ?? []).map((r) => ({
        value: Number(r.id),
        label: String((r as { display_name?: unknown }).display_name ?? r.name ?? `#${r.id}`),
      })),
    [warehousesQuery.data],
  );

  const productsQuery = useQuery({
    queryKey: ['stock-ledger-products', productSearch],
    queryFn: () =>
      modelApi.listRecords('inventory.product', 1, 50, productSearch ? { search: productSearch } : undefined),
    staleTime: 30 * 1000,
    enabled: productSearch.length > 0,
  });
  const productOptions = useMemo(() => {
    const fetched = (productsQuery.data?.results ?? []).map((r) => ({
      value: Number(r.id),
      label: String((r as { display_name?: unknown }).display_name ?? r.name ?? `#${r.id}`),
    }));
    if (productLabel && !fetched.some((o) => o.value === productId)) {
      fetched.unshift({ value: productId as number, label: productLabel });
    }
    return fetched;
  }, [productsQuery.data, productLabel, productId]);

  const warehousesJoined = warehouseIds.length ? warehouseIds.join(',') : '';
  const warehouseLabel =
    warehouseIds.length === 0
      ? 'Semua Gudang'
      : warehouseOptions.filter((o) => warehouseIds.includes(o.value)).map((o) => o.label).join(', ');
  const sourcesJoined = sourceModels.length ? sourceModels.join(',') : '';

  const periodText =
    range?.[0] && range?.[1]
      ? `${fmtReportDate(range[0].format('YYYY-MM-DD'))} s/d ${fmtReportDate(range[1].format('YYYY-MM-DD'))}`
      : 'Semua periode';

  const query = useQuery({
    queryKey: [
      'stock-ledger',
      productId ?? '',
      warehousesJoined,
      sourcesJoined,
      range?.[0]?.format('YYYY-MM-DD') ?? '',
      range?.[1]?.format('YYYY-MM-DD') ?? '',
    ],
    queryFn: () =>
      stockLedgerApi.get({
        product: productId,
        warehouses: warehousesJoined || undefined,
        sources: sourcesJoined || undefined,
        date_from: range?.[0]?.format('YYYY-MM-DD'),
        date_to: range?.[1]?.format('YYYY-MM-DD'),
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;

  const onRefresh = useCallback(() => {
    query.refetch();
  }, [query]);

  if (query.isError) {
    message.error('Gagal memuat laporan: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  const rows = query.data?.rows ?? [];
  const totals = query.data?.totals;
  const sourceOptions = useMemo(
    () => (query.data?.sources ?? []).map((s) => ({ value: s.value, label: s.label })),
    [query.data],
  );

  const columns: ReportColumn<StockLedgerRow>[] = [
    {
      key: 'date',
      title: 'Tanggal',
      dataIndex: 'date',
      width: 120,
      render: (r) => fmtReportDate(r.date),
    },
    {
      key: 'product',
      title: 'Produk',
      width: 240,
      render: (r) => (
        <span>
          {r.code ? <Text type="secondary">{r.code}</Text> : null}
          {r.code ? ' · ' : ''}
          {r.name}
        </span>
      ),
      export: { value: (r) => (r.code ? `${r.code} · ${r.name}` : r.name) },
    },
    { key: 'location', title: 'Lokasi', dataIndex: 'location_name', width: 150 },
    {
      key: 'qty_in',
      title: 'Masuk',
      dataIndex: 'qty_in',
      align: 'right',
      width: 100,
      render: (r) => (r.qty_in != null ? <span style={{ color: '#389e0d' }}>{fmtQty(r.qty_in)}</span> : null),
    },
    {
      key: 'qty_out',
      title: 'Keluar',
      dataIndex: 'qty_out',
      align: 'right',
      width: 100,
      render: (r) => (r.qty_out != null ? <span style={{ color: '#cf1322' }}>{fmtQty(r.qty_out)}</span> : null),
    },
    {
      key: 'reference',
      title: 'Ref. Sumber',
      dataIndex: 'reference',
      width: 160,
      render: (r) => r.reference || '—',
    },
    {
      key: 'source',
      title: 'Model Sumber',
      dataIndex: 'source_label',
      width: 160,
      render: (r) => (r.source_label ? <Tag color={labelColor[r.source_label] ?? 'default'}>{r.source_label}</Tag> : '—'),
    },
    {
      key: 'description',
      title: 'Deskripsi',
      dataIndex: 'description',
      render: (r) => r.description || '—',
    },
  ];

  /** Baris Total ringkasan. */
  const summaryCells: ReportSummaryCell[] = [
    { colSpan: 3, value: <Text strong>Total ({totals?.count ?? 0} baris)</Text> },
    {
      align: 'right',
      value: (
        <Text strong style={{ color: '#389e0d' }}>
          {fmtQty(totals?.qty_in ?? 0)}
        </Text>
      ),
    },
    {
      align: 'right',
      value: (
        <Text strong style={{ color: '#cf1322' }}>
          {fmtQty(totals?.qty_out ?? 0)}
        </Text>
      ),
    },
    { colSpan: 3, align: 'right', value: <Text strong>Net: {fmtQty(totals?.net ?? 0)}</Text> },
  ];

  // ── Filter (metadata) — grid 4 kolom: 1+1+1 (periode di header) ──
  const filters: ReportFilter[] = [
    {
      key: 'product',
      label: 'Produk',
      type: 'select',
      value: productId,
      options: productOptions,
      showSearch: true,
      serverSearch: true,
      placeholder: 'Cari produk…',
      loading: productsQuery.isFetching,
      onSearch: (v) => setProductSearch(v),
      notFoundContent: productSearch ? 'Produk tidak ditemukan' : 'Ketik untuk mencari produk…',
      onChange: (v, o) => {
        const id = v as number | undefined;
        setProductId(id);
        const label = (o as { label?: string } | undefined)?.label;
        setProductLabel(id !== undefined ? label ?? `#${id}` : undefined);
      },
    },
    {
      key: 'warehouse',
      label: 'Gudang',
      type: 'select',
      value: warehouseIds,
      options: warehouseOptions,
      multiple: true,
      showSearch: true,
      placeholder: 'Semua Gudang',
      loading: warehousesQuery.isLoading,
      onChange: (v) => setWarehouseIds((v as number[] | undefined) ?? []),
    },
    {
      key: 'source',
      label: 'Model Sumber',
      type: 'select',
      value: sourceModels,
      options: sourceOptions,
      multiple: true,
      showSearch: true,
      placeholder: 'Semua Sumber',
      loading: query.isFetching,
      onChange: (v) => setSourceModels((v as string[] | undefined) ?? []),
    },
    {
      key: 'period',
      label: 'Periode',
      type: 'period',
      place: 'header',
      width: 240,
      value: period,
      range: customRange,
      resolvedRange: range,
      options: PERIOD_PRESETS.map((p) => ({ key: p.key, label: p.label })),
      disabledDate: notFuture,
      onChange: ({ key, range: r }) => {
        setPeriod(key);
        if (key === 'custom') setCustomRange(r ?? (range ?? null));
      },
    },
  ];

  // ── Export Excel (header & isi diturunkan shell dari metadata kolom) ──
  const exportConfig = useMemo(
    () => ({
      filename: () =>
        `Stock_Ledger_${range?.[0]?.format('YYYY-MM-DD') ?? 'all'}${range?.[1] ? `_${range[1].format('YYYY-MM-DD')}` : ''}.xlsx`,
      sheetName: 'Mutasi Stock',
      meta: [
        ['Produk', productLabel ?? 'Semua Produk'],
        ['Gudang', warehouseLabel],
        ['Model Sumber', sourceModels.length ? sourceModels.join(', ') : 'Semua Sumber'],
        ['Periode', periodText],
      ] as (string | number)[][],
    }),
    [range, productLabel, warehouseLabel, sourceModels, periodText],
  );

  return (
    <ReportPage<StockLedgerRow>
      title="Mutasi Stock"
      filters={filters}
      fetchedAt={query.dataUpdatedAt || null}
      loading={loading}
      refreshing={refreshing}
      onRefresh={onRefresh}
      columns={columns}
      dataSource={rows}
      rowKey="id"
      summaryCells={summaryCells}
      emptyText="Tidak ada pergerakan stok untuk filter ini"
      exportConfig={exportConfig}
    />
  );
}
