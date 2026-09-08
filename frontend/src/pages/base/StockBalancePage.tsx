import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { stockBalanceApi } from '../../api/report';
import { modelApi } from '../../api/models';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const fmtQty = (v: number) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

/**
 * Stock Balance — laporan saldo stok per produk, bersumber dari row stock
 * ledger (agregasi di core/stock_engine.py -> StockEngine.stock_balance).
 * Route: /inventory/stock_balance
 */
export default function StockBalancePage() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);
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

  const query = useQuery({
    queryKey: [
      'stock-balance',
      dateRange?.[0]?.format('YYYY-MM-DD') ?? '',
      dateRange?.[1]?.format('YYYY-MM-DD') ?? '',
      locationId ?? '',
    ],
    queryFn: () =>
      stockBalanceApi.get({
        date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
        date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
        location: locationId,
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;

  const onDateChange = useCallback((dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    setDateRange(dates);
  }, []);

  const onRefresh = useCallback(() => {
    query.refetch();
  }, [query]);

  if (query.isError) {
    message.error('Gagal memuat laporan: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  const data = query.data;
  const periodText =
    data?.period?.date_from && data?.period?.date_to
      ? `${data.period.date_from} s/d ${data.period.date_to}`
      : 'Semua periode';

  const columns = [
    { title: 'Kode', dataIndex: 'code', width: 110 },
    { title: 'Produk', dataIndex: 'name' },
    { title: 'Satuan', dataIndex: 'uom', width: 90 },
    {
      title: 'Saldo Awal',
      dataIndex: 'opening',
      align: 'right' as const,
      width: 130,
      render: (v: number) => fmtQty(v),
    },
    {
      title: 'Masuk',
      dataIndex: 'qty_in',
      align: 'right' as const,
      width: 110,
      render: (v: number) => fmtQty(v),
    },
    {
      title: 'Keluar',
      dataIndex: 'qty_out',
      align: 'right' as const,
      width: 110,
      render: (v: number) => fmtQty(v),
    },
    {
      title: 'Saldo Akhir',
      dataIndex: 'closing',
      align: 'right' as const,
      width: 130,
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
              {periodText}
            </Text>
          </div>
          <Space>
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
            <RangePicker
              size="small"
              value={dateRange}
              onChange={(dates) => onDateChange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
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
              rowKey="product_id"
              columns={columns}
              dataSource={data?.rows ?? []}
              pagination={false}
              locale={{ emptyText: 'Tidak ada pergerakan stok' }}
              summary={() => {
                const t = data?.totals;
                return (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={3}>
                      <Text strong>Total</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3} align="right">
                      <Text strong>{fmtQty(t?.opening ?? 0)}</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={4} align="right">
                      <Text strong>{fmtQty(t?.qty_in ?? 0)}</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={5} align="right">
                      <Text strong>{fmtQty(t?.qty_out ?? 0)}</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={6} align="right">
                      <Text strong>{fmtQty(t?.closing ?? 0)}</Text>
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
