import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { stockBalanceApi } from '../../api/report';
import { modelApi } from '../../api/models';
import { fmtQty, fmtReportDate } from '../../utils/reportFormat';
import ReportPage from '../../components/report/ReportPage';
import type { ReportColumn, ReportFilter, ReportSummaryCell } from '../../components/report/types';

const { Text } = Typography;

const fmtDelta = (v: number | null | undefined) => {
  const n = Number(v ?? 0);
  const s = fmtQty(Math.abs(n));
  return n > 0 ? `+${s}` : n < 0 ? `−${s}` : s;
};

/** Opsi dropdown periode — snapshot SATU tanggal (mode 'date'). */
const DATE_OPTIONS: { key: string; label: string }[] = [
  { key: 'today', label: 'Hari Ini' },
  { key: 'yesterday', label: 'Kemarin' },
  { key: 'last_week', label: 'Minggu Lalu' },
  { key: 'last_month', label: 'Bulan Lalu' },
  { key: 'all', label: 'Stok Terkini' },
];

/** Tanggal snapshot untuk key periode (null = seluruh row aktif / stok terkini). */
const snapshotDate = (key: string): Dayjs | null => {
  if (key === 'today') return dayjs().startOf('day');
  if (key === 'yesterday') return dayjs().subtract(1, 'day').startOf('day');
  if (key === 'last_week') return dayjs().subtract(7, 'day').startOf('day');
  if (key === 'last_month') return dayjs().subtract(1, 'month').startOf('day');
  return null;
};

/** Blok tanggal di masa depan (stok masa depan tidak mungkin). */
const notFuture = (d: Dayjs) => d.isAfter(dayjs().endOf('day'));

interface MergedRow {
  product_id: number;
  code: string;
  name: string;
  uom: string;
  qtyA: number;
  qtyB: number;
}

/**
 * Stock Balance — saldo stok per produk pada SATU tanggal (opsional compare
 * dua tanggal). Route: /inventory/stock_balance
 *
 * Layout/UI memakai standar <ReportPage /> (2 card: filter 4 kolom + tabel);
 * halaman ini hanya mendefinisikan metadata filter, kolom, dan export.
 */
export default function StockBalancePage() {
  const [period, setPeriod] = useState('today');
  const [customDate, setCustomDate] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [compare, setCompare] = useState(false);
  const [date2, setDate2] = useState<Dayjs | null>(null);
  const [warehouseIds, setWarehouseIds] = useState<number[]>([]);
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [productSearch, setProductSearch] = useState('');

  /** Tanggal snapshot efektif (dropdown periode / kustom). */
  const date = useMemo(
    () => (period === 'custom' ? customDate?.[0] ?? null : snapshotDate(period)),
    [period, customDate],
  );
  const resolvedRange = useMemo(() => [date, null] as [Dayjs | null, Dayjs | null], [date]);

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
    queryKey: ['stock-balance-products', productSearch],
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

  // ── Query laporan ──
  const q1 = useQuery({
    queryKey: ['stock-balance', date?.format('YYYY-MM-DD') ?? '', warehousesJoined, productId ?? ''],
    queryFn: () =>
      stockBalanceApi.get({
        date: date?.format('YYYY-MM-DD') ?? undefined,
        warehouses: warehousesJoined || undefined,
        product: productId,
      }),
    staleTime: 30 * 1000,
  });
  const q2 = useQuery({
    queryKey: ['stock-balance', date2?.format('YYYY-MM-DD') ?? '', warehousesJoined, productId ?? '', 'cmp'],
    queryFn: () =>
      stockBalanceApi.get({
        date: date2?.format('YYYY-MM-DD') ?? undefined,
        warehouses: warehousesJoined || undefined,
        product: productId,
      }),
    enabled: compare && !!date2,
    staleTime: 30 * 1000,
  });

  const loading = q1.isLoading || (compare && q2.isLoading);
  const refreshing = (q1.isFetching || (compare && !!q2 && q2.isFetching)) && !loading;

  const dateLabel = date ? fmtReportDate(date.format('YYYY-MM-DD')) : 'Stok Terkini';
  const date2Label = date2 ? fmtReportDate(date2.format('YYYY-MM-DD')) : '—';

  const onRefresh = useCallback(() => {
    q1.refetch();
    if (compare && q2) q2.refetch();
  }, [q1, q2, compare]);

  const toggleCompare = useCallback(
    (on: boolean) => {
      setCompare(on);
      if (on && !date2) setDate2((date ?? dayjs()).subtract(7, 'day').startOf('day'));
    },
    [date, date2],
  );

  if (q1.isError) {
    message.error('Gagal memuat laporan: ' + ((q1.error as Error)?.message || 'Unknown error'));
  }
  if (q2.isError) {
    message.error('Gagal memuat data pembanding: ' + ((q2.error as Error)?.message || 'Unknown error'));
  }

  const dataRows: MergedRow[] = useMemo(() => {
    const rowsA = q1.data?.rows ?? [];
    if (!compare || !q2.data) return rowsA.map((r) => ({ ...r, qtyA: r.qty, qtyB: r.qty }));
    const byId = new Map<number, MergedRow>();
    for (const r of rowsA) byId.set(r.product_id, { ...r, qtyA: r.qty, qtyB: 0 });
    for (const r of q2.data?.rows ?? []) {
      const ex = byId.get(r.product_id);
      if (ex) ex.qtyB = r.qty;
      else byId.set(r.product_id, { ...r, qtyA: 0, qtyB: r.qty });
    }
    return [...byId.values()].sort((x, y) => (x.code || x.name).localeCompare(y.code || y.name));
  }, [q1.data, q2.data, compare]);

  const totals = useMemo(() => {
    if (!compare) return { qtyA: q1.data?.totals.qty ?? 0, qtyB: 0, delta: 0 };
    return {
      qtyA: dataRows.reduce((s, r) => s + r.qtyA, 0),
      qtyB: dataRows.reduce((s, r) => s + r.qtyB, 0),
      delta: dataRows.reduce((s, r) => s + (r.qtyB - r.qtyA), 0),
    };
  }, [compare, dataRows, q1.data]);

  // ── Kolom (metadata) ──
  const fixedCols: ReportColumn<MergedRow>[] = [
    { key: 'code', title: 'Kode', dataIndex: 'code', width: 120 },
    { key: 'name', title: 'Produk', dataIndex: 'name' },
    { key: 'uom', title: 'Satuan', dataIndex: 'uom', width: 90 },
  ];
  const qtyCols: ReportColumn<MergedRow>[] = compare
    ? [
        {
          key: 'qty_a',
          title: `Saldo · ${dateLabel}`,
          dataIndex: 'qtyA',
          align: 'right',
          width: 140,
          render: (r) => <Text strong>{fmtQty(r.qtyA)}</Text>,
        },
        {
          key: 'qty_b',
          title: `Saldo · ${date2Label}`,
          dataIndex: 'qtyB',
          align: 'right',
          width: 140,
          render: (r) => <Text strong>{fmtQty(r.qtyB)}</Text>,
        },
        {
          key: 'delta',
          title: 'Selisih',
          align: 'right',
          width: 120,
          render: (r) => {
            const d = r.qtyB - r.qtyA;
            return (
              <Text strong style={{ color: d > 0 ? '#389e0d' : d < 0 ? '#cf1322' : undefined }}>
                {fmtDelta(d)}
              </Text>
            );
          },
          export: { value: (r) => r.qtyB - r.qtyA },
        },
      ]
    : [
        {
          key: 'qty_a',
          title: `Saldo · ${dateLabel}`,
          dataIndex: 'qtyA',
          align: 'right',
          width: 140,
          render: (r) => <Text strong>{fmtQty(r.qtyA)}</Text>,
        },
      ];

  const columns: ReportColumn<MergedRow>[] = [...fixedCols, ...qtyCols];

  /** Baris Total — selnya mengikuti jumlah kolom yang sedang tampil. */
  const summaryCells: ReportSummaryCell[] = [
    { colSpan: 3, value: <Text strong>Total</Text> },
    { align: 'right', value: <Text strong>{fmtQty(totals.qtyA)}</Text> },
    ...(compare
      ? [
          { align: 'right' as const, value: <Text strong>{fmtQty(totals.qtyB)}</Text> },
          {
            align: 'right' as const,
            value: (
              <Text strong style={{ color: totals.delta > 0 ? '#389e0d' : totals.delta < 0 ? '#cf1322' : undefined }}>
                {fmtDelta(totals.delta)}
              </Text>
            ),
          },
        ]
      : []),
  ];

  // ── Filter (metadata) — grid 4 kolom: 1+1+1+1 ──
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
      key: 'compare',
      label: 'Compare',
      type: 'boolean',
      value: compare,
      onChange: toggleCompare,
    },
    {
      key: 'compare_date',
      label: `Pembanding · ${date2Label}`,
      type: 'date',
      value: date2,
      disabled: !compare,
      disabledDate: notFuture,
      onChange: (d) => setDate2(d ? d.startOf('day') : null),
    },
    {
      key: 'period',
      label: 'Periode',
      type: 'period',
      mode: 'date',
      place: 'header',
      width: 220,
      value: period,
      range: customDate,
      resolvedRange,
      options: DATE_OPTIONS,
      disabledDate: notFuture,
      onChange: ({ key, range: r }) => {
        setPeriod(key);
        if (key === 'custom') setCustomDate(r ?? (date ? [date, null] : null));
      },
    },
  ];

  // ── Export Excel (header & isi diturunkan shell dari metadata kolom) ──
  const exportConfig = useMemo(
    () => ({
      filename: () =>
        `Stock_Balance_${
          compare && date2
            ? `${date?.format('YYYY-MM-DD') ?? 'all'}_vs_${date2.format('YYYY-MM-DD')}`
            : date?.format('YYYY-MM-DD') ?? 'all'
        }.xlsx`,
      sheetName: 'Stock Balance',
      meta: [
        ['Tanggal', compare ? `${dateLabel} vs ${date2Label}` : dateLabel],
        ['Gudang', warehouseLabel],
        ['Produk', productLabel ?? 'Semua Produk'],
      ] as (string | number)[][],
    }),
    [compare, date, date2, dateLabel, date2Label, warehouseLabel, productLabel],
  );

  return (
    <ReportPage<MergedRow>
      title="Stock Balance"
      filters={filters}
      fetchedAt={q1.dataUpdatedAt || null}
      loading={loading}
      refreshing={refreshing}
      onRefresh={onRefresh}
      columns={columns}
      dataSource={dataRows}
      rowKey="product_id"
      summaryCells={summaryCells}
      emptyText="Tidak ada stok pada tanggal tersebut"
      exportConfig={exportConfig}
    />
  );
}
