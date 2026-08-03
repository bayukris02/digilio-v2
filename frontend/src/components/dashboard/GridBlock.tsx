import { useMemo, useState, useCallback } from 'react';
import { Input, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, ICellRendererParams } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry, themeBalham } from 'ag-grid-community';
import { RowGroupingModule } from 'ag-grid-enterprise';
import type { DashboardBlock } from '../../api/dashboard';
import type { FieldConfig } from '../../api/models';
import { formatDate } from '../../utils/format';

ModuleRegistry.registerModules([AllCommunityModule, RowGroupingModule]);

const { Search } = Input;

export default function GridBlock({
  block,
  fields,
  onNavigate,
}: {
  block: DashboardBlock;
  fields?: Record<string, FieldConfig>;
  onNavigate?: (modelName: string, recordId: number) => void;
}) {
  const rows = block.data.rows ?? [];
  const count = block.data.count ?? rows.length;
  const [quickFilter, setQuickFilter] = useState('');

  // ── Summary block: kolom label/count/value — value format tergantung aggregate ──
  // ── Grid block: kolom dari block.columns + config field ──
  const columns = useMemo<ColDef[]>(() => {
    if (block.type === 'summary') {
      const labelField = fields?.[block.group_by ?? ''];
      const isMoney = block.aggregate?.func === 'sum';
      return [
        {
          field: 'label',
          headerName: labelField?.label ?? block.group_by ?? 'Label',
          sortable: true,
          filter: true,
          flex: 2,
          minWidth: 160,
        },
        {
          field: 'count',
          headerName: 'Records',
          sortable: true,
          filter: 'agNumberColumnFilter',
          width: 110,
          valueFormatter: (p) => Number(p.value ?? 0).toLocaleString('id-ID'),
        },
        {
          field: 'value',
          headerName: 'Total',
          sortable: true,
          filter: 'agNumberColumnFilter',
          width: 140,
          cellRenderer: (p: ICellRendererParams) =>
            isMoney
              ? `Rp ${Number(p.value ?? 0).toLocaleString('id-ID')}`
              : Number(p.value ?? 0).toLocaleString('id-ID'),
        },
      ];
    }

    const cols = (block.columns ?? []).map((key) => {
      const field = fields?.[key];
      const col: ColDef = {
        field: key,
        headerName: field?.label ?? key,
        sortable: true,
        resizable: true,
        filter: true,
        floatingFilter: true,
        flex: 1,
        minWidth: 110,
      };
      const ftype = field?.type;
      if (ftype === 'monetary') {
        col.filter = 'agNumberColumnFilter';
        col.cellRenderer = (p: ICellRendererParams) =>
          `Rp ${Number(p.value ?? 0).toLocaleString('id-ID')}`;
      } else if (ftype === 'date') {
        col.filter = 'agDateColumnFilter';
        col.filterParams = { browserDatePicker: true };
        col.cellRenderer = (p: ICellRendererParams) => formatDate(p.value as string);
      } else if (ftype === 'selection') {
        col.filter = 'agTextColumnFilter';
        const colors = ((field as Record<string, unknown> | undefined)?.colors ?? {}) as Record<string, string>;
        col.cellRenderer = (p: ICellRendererParams) => {
          const label =
            field?.options?.find((o) => o.value === p.value)?.label ?? String(p.value ?? '');
          const color = colors[String(p.value)] || 'default';
          return <Tag color={color}>{label}</Tag>;
        };
      } else if (ftype === 'many2one') {
        col.valueGetter = (params: { data?: Record<string, unknown> }) => {
          const v = params.data?.[key];
          return (v as Record<string, unknown> | undefined)?.name as string || '';
        };
        col.cellRenderer = (p: ICellRendererParams) => <span>{p.value}</span>;
      }
      return col;
    });
    return cols;
  }, [block, fields]);

  const onRowClicked = useCallback(
    (params: { data?: Record<string, unknown> }) => {
      const id = params.data?.id as number | undefined;
      if (id != null && onNavigate && block.type === 'grid') {
        onNavigate(block.model, id);
      }
    },
    [onNavigate, block],
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: '#8c8c8c' }}>
          {count.toLocaleString('id-ID')} records
        </span>
        <Search
          placeholder="Quick filter"
          allowClear
          size="small"
          style={{ width: 200 }}
          prefix={<SearchOutlined />}
          onSearch={setQuickFilter}
          onChange={(e) => !e.target.value && setQuickFilter('')}
        />
      </div>
      <div className="ag-theme-balham" style={{ height: block.height ?? 340 }}>
        <AgGridReact
          rowData={rows}
          columnDefs={columns}
          defaultColDef={{ resizable: true, sortable: true }}
          theme={themeBalham}
          quickFilterText={quickFilter}
          onRowClicked={onRowClicked}
          pagination
          paginationPageSize={10}
          paginationPageSizeSelector={[10, 20, 50, 100]}
          domLayout="autoHeight"
          suppressCellFocus
        />
      </div>
    </div>
  );
}
