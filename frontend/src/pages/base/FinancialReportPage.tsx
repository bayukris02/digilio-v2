import { useCallback, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Table, Card, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { reportApi, type ReportSection } from '../../api/report';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const fmtIDR = (v: number) =>
  `Rp ${Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function SectionTable({ section, showSides, showBalanceCol }: {
  section: ReportSection;
  showSides?: boolean;
  showBalanceCol?: boolean;
}) {
  const columns = !showSides
    ? [
        { title: 'Kode', dataIndex: 'code', width: 120 },
        { title: 'Akun', dataIndex: 'name' },
        {
          title: 'Jumlah',
          dataIndex: 'amount',
          align: 'right' as const,
          width: 180,
          render: (v: number) => fmtIDR(v),
        },
      ]
    : [
        { title: 'Kode', dataIndex: 'code', width: 120 },
        { title: 'Akun', dataIndex: 'name' },
        {
          title: 'Debit',
          dataIndex: 'debit',
          align: 'right' as const,
          width: 170,
          render: (v: number) => fmtIDR(v),
        },
        {
          title: 'Kredit',
          dataIndex: 'credit',
          align: 'right' as const,
          width: 170,
          render: (v: number) => fmtIDR(v),
        },
        ...(showBalanceCol
          ? [
              {
                title: 'Saldo',
                dataIndex: 'amount',
                align: 'right' as const,
                width: 170,
                render: (v: number) => fmtIDR(v),
              },
            ]
          : []),
      ];

  return (
    <Table
      size="small"
      rowKey="code"
      columns={columns}
      dataSource={section.rows}
      pagination={false}
      summary={() => (
        <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={2}>
            <Text strong>Total {section.title}</Text>
          </Table.Summary.Cell>
          {showSides ? (
            <>
              <Table.Summary.Cell index={1} align="right">
                <Text strong>{fmtIDR(section.debit_subtotal ?? 0)}</Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2} align="right">
                <Text strong>{fmtIDR(section.credit_subtotal ?? 0)}</Text>
              </Table.Summary.Cell>
              {showBalanceCol && (
                <Table.Summary.Cell index={3} align="right">
                  <Text strong>{fmtIDR(section.subtotal)}</Text>
                </Table.Summary.Cell>
              )}
            </>
          ) : (
            <Table.Summary.Cell index={1} align="right">
              <Text strong>{fmtIDR(section.subtotal)}</Text>
            </Table.Summary.Cell>
          )}
        </Table.Summary.Row>
      )}
    />
  );
}

/**
 * Generic financial report page (Laba Rugi, Neraca, dst).
 * Route: /accounting/laba_rugi → <FinancialReportPage reportKey="profit_loss" />
 * Report lain cukup ganti reportKey (config di backend).
 * Konten di-center (maxWidth + margin auto) supaya tampil seperti laporan
 * keuangan; kolom Debit/Kredit/Saldo tampil otomatis jika config report
 * mengirim `show_sides` / `show_balance_col`.
 */
export default function FinancialReportPage({ reportKey }: { reportKey: string }) {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const query = useQuery({
    queryKey: ['report', reportKey, dateRange?.[0]?.format('YYYY-MM-DD') ?? '', dateRange?.[1]?.format('YYYY-MM-DD') ?? ''],
    queryFn: () =>
      reportApi.get(reportKey, {
        date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
        date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
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
    message.error('Failed to load report: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  const data = query.data;
  const periodText =
    data?.period?.date_from && data?.period?.date_to
      ? `${data.period.date_from} s/d ${data.period.date_to}`
      : 'Semua periode';

  return (
    <div style={{ padding: 16 }}>
      <div style={{ maxWidth: 900, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {data?.title ?? 'Laporan'}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {periodText}
            </Text>
          </div>
          <Space>
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
          <>
            {data?.sections?.map((section) => (
              <Card key={section.key} size="small" style={{ marginBottom: 16 }}>
                <SectionTable
                  section={section}
                  showSides={data.show_sides}
                  showBalanceCol={data.show_balance_col}
                />
              </Card>
            ))}
            {data?.totals?.map((total) => (
              <Card key={total.key} size="small" style={{ background: '#fafafa' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong style={{ fontSize: 15 }}>
                    {total.label}
                  </Text>
                  <Text strong style={{ fontSize: 15 }}>
                    {fmtIDR(total.amount)}
                  </Text>
                </div>
              </Card>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
