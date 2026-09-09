import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { stockBalanceApi } from '../../api/report';
import { modelApi } from '../../api/models';

const { Title, Text } = Typography;

const fmtQty = (v: number) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

// Preset tanggal relatif terhadap hari ini
const PRESETS: { key: string; label: string; offsetDays: number }[] = [
  { key: 'today', label: 'Hari Ini', offsetDays: 0 },
  { key: 'yesterday', label: 'Kemarin', offsetDays: 1 },
  { key: 'lastweek', label: 'Minggu Lalu', offsetDays: 7 },
  { key: 'lastmonth', label: 'Bulan Lalu', offsetDays: 30 },
];

/**
 * Stock Balance — saldo stok per produk pada SATU tanggal pilihan
 * (preset Hari Ini / Kemarin / Minggu Lalu / Bulan Lalu / tanggal custom).
 * Sumber: row stock ledger aktif (agregasi di core/stock_engine.py).
 * Route: /inventory/stock_balance
 */
export default function StockBalancePage() {
  const [date, setDate] = useState<Dayjs>(() => dayjs().startOf('day'));
  const [locationId, setLocationId] = useState<number | undefined>(undefined);

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

  const today = useMemo(() => dayjs().startOf('day'), []);

  const query = useQuery({
    queryKey: ['stock-balance', date?.format('YYYY-MM-DD') ?? '', locationId ?? ''],
    queryFn: () =>
      stockBalanceApi.get({
        date: date?.format('YYYY-MM-DD') ?? undefined,
        location: locationId,
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;

  const activePreset = PRESETS.find((p) => date?.isSame(today.subtract(p.offsetDays, 'day'), 'day'));
  const dateLabel = activePreset
    ? activePreset.label
    : date
      ? date.format('DD MMM YYYY')
      : '—';

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

  const columns = [
    { title: 'Kode', dataIndex: 'code', width: 120 },
    { title: 'Produk', dataIndex: 'name' },
    { title: 'Satuan', dataIndex: 'uom', width: 90 },
    {
      title: dateLabel,
      dataIndex: 'qty',
      align: 'right' as const,
      width: 140,
      render: (v: number) => <Text strong>{fmtQty(v)}</Text>,
    },
  ];

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 900, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {data?.title ?? 'Stock Balance'}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Saldo stok per <Tag style={{ marginRight: 0 }}>{dateLabel}</Tag> · {locationLabel}
            </Text>
          </div>
          <Space wrap>
            <Select
              size="small"
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Semua Lokasi"
              style={{ width: 180 }}
              value={locationId}
              options={locationOptions}
              loading={locationsQuery.isLoading}
              onChange={(v) => setLocationId(v)}
            />
            <Button size="small" icon={<ReloadOutlined spin={refreshing} />} onClick={onRefresh} loading={refreshing}>
              Refresh
            </Button>
          </Space>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Tanggal:
          </Text>
          {PRESETS.map((p) => {
            const presetDate = today.subtract(p.offsetDays, 'day');
            const active = !!date?.isSame(presetDate, 'day');
            return (
              <Button
                key={p.key}
                size="small"
                type={active ? 'primary' : 'default'}
                onClick={() => setDate(presetDate)}
              >
                {p.label}
              </Button>
            );
          })}
          <DatePicker
            size="small"
            value={date}
            allowClear={false}
            onChange={(d) => setDate((d ?? dayjs()).startOf('day'))}
          />
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small">
            <Table
              size="small"
              rowKey="product_id"
              columns={columns}
              dataSource={data?.rows ?? []}
              pagination={false}
              locale={{ emptyText: 'Tidak ada stok pada tanggal tersebut' }}
              summary={() => {
                const t = data?.totals;
                return (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={3}>
                      <Text strong>Total</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3} align="right">
                      <Text strong>{fmtQty(t?.qty ?? 0)}</Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                );
              }}
            />
          </Card>
        )}
      </div>
    </div>
  );
}
