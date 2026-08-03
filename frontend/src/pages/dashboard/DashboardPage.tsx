import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Typography, Row, Space, Button, DatePicker, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { dashboardApi } from '../../api/dashboard';
import BlockRenderer from '../../components/dashboard/BlockRenderer';

const { Title } = Typography;
const { RangePicker } = DatePicker;

/**
 * Generic dashboard page — render block config dari backend.
 * Route: /purchase/dashboard → <DashboardPage dashboardKey="purchase" />
 * Modul lain cukup ganti dashboardKey.
 */
export default function DashboardPage({ dashboardKey }: { dashboardKey: string }) {
  const navigate = useNavigate();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const query = useQuery({
    queryKey: ['dashboard', dashboardKey, dateRange?.[0]?.format('YYYY-MM-DD') ?? '', dateRange?.[1]?.format('YYYY-MM-DD') ?? ''],
    queryFn: () =>
      dashboardApi.get(dashboardKey, {
        date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
        date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;

  // Navigasi row grid → form model (pola open-record yang sama seperti list page)
  const onNavigate = useCallback(
    (modelName: string, recordId: number) => {
      navigate(`/${modelName}/${recordId}`);
    },
    [navigate],
  );

  const onDateChange = useCallback((dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    setDateRange(dates);
  }, []);

  const onRefresh = useCallback(() => {
    query.refetch();
  }, [query]);

  if (query.isError) {
    message.error('Failed to load dashboard: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  const blocks = query.data?.blocks ?? [];

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          {query.data?.title ?? 'Dashboard'}
        </Title>
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
        <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading dashboard…</div>
      ) : (
        <Row gutter={[16, 16]}>
          {blocks.map((block) => (
            <BlockRenderer key={block.key} block={block} fields={query.data?.fields?.[block.model]} onNavigate={onNavigate} />
          ))}
        </Row>
      )}
    </div>
  );
}
