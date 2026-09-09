import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { stockCardApi } from '../../api/report';
import type { StockCardRow } from '../../api/report';
import { modelApi } from '../../api/models';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const fmtQty = (v: number | null | undefined) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

const fmtDate = (v: string | null | undefined) => (v ? dayjs(v).format('DD MMM YYYY') : '—');

/** Warna label per jenis sumber pergerakan (ringan, bukan Tag utk qty label) */
const labelColor: Record<string, string> = {
  'Penerimaan (GR)': 'green',
  'Pengiriman (DO)': 'red',
  'Transfer Masuk': 'cyan',
  'Transfer Keluar': 'volcano',
  Penyesuaian: 'purple',
};

const isSumRow = (r: StockCardRow) => r.kind !== 'movement';

/**
 * Stock Card — kartu stok: detail pergerakan (GR/DO/transfer/penyesuaian)
 * per produk & lokasi dengan saldo berjalan + baris Saldo Awal/Akhir.
 * Sumber: row stock ledger aktif (agregasi di core/stock_engine.py).
 * Route: /inventory/stock_card
 */
export default function StockCardPage() {
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [productLabel, setProductLabel] = useState<string | undefined>(undefined);
  const [locationId, setLocationId] = useState<number | undefined>(undefined);
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const [productSearch, setProductSearch] = useState('');

  const locationsQuery = useQuery({
    queryKey: ['model-records', 'inventory.warehouse_location'],
    queryFn: () => modelApi.listRecords('inventory.warehouse_location', 1, 100),
    staleTime: 60 * 1000,
  });

  const locationOptions = useMemo(
    () =>
      (locationsQuery.data?.results ?? []).map((r) => ({
        value: Number(r.id),
        label: String((r as { display_name?: unknown }).display_name ?? r.name ?? `#${r.id}`),
      })),
    [locationsQuery.data],
  );

  // Produk — remote search (pakai ?search= di list API), debounce 300ms
  const productsQuery = useQuery({
    queryKey: ['stock-card-products', productSearch],
    queryFn: () =>
      modelApi.listRecords('inventory.product', 1, 50, productSearch ? { search: productSearch } : undefined),
    staleTime: 30 * 1000,
    enabled: productSearch.length > 0,
  });

  const handleProductSearch = useCallback((v: string) => {
    setProductSearch(v);
  }, []);

  const handleProductChange = useCallback((v: number | undefined, opt: unknown) => {
    setProductId(v);
    const o = opt as { label?: string } | undefined;
    setProductLabel(v !== undefined ? o?.label ?? `#${v}` : undefined);
  }, []);

  const selectOptions = useMemo(() => {
    const fetched = (productsQuery.data?.results ?? []).map((r) => ({
      value: Number(r.id),
      label: String((r as { display_name?: unknown }).display_name ?? r.name ?? `#${r.id}`),
    }));
    if (productLabel && !fetched.some((o) => o.value === productId)) {
      fetched.unshift({ value: productId as number, label: productLabel });
    }
    return fetched;
  }, [productsQuery.data, productLabel, productId]);

  const query = useQuery({
    queryKey: [
      'stock-card',
      productId ?? '',
      locationId ?? '',
      range?.[0]?.format('YYYY-MM-DD') ?? '',
      range?.[1]?.format('YYYY-MM-DD') ?? '',
    ],
    queryFn: () =>
      stockCardApi.get({
        product: productId,
        location: locationId,
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

  const data = query.data;
  const locationLabel =
    locationId !== undefined
      ? locationOptions.find((o) => o.value === locationId)?.label ?? `#${locationId}`
      : 'Semua Lokasi';
  const periodText =
    data?.filters.date_from && data?.filters.date_to
      ? `${data.filters.date_from} s/d ${data.filters.date_to}`
      : data?.filters.date_from
        ? `dari ${data.filters.date_from}`
        : data?.filters.date_to
          ? `sampai ${data.filters.date_to}`
          : 'Semua periode';

  const baseColumns = [
    {
      title: 'Tanggal',
      dataIndex: 'date',
      width: 110,
      render: (v: string) => fmtDate(v),
    },
    {
      title: 'Jenis',
      dataIndex: 'source_label',
      width: 150,
      render: (v: string, row: StockCardRow) =>
        row.kind === 'movement' ? <Tag color={labelColor[v] ?? 'default'}>{v}</Tag> : <span>{v}</span>,
    },
    {
      title: 'No. Dokumen',
      dataIndex: 'reference',
      width: 150,
      render: (v: string, row: StockCardRow) => (
        <Text strong={isSumRow(row)} italic={isSumRow(row)} type={isSumRow(row) ? 'secondary' : undefined}>
          {v || '—'}
        </Text>
      ),
    },
    {
      title: 'Keterangan',
      dataIndex: 'description',
      render: (v: string, row: StockCardRow) =>
        isSumRow(row) ? null : <span>{v || '—'}</span>,
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

  const columns = [
    ...(productId === undefined
      ? [
          {
            title: 'Produk',
            width: 240,
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
    ...(locationId === undefined
      ? [
          {
            title: 'Lokasi',
            width: 160,
            render: (_: unknown, row: StockCardRow) => (isSumRow(row) ? null : row.location_name),
          },
        ]
      : []),
    ...baseColumns,
  ];

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {data?.title ?? 'Stock Card'}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {productLabel ?? 'Semua Produk'} · {locationLabel} · {periodText}
            </Text>
          </div>
          <Space wrap>
            <Select
              size="small"
              allowClear
              showSearch
              placeholder="Semua Produk"
              style={{ width: 220 }}
              value={productId}
              options={selectOptions}
              loading={productsQuery.isFetching}
              filterOption={false}
              onSearch={handleProductSearch}
              onChange={handleProductChange}
              notFoundContent={productSearch ? 'Produk tidak ditemukan' : 'Ketik untuk mencari produk…'}
            />
            <Select
              size="small"
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Semua Lokasi"
              style={{ width: 170 }}
              value={locationId}
              options={locationOptions}
              loading={locationsQuery.isLoading}
              onChange={(v) => setLocationId(v)}
            />
            <RangePicker
              size="small"
              value={range}
              onChange={(dates) => setRange(dates as [Dayjs | null, Dayjs | null] | null)}
            />
            <Button size="small" icon={<ReloadOutlined spin={refreshing} />} onClick={onRefresh} loading={refreshing}>
              Refresh
            </Button>
          </Space>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small">
            <Table
              size="small"
              rowKey={(r, i) => `${r.product_id}-${r.location_id}-${i}`}
              columns={columns}
              dataSource={data?.rows ?? []}
              pagination={false}
              locale={{ emptyText: 'Tidak ada pergerakan stok untuk filter ini' }}
            />
          </Card>
        )}
      </div>
    </div>
  );
}
