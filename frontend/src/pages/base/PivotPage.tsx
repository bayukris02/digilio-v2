import { useCallback, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Typography, Space, Button, DatePicker, Card, message, Switch } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeBalham } from 'ag-grid-community';
import { PivotModule, ColumnsToolPanelModule } from 'ag-grid-enterprise';
import { pivotApi, type PivotColumn } from '../../api/pivot';

ModuleRegistry.registerModules([AllCommunityModule, PivotModule, ColumnsToolPanelModule]);

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/**
 * Generic pivot page — AG Grid enterprise pivot mode.
 * Route: /purchase/pivot → <PivotPage pivotKey="purchase" />
 * Modul lain cukup ganti pivotKey (config di backend).
 */
export default function PivotPage({ pivotKey }: { pivotKey: string }) {
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [pivotMode, setPivotMode] = useState(true);
  const gridRef = useRef<AgGridReact>(null);

  const query = useQuery({
    queryKey: ['pivot', pivotKey, dateRange?.[0]?.format('YYYY-MM-DD') ?? '', dateRange?.[1]?.format('YYYY-MM-DD') ?? ''],
    queryFn: () =>
      pivotApi.get(pivotKey, {
        date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
        date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
      }),
    staleTime: 30 * 1000,
  });

  const loading = query.isLoading;
  const refreshing = query.isFetching && !query.isLoading;

  const columnDefs = useMemo(
    () =>
      (query.data?.columns ?? []).map((c: PivotColumn) => ({
        headerName: c.label,
        field: c.field,
        rowGroup: c.rowGroup,
        pivot: c.pivot,
        aggFunc: c.aggFunc,
        enableRowGroup: true,
        enablePivot: true,
        enableValue: true,
      })),
    [query.data],
  );

  const defaultColDef = useMemo(() => ({ sortable: true, resizable: true, filter: true }), []);

  const onDateChange = useCallback((dates: [Dayjs | null, Dayjs | null] | null) => {
    setDateRange(dates);
  }, []);

  const onRefresh = useCallback(() => {
    query.refetch();
  }, [query]);

  const onPivotModeToggle = useCallback((checked: boolean) => {
    setPivotMode(checked);
    gridRef.current?.api.setGridOption('pivotMode', checked);
  }, []);

  const onPivotModeChanged = useCallback(() => {
    const mode = gridRef.current?.api.getGridOption('pivotMode');
    if (typeof mode === 'boolean') setPivotMode(mode);
  }, []);

  if (query.isError) {
    message.error('Failed to load pivot: ' + ((query.error as Error)?.message || 'Unknown error'));
  }

  const periodText =
    dateRange?.[0] && dateRange?.[1]
      ? `${dateRange[0].format('DD-MM-YYYY')} s/d ${dateRange[1].format('DD-MM-YYYY')}`
      : 'Semua periode';

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            {query.data?.title ?? 'Pivot'}
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {periodText}
          </Text>
        </div>
        <Space>
          <RangePicker
            size="small"
            value={dateRange}
            onChange={(dates) => onDateChange(dates as [Dayjs | null, Dayjs | null] | null)}
          />
          <Switch checked={pivotMode} onChange={onPivotModeToggle} checkedChildren="Pivot" unCheckedChildren="Grid" />
          <Button size="small" icon={<ReloadOutlined spin={refreshing} />} onClick={onRefresh} loading={refreshing}>
            Refresh
          </Button>
        </Space>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48, color: '#8c8c8c' }}>Loading pivot…</div>
      ) : (
        <Card styles={{ body: { padding: 0 } }}>
          <div style={{ height: 560, width: '100%' }}>
            <AgGridReact
              ref={gridRef}
              rowData={query.data?.rowData ?? []}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              pivotMode={pivotMode}
              onColumnPivotModeChanged={onPivotModeChanged}
              sideBar={{
                toolPanels: [
                  {
                    id: 'columns',
                    labelDefault: 'Columns',
                    labelKey: 'columns',
                    iconKey: 'columns',
                    toolPanel: 'agColumnsToolPanel',
                  },
                ],
                defaultToolPanel: 'columns',
              }}
              groupDefaultExpanded={1}
              animateRows
              theme={themeBalham}
            />
          </div>
        </Card>
      )}
    </div>
  );
}
