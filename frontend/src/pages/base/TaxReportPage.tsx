import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Select, Table, Card, message, Switch, Empty } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { taxReportApi, type TaxReportRow, type TaxReportBucket } from '../../api/report';
import { modelApi } from '../../api/models';
import { exportXlsx, numCell } from '../../utils/exportExcel';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const fmtIDR = (v: number) =>
  `Rp ${Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const fmtNum = (v: number | null | undefined) =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

type PeriodKey = 'all' | 'this_month' | 'last_month' | 'this_year';

const PERIODS: { key: PeriodKey; label: string; range: () => [Dayjs, Dayjs] | null }[] = [
  { key: 'this_month', label: 'Bulan Ini', range: () => [dayjs().startOf('month'), dayjs().endOf('month')] },
  {
    key: 'last_month',
    label: 'Bulan Lalu',
    range: () => [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')],
  },
  { key: 'this_year', label: 'Tahun Ini', range: () => [dayjs().startOf('year'), dayjs().endOf('year')] },
  { key: 'all', label: 'Semua', range: () => null },
];

/**
 * Report Pajak — rekap pajak per tag `taxes` dari baris dokumen lintas modul
 * (SO, PO, Faktur, Tagihan, Quick Sales, Quick Purchase).
 * Route: /accounting/pajak
 */
export default function TaxReportPage() {
  const [period, setPeriod] = useState<PeriodKey>('this_month');
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(() => [dayjs().startOf('month'), dayjs().endOf('month')]);
  const [moduleKeys, setModuleKeys] = useState<string[]>([]);
  const [taxIds, setTaxIds] = useState<number[]>([]);
  const [includeDraft, setIncludeDraft] = useState(true);

  // ── Master pajak (untuk filter tag) ──
  const taxesQuery = useQuery({
    queryKey: ['tax-report-masters'],
    queryFn: () => modelApi.listRecords('accounting.tax', 1, 200),
    staleTime: 60 * 1000,
  });
  const taxOptions = useMemo(
    () =>
      (taxesQuery.data?.results ?? []).map((t) => {
        const rate = Number((t as { rate?: unknown }).rate ?? 0);
        const nm = String((t as { name?: unknown }).name ?? `#${t.id}`);
        return { value: Number(t.id), label: rate ? `${nm} (${rate}%)` : nm };
      }),
    [taxesQuery.data],
  );

  const dateFrom = range?.[0]?.format('YYYY-MM-DD');
  const dateTo = range?.[1]?.format('YYYY-MM-DD');
  const modulesJoined = moduleKeys.length ? moduleKeys.join(',') : '';
  const taxesJoined = taxIds.length ? taxIds.join(',') : '';

  const query = useQuery({
    queryKey: ['tax-report', dateFrom ?? '', dateTo ?? '', modulesJoined, taxesJoined, includeDraft ? '1' : '0'],
    queryFn: () =>
      taxReportApi.get({
        date_from: dateFrom,
        date_to: dateTo,
        modules: modulesJoined || undefined,
        taxes: taxesJoined || undefined,
        include_draft: includeDraft ? '1' : '0',
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;
  const data = query.data;

  const moduleOptions = useMemo(
    () => (data?.modules ?? []).map((m) => ({ value: m.key, label: m.label })),
    [data],
  );
  const moduleLabel = (key: string) => data?.modules.find((m) => m.key === key)?.label ?? key;

  const onRefresh = useCallback(() => query.refetch(), [query]);

  const periodText = dateFrom && dateTo ? `${dayjs(dateFrom).format('DD MMM YYYY')} s/d ${dayjs(dateTo).format('DD MMM YYYY')}` : 'Semua periode';

  if (query.isError) {
    message.error('Gagal memuat report pajak: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  // ── Kolom utama (per tag pajak) ──
  const columns = [
    { title: 'Pajak', dataIndex: 'name', render: (v: string) => <Text strong>{v}</Text> },
    {
      title: 'Tarif',
      dataIndex: 'rate',
      width: 90,
      align: 'right' as const,
      render: (v: number) => <Text>{Number(v ?? 0)}%</Text>,
    },
    {
      title: 'Jenis',
      dataIndex: 'is_include',
      width: 110,
      render: (v: boolean) => (
        <Text type={v ? 'secondary' : undefined}>{v ? 'Include' : 'Exclude'}</Text>
      ),
    },
    {
      title: 'DPP',
      dataIndex: 'dpp',
      width: 170,
      align: 'right' as const,
      render: (v: number) => fmtIDR(v),
    },
    {
      title: 'Nilai Pajak',
      dataIndex: 'tax_amount',
      width: 170,
      align: 'right' as const,
      render: (v: number) => <Text strong>{fmtIDR(v)}</Text>,
    },
    { title: 'Transaksi', dataIndex: 'count', width: 100, align: 'right' as const, render: (v: number) => fmtNum(v) },
  ];

  const totals = data?.totals;

  // ── Export Excel ──
  const onExport = useCallback(() => {
    if (!data) return;
    const rows: (string | number)[][] = [
      ['Report Pajak'],
      ['Periode', periodText],
      ['Modul', moduleKeys.length ? moduleKeys.map(moduleLabel).join(', ') : 'Semua Modul'],
      ['Pajak', taxIds.length ? taxOptions.filter((o) => taxIds.includes(o.value)).map((o) => o.label).join(', ') : 'Semua Pajak'],
      ['Termasuk Draft', includeDraft ? 'Ya' : 'Tidak'],
      ['Baris tanpa tanggal', data.undated_count || 0],
      [],
      ['Pajak', 'Tarif (%)', 'Jenis', 'DPP', 'Nilai Pajak', 'Transaksi'],
    ];
    for (const r of data.rows) {
      rows.push([r.name, numCell(r.rate), r.is_include ? 'Include' : 'Exclude', numCell(r.dpp), numCell(r.tax_amount), r.count]);
      for (const [modKey, b] of Object.entries(r.by_module)) {
        rows.push([`   • ${moduleLabel(modKey)}`, '', '', numCell(b.dpp), numCell(b.tax_amount), b.count]);
      }
    }
    rows.push(['TOTAL', '', '', numCell(data.totals.dpp), numCell(data.totals.tax_amount), data.totals.count]);
    exportXlsx({
      filename: `Report_Pajak_${dateFrom ?? 'semua'}_${dateTo ?? 'semua'}.xlsx`,
      sheetName: 'Report Pajak',
      rows,
      colWidths: [34, 10, 10, 18, 18, 12],
    });
  }, [data, periodText, moduleKeys, taxIds, taxOptions, moduleLabel, includeDraft, dateFrom, dateTo]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              Report Pajak
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Rekap pajak per tag dari dokumen: {periodText}
              {includeDraft ? '' : ' · hanya dokumen terkonfirmasi'}
            </Text>
            {!!data?.undated_count && (
              <div>
                <Text type="warning" style={{ fontSize: 12 }}>
                  {data.undated_count} baris dokumen tanpa tanggal ikut dihitung (di luar rentang tanggal).
                </Text>
              </div>
            )}
          </div>
          <Space>
            <Button size="small" icon={<DownloadOutlined />} onClick={onExport} disabled={!data?.rows?.length}>
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
                Periode:
              </Text>
              {PERIODS.map((p) => (
                <Button
                  key={p.key}
                  size="small"
                  type={period === p.key ? 'primary' : 'default'}
                  onClick={() => {
                    setPeriod(p.key);
                    setRange(p.range());
                  }}
                >
                  {p.label}
                </Button>
              ))}
              <RangePicker
                size="small"
                value={range}
                onChange={(dates) => {
                  setRange(dates as [Dayjs, Dayjs] | null);
                  setPeriod('all');
                }}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Modul:
              </Text>
              <Select
                size="small"
                mode="multiple"
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="Semua Modul"
                style={{ minWidth: 200, maxWidth: 320 }}
                value={moduleKeys}
                options={moduleOptions}
                onChange={(v) => setModuleKeys(v)}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Pajak:
              </Text>
              <Select
                size="small"
                mode="multiple"
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="Semua Pajak"
                style={{ minWidth: 200, maxWidth: 320 }}
                value={taxIds}
                options={taxOptions}
                loading={taxesQuery.isLoading}
                onChange={(v) => setTaxIds(v)}
              />
            </Space>
            <Space size={4} align="center">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Termasuk Draft:
              </Text>
              <Switch size="small" checked={includeDraft} onChange={setIncludeDraft} />
            </Space>
          </div>
        </Card>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading report…</div>
        ) : (
          <Card size="small">
            {data?.rows?.length ? (
              <Table<TaxReportRow>
                size="small"
                rowKey="tax_id"
                columns={columns}
                dataSource={data.rows}
                pagination={false}
                expandable={{
                  expandedRowRender: (row) => (
                    <Table
                      size="small"
                      rowKey="key"
                      pagination={false}
                      dataSource={Object.entries(row.by_module).map(([key, b]) => ({ key, ...(b as TaxReportBucket) }))}
                      columns={[
                        { title: 'Modul', dataIndex: 'key', render: (k: string) => moduleLabel(k), width: 200 },
                        { title: 'DPP', dataIndex: 'dpp', align: 'right' as const, width: 170, render: (v: number) => fmtIDR(v) },
                        {
                          title: 'Nilai Pajak',
                          dataIndex: 'tax_amount',
                          align: 'right' as const,
                          width: 170,
                          render: (v: number) => fmtIDR(v),
                        },
                        { title: 'Transaksi', dataIndex: 'count', align: 'right' as const, width: 100, render: (v: number) => fmtNum(v) },
                      ]}
                    />
                  ),
                }}
                summary={() =>
                  totals ? (
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0} colSpan={3}>
                        <Text strong>Total</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={3} align="right">
                        <Text strong>{fmtIDR(totals.dpp)}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={4} align="right">
                        <Text strong>{fmtIDR(totals.tax_amount)}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right">
                        <Text strong>{fmtNum(totals.count)}</Text>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  ) : null
                }
              />
            ) : (
              <Empty description="Tidak ada transaksi ber-pajak pada periode ini" />
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
