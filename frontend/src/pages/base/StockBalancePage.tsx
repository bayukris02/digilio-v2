import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message, Tag, Switch } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { stockBalanceApi } from '../../api/report';
import { modelApi } from '../../api/models';
import { exportXlsx, numCell } from '../../utils/exportExcel';

const { Title, Text } = Typography;

const fmtQty = (v: number | null | undefined) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

const fmtDelta = (v: number | null | undefined) => {
  const n = Number(v ?? 0);
  const s = fmtQty(Math.abs(n));
  return n > 0 ? `+${s}` : n < 0 ? `−${s}` : s;
};

const PRESETS: { key: string; label: string; offsetDays: number }[] = [
  { key: 'today', label: 'Hari Ini', offsetDays: 0 },
  { key: 'yesterday', label: 'Kemarin', offsetDays: 1 },
  { key: 'lastweek', label: 'Minggu Lalu', offsetDays: 7 },
  { key: 'lastmonth', label: 'Bulan Lalu', offsetDays: 30 },
];

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
 */
export default function StockBalancePage() {
  const today = useMemo(() => dayjs().startOf('day'), []);
  const [date, setDate] = useState<Dayjs>(() => dayjs().startOf('day'));
  const [compare, setCompare] = useState(false);
  const [date2, setDate2] = useState<Dayjs | null>(null);
  const [warehouseIds, setWarehouseIds] = useState<number[]>([]);
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [productSearch, setProductSearch] = useState('');

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

  const activePreset = PRESETS.find((p) => date?.isSame(today.subtract(p.offsetDays, 'day'), 'day'));
  const dateLabel = activePreset
    ? activePreset.label
    : date
      ? date.format('DD MMM YYYY')
      : '—';
  const date2Label = date2 ? date2.format('DD MMM YYYY') : '—';

  const onRefresh = useCallback(() => {
    q1.refetch();
    if (compare && q2) q2.refetch();
  }, [q1, q2, compare]);

  const toggleCompare = useCallback(
    (on: boolean) => {
      setCompare(on);
      if (on && !date2) {
        setDate2(date.subtract(7, 'day'));
      }
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

  // ── Kolom ──
  const fixedCols = [
    { title: 'Kode', dataIndex: 'code', width: 120 },
    { title: 'Produk', dataIndex: 'name' },
    { title: 'Satuan', dataIndex: 'uom', width: 90 },
  ];
  const qtyCols = compare
    ? [
        {
          title: `Saldo · ${dateLabel}`,
          dataIndex: 'qtyA',
          align: 'right' as const,
          width: 140,
          render: (v: number) => <Text strong>{fmtQty(v)}</Text>,
        },
        {
          title: `Saldo · ${date2Label}`,
          dataIndex: 'qtyB',
          align: 'right' as const,
          width: 140,
          render: (v: number) => <Text strong>{fmtQty(v)}</Text>,
        },
        {
          title: 'Selisih',
          dataIndex: 'delta',
          align: 'right' as const,
          width: 120,
          render: (_: unknown, r: MergedRow) => {
            const d = r.qtyB - r.qtyA;
            return (
              <Text strong style={{ color: d > 0 ? '#389e0d' : d < 0 ? '#cf1322' : undefined }}>
                {fmtDelta(d)}
              </Text>
            );
          },
        },
      ]
    : [
        {
          title: `Saldo · ${dateLabel}`,
          dataIndex: 'qtyA',
          align: 'right' as const,
          width: 140,
          render: (v: number) => <Text strong>{fmtQty(v)}</Text>,
        },
      ];

  const columns = [...fixedCols, ...qtyCols];

  // ── Export Excel ──
  const onExport = useCallback(() => {
    const rows: (string | number)[][] = [
      ['Stock Balance'],
      ['Tanggal', compare ? `${dateLabel} vs ${date2Label}` : dateLabel],
      ['Gudang', warehouseLabel],
      ['Produk', productLabel ?? 'Semua Produk'],
      [],
    ];
    if (compare) {
      rows.push(['Kode', 'Produk', 'Satuan', `Saldo ${dateLabel}`, `Saldo ${date2Label}`, 'Selisih']);
      for (const r of dataRows) rows.push([r.code, r.name, r.uom, numCell(r.qtyA), numCell(r.qtyB), numCell(r.qtyB - r.qtyA)]);
      rows.push(['', 'Total', '', numCell(totals.qtyA), numCell(totals.qtyB), numCell(totals.delta)]);
    } else {
      rows.push(['Kode', 'Produk', 'Satuan', `Saldo ${dateLabel}`]);
      for (const r of dataRows) rows.push([r.code, r.name, r.uom, numCell(r.qtyA)]);
      rows.push(['', 'Total', '', numCell(totals.qtyA)]);
    }
    exportXlsx({
      filename: `Stock_Balance_${compare && date2 ? `${date.format('YYYY-MM-DD')}_vs_${date2.format('YYYY-MM-DD')}` : date.format('YYYY-MM-DD')}.xlsx`,
      sheetName: 'Stock Balance',
      rows,
      colWidths: [14, 36, 10, 16, 16, 12],
    });
  }, [compare, date, date2, dateLabel, warehouseLabel, productLabel, dataRows, totals]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              Stock Balance
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Saldo stok per <Tag style={{ marginRight: 0 }}>{dateLabel}</Tag> · {warehouseLabel}
            </Text>
          </div>
          <Space>
            <Button size="small" icon={<DownloadOutlined />} onClick={onExport} disabled={!q1.data?.rows?.length}>
              Export Excel
            </Button>
            <Button size="small" icon={<ReloadOutlined spin={refreshing} />} onClick={onRefresh} loading={refreshing}>
              Refresh
            </Button>
          </Space>
        </div>

        {/* Filter panel */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, rowGap: 10 }}>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Gudang:
              </Text>
              <Select
                size="small"
                mode="multiple"
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="Semua Gudang"
                style={{ minWidth: 220, maxWidth: 360 }}
                value={warehouseIds}
                options={warehouseOptions}
                loading={warehousesQuery.isLoading}
                onChange={(v) => setWarehouseIds(v)}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Produk:
              </Text>
              <Select
                size="small"
                allowClear
                showSearch
                placeholder="Cari produk…"
                style={{ width: 220 }}
                value={productId}
                options={productOptions}
                loading={productsQuery.isFetching}
                filterOption={false}
                onSearch={(v) => setProductSearch(v)}
                onChange={(v, o) => {
                  setProductId(v);
                  const label = (o as { label?: string } | undefined)?.label;
                  setProductLabel(v !== undefined ? label ?? `#${v}` : undefined);
                }}
                notFoundContent={productSearch ? 'Produk tidak ditemukan' : 'Ketik untuk mencari produk…'}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Tanggal:
              </Text>
              {PRESETS.map((p) => {
                const presetDate = today.subtract(p.offsetDays, 'day');
                const active = !!date?.isSame(presetDate, 'day') && !compare;
                return (
                  <Button
                    key={p.key}
                    size="small"
                    type={active ? 'primary' : 'default'}
                    onClick={() => {
                      setDate(presetDate);
                      if (compare) setCompare(false);
                    }}
                  >
                    {p.label}
                  </Button>
                );
              })}
              <DatePicker
                size="small"
                value={date}
                allowClear={false}
                disabledDate={notFuture}
                onChange={(d) => setDate((d ?? today).startOf('day'))}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Compare:
              </Text>
              <Switch size="small" checked={compare} onChange={toggleCompare} />
              {compare ? (
                <DatePicker
                  size="small"
                  value={date2}
                  allowClear={false}
                  disabledDate={notFuture}
                  onChange={(d) => setDate2((d ?? today).startOf('day'))}
                />
              ) : null}
            </Space>
          </div>
        </Card>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small">
            <Table
              size="small"
              rowKey="product_id"
              columns={columns}
              dataSource={dataRows}
              pagination={false}
              locale={{ emptyText: 'Tidak ada stok pada tanggal tersebut' }}
              summary={() => (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={3}>
                    <Text strong>Total</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <Text strong>{fmtQty(totals.qtyA)}</Text>
                  </Table.Summary.Cell>
                  {compare ? (
                    <>
                      <Table.Summary.Cell index={4} align="right">
                        <Text strong>{fmtQty(totals.qtyB)}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right">
                        <Text strong style={{ color: totals.delta > 0 ? '#389e0d' : totals.delta < 0 ? '#cf1322' : undefined }}>
                          {fmtDelta(totals.delta)}
                        </Text>
                      </Table.Summary.Cell>
                    </>
                  ) : null}
                </Table.Summary.Row>
              )}
            />
          </Card>
        )}
      </div>
    </div>
  );
}
