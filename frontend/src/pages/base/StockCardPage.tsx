import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Tag, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { stockCardApi } from '../../api/report';
import type { StockCardRow } from '../../api/report';
import { modelApi } from '../../api/models';
import { fmtQty, fmtReportDate } from '../../utils/reportFormat';
import ReportPage from '../../components/report/ReportPage';
import type { ReportColumn, ReportFilter } from '../../components/report/types';

const { Text } = Typography;

/** Warna label per jenis sumber pergerakan */
const labelColor: Record<string, string> = {
  'Penerimaan (GR)': 'green',
  'Pengiriman (DO)': 'red',
  'Transfer Masuk': 'cyan',
  'Transfer Keluar': 'volcano',
  Penyesuaian: 'purple',
};

const isSumRow = (r: StockCardRow) => r.kind !== 'movement';

/** Blok tanggal di masa depan (stok masa depan tidak mungkin). */
const notFuture = (d: Dayjs) => d.isAfter(dayjs().endOf('day'));

/** Opsi dropdown periode. */
const PERIOD_OPTIONS: { key: string; label: string }[] = [
  { key: 'today', label: 'Hari Ini' },
  { key: 'last_7_days', label: '7 Hari Terakhir' },
  { key: 'this_month', label: 'Bulan Ini' },
  { key: 'last_month', label: 'Bulan Lalu' },
  { key: 'this_year', label: 'Tahun Ini' },
  { key: 'all', label: 'Semua' },
];

/** Range tanggal untuk key periode (null = tanpa batas). */
const periodRange = (key: string): [Dayjs, Dayjs] | null => {
  if (key === 'today') return [dayjs().startOf('day'), dayjs().endOf('day')];
  if (key === 'last_7_days') return [dayjs().subtract(6, 'day').startOf('day'), dayjs().endOf('day')];
  if (key === 'this_month') return [dayjs().startOf('month'), dayjs().endOf('month')];
  if (key === 'last_month') {
    const prev = dayjs().subtract(1, 'month');
    return [prev.startOf('month'), prev.endOf('month')];
  }
  if (key === 'this_year') return [dayjs().startOf('year'), dayjs().endOf('year')];
  return null;
};

/**
 * Stock Card — kartu stok detail pergerakan (GR/DO/transfer/penyesuaian)
 * per produk & lokasi dengan saldo berjalan + Saldo Awal/Akhir.
 * Route: /inventory/stock_card
 *
 * Layout/UI memakai standar <ReportPage /> (2 card: filter 4 kolom + tabel);
 * halaman ini hanya mendefinisikan metadata filter, kolom, dan export.
 */
export default function StockCardPage() {
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [warehouseIds, setWarehouseIds] = useState<number[]>([]);
  const [period, setPeriod] = useState('all');
  const [customRange, setCustomRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [productSearch, setProductSearch] = useState('');

  /** Range efektif: dari dropdown periode, atau range manual saat "Kustom". */
  const range = useMemo(
    () => (period === 'custom' ? customRange : periodRange(period)),
    [period, customRange],
  );

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
    queryKey: ['stock-card-products', productSearch],
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

  const query = useQuery({
    queryKey: [
      'stock-card',
      productId ?? '',
      warehousesJoined,
      range?.[0]?.format('YYYY-MM-DD') ?? '',
      range?.[1]?.format('YYYY-MM-DD') ?? '',
    ],
    queryFn: () =>
      stockCardApi.get({
        product: productId,
        warehouses: warehousesJoined || undefined,
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
  const periodText =
    range?.[0] && range?.[1]
      ? `${fmtReportDate(range[0].format('YYYY-MM-DD'))} s/d ${fmtReportDate(range[1].format('YYYY-MM-DD'))}`
      : range?.[0]
        ? `dari ${fmtReportDate(range[0].format('YYYY-MM-DD'))}`
        : range?.[1]
          ? `sampai ${fmtReportDate(range[1].format('YYYY-MM-DD'))}`
          : 'Semua periode';

  const columns: ReportColumn<StockCardRow>[] = [
    ...(productId === undefined
      ? [
          {
            key: 'product',
            title: 'Produk',
            width: 220,
            render: (row: StockCardRow) =>
              isSumRow(row) ? null : (
                <span>
                  {row.code ? <Text type="secondary">{row.code}</Text> : null}
                  {row.code ? ' · ' : ''}
                  {row.name}
                </span>
              ),
            export: {
              value: (row: StockCardRow) =>
                isSumRow(row) ? '' : row.code ? `${row.code} · ${row.name}` : row.name,
            },
          },
        ]
      : []),
    {
      key: 'location',
      title: 'Lokasi',
      dataIndex: 'location_name',
      width: 150,
      render: (row: StockCardRow) => (isSumRow(row) ? null : row.location_name),
    },
    {
      key: 'date',
      title: 'Tanggal',
      dataIndex: 'date',
      width: 110,
      render: (row: StockCardRow) => fmtReportDate(row.date),
    },
    {
      key: 'source',
      title: 'Jenis',
      dataIndex: 'source_label',
      width: 160,
      render: (row: StockCardRow) =>
        row.kind === 'movement' ? (
          <Tag color={labelColor[row.source_label] ?? 'default'}>{row.source_label}</Tag>
        ) : (
          <span>{row.source_label}</span>
        ),
      export: { value: (row: StockCardRow) => (row.kind === 'movement' ? row.source_label : row.reference) },
    },
    {
      key: 'reference',
      title: 'No. Dokumen',
      dataIndex: 'reference',
      width: 150,
      render: (row: StockCardRow) => (
        <Text strong={isSumRow(row)} italic={isSumRow(row)} type={isSumRow(row) ? 'secondary' : undefined}>
          {row.kind === 'movement' ? row.reference || '—' : ''}
        </Text>
      ),
      export: { value: (row: StockCardRow) => (row.kind === 'movement' ? row.reference : '') },
    },
    {
      key: 'description',
      title: 'Keterangan',
      dataIndex: 'description',
      render: (row: StockCardRow) => (isSumRow(row) ? null : <span>{row.description || '—'}</span>),
      export: { value: (row: StockCardRow) => (row.kind === 'movement' ? row.description : '') },
    },
    {
      key: 'qty_in',
      title: 'Masuk',
      dataIndex: 'qty_in',
      align: 'right',
      width: 100,
      render: (row: StockCardRow) =>
        row.qty_in != null ? <span style={{ color: '#389e0d' }}>{fmtQty(row.qty_in)}</span> : null,
    },
    {
      key: 'qty_out',
      title: 'Keluar',
      dataIndex: 'qty_out',
      align: 'right',
      width: 100,
      render: (row: StockCardRow) =>
        row.qty_out != null ? <span style={{ color: '#cf1322' }}>{fmtQty(row.qty_out)}</span> : null,
    },
    {
      key: 'balance',
      title: 'Saldo',
      dataIndex: 'balance',
      align: 'right',
      width: 120,
      render: (row: StockCardRow) => (
        <Text strong={isSumRow(row)} italic={isSumRow(row)}>
          {row.balance != null ? fmtQty(row.balance) : ''}
        </Text>
      ),
    },
  ];

  // ── Filter (metadata) — grid 4 kolom: 1+1+2 ──
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
      key: 'period',
      label: 'Periode',
      type: 'period',
      place: 'header',
      width: 240,
      value: period,
      range: customRange,
      resolvedRange: range,
      options: PERIOD_OPTIONS,
      disabledDate: notFuture,
      onChange: ({ key, range: r }) => {
        setPeriod(key);
        // Prefill range manual dari periode yang sedang aktif saat pindah ke "Kustom".
        if (key === 'custom') setCustomRange(r ?? (Array.isArray(range) ? range : null));
      },
    },
  ];

  // ── Export Excel (header & isi diturunkan shell dari metadata kolom) ──
  const exportConfig = useMemo(
    () => ({
      filename: () =>
        `Stock_Card_${range?.[0]?.format('YYYY-MM-DD') ?? 'all'}${range?.[1] ? `_${range[1].format('YYYY-MM-DD')}` : ''}.xlsx`,
      sheetName: 'Kartu Stock',
      meta: [
        ['Produk', productLabel ?? 'Semua Produk'],
        ['Gudang', warehouseLabel],
        ['Periode', periodText],
      ] as (string | number)[][],
    }),
    [range, productLabel, warehouseLabel, periodText],
  );

  return (
    <ReportPage<StockCardRow>
      title="Kartu Stock"
      filters={filters}
      fetchedAt={query.dataUpdatedAt || null}
      loading={loading}
      refreshing={refreshing}
      onRefresh={onRefresh}
      columns={columns}
      dataSource={rows}
      rowKey={(r, i) => `${r.product_id}-${r.location_id}-${r.kind}-${r.date}-${r.reference}-${i}`}
      emptyText="Tidak ada pergerakan stok untuk filter ini"
      exportConfig={exportConfig}
    />
  );
}
