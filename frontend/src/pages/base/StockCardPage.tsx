import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message, Tag } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { stockCardApi } from '../../api/report';
import type { StockCardRow } from '../../api/report';
import { modelApi } from '../../api/models';
import { exportXlsx, numCell } from '../../utils/exportExcel';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const fmtQty = (v: number | null | undefined) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

const fmtDate = (v: string | null | undefined) => (v ? dayjs(v).format('DD MMM YYYY') : '—');

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

/**
 * Stock Card — kartu stok detail pergerakan (GR/DO/transfer/penyesuaian)
 * per produk & lokasi dengan saldo berjalan + Saldo Awal/Akhir.
 * Route: /inventory/stock_card
 */
export default function StockCardPage() {
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [warehouseIds, setWarehouseIds] = useState<number[]>([]);
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
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
  const periodText = range?.[0] && range?.[1]
    ? `${range[0].format('DD MMM YYYY')} s/d ${range[1].format('DD MMM YYYY')}`
    : range?.[0]
      ? `dari ${range[0].format('DD MMM YYYY')}`
      : range?.[1]
        ? `sampai ${range[1].format('DD MMM YYYY')}`
        : 'Semua periode';

  const columns = [
    ...(productId === undefined
      ? [
          {
            title: 'Produk',
            width: 220,
            render: (_: unknown, row: StockCardRow) =>
              isSumRow(row) ? null : (
                <span>
                  {row.code ? <Text type="secondary">{row.code}</Text> : null}
                  {row.code ? ' · ' : ''}
                  {row.name}
                </span>
              ),
          },
        ]
      : []),
    {
      title: 'Lokasi',
      dataIndex: 'location_name',
      width: 150,
      render: (v: string, row: StockCardRow) => (isSumRow(row) ? null : v),
    },
    {
      title: 'Tanggal',
      dataIndex: 'date',
      width: 110,
      render: (v: string) => fmtDate(v),
    },
    {
      title: 'Jenis',
      dataIndex: 'source_label',
      width: 160,
      render: (v: string, row: StockCardRow) =>
        row.kind === 'movement' ? <Tag color={labelColor[v] ?? 'default'}>{v}</Tag> : <span>{v}</span>,
    },
    {
      title: 'No. Dokumen',
      dataIndex: 'reference',
      width: 150,
      render: (v: string, row: StockCardRow) => (
        <Text strong={isSumRow(row)} italic={isSumRow(row)} type={isSumRow(row) ? 'secondary' : undefined}>
          {row.kind === 'movement' ? v || '—' : ''}
        </Text>
      ),
    },
    {
      title: 'Keterangan',
      dataIndex: 'description',
      render: (v: string, row: StockCardRow) => (isSumRow(row) ? null : <span>{v || '—'}</span>),
    },
    {
      title: 'Masuk',
      dataIndex: 'qty_in',
      align: 'right' as const,
      width: 100,
      render: (v: number | null) =>
        v != null ? <span style={{ color: '#389e0d' }}>{fmtQty(v)}</span> : null,
    },
    {
      title: 'Keluar',
      dataIndex: 'qty_out',
      align: 'right' as const,
      width: 100,
      render: (v: number | null) =>
        v != null ? <span style={{ color: '#cf1322' }}>{fmtQty(v)}</span> : null,
    },
    {
      title: 'Saldo',
      dataIndex: 'balance',
      align: 'right' as const,
      width: 120,
      render: (v: number | null, row: StockCardRow) => (
        <Text strong={isSumRow(row)} italic={isSumRow(row)}>
          {v != null ? fmtQty(v) : ''}
        </Text>
      ),
    },
  ];

  // ── Export Excel ──
  const onExport = useCallback(() => {
    const header = [
      ...(productId === undefined ? ['Produk'] : []),
      'Lokasi',
      'Tanggal',
      'Jenis',
      'No. Dokumen',
      'Keterangan',
      'Masuk',
      'Keluar',
      'Saldo',
    ];
    const data: (string | number)[][] = rows.map((r) => [
      ...(productId === undefined ? [r.code ? `${r.code} · ${r.name}` : r.name] : []),
      r.location_name,
      r.date || '',
      r.kind === 'movement' ? r.source_label : r.reference,
      r.kind === 'movement' ? r.reference : '',
      r.kind === 'movement' ? r.description : '',
      numCell(r.qty_in),
      numCell(r.qty_out),
      numCell(r.balance),
    ]);
    exportXlsx({
      filename: `Stock_Card_${range?.[0]?.format('YYYY-MM-DD') ?? 'all'}${range?.[1] ? `_${range[1].format('YYYY-MM-DD')}` : ''}.xlsx`,
      sheetName: 'Stock Card',
      rows: [
        ['Stock Card'],
        ['Produk', productLabel ?? 'Semua Produk'],
        ['Gudang', warehouseLabel],
        ['Periode', periodText],
        [],
        header,
        ...data,
      ],
      colWidths: [28, 18, 12, 18, 16, 40, 10, 10, 12],
    });
  }, [rows, productId, productLabel, warehouseLabel, range, periodText]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              Stock Card
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {productLabel ?? 'Semua Produk'} · {warehouseLabel} · {periodText}
            </Text>
          </div>
          <Space>
            <Button size="small" icon={<DownloadOutlined />} onClick={onExport} disabled={!rows.length}>
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
                Periode:
              </Text>
              <RangePicker
                size="small"
                value={range}
                disabledDate={notFuture}
                onChange={(dates) => setRange(dates as [Dayjs | null, Dayjs | null] | null)}
              />
            </Space>
          </div>
        </Card>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small">
            <Table
              size="small"
              rowKey={(r, i) => `${r.product_id}-${r.location_id}-${r.kind}-${r.date}-${r.reference}-${i}`}
              columns={columns}
              dataSource={rows}
              pagination={false}
              locale={{ emptyText: 'Tidak ada pergerakan stok untuk filter ini' }}
            />
          </Card>
        )}
      </div>
    </div>
  );
}
