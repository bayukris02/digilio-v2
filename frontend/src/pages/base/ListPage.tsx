import { useMemo, useState, useRef, useCallback } from 'react';
import {
  Typography,
  Card,
  Input,
  Select,
  DatePicker,
  Space,
  Button,
  Dropdown,
  Checkbox,
  message,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  DownloadOutlined,
  SettingOutlined,
  FilterOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, ICellRendererParams } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry, themeBalham } from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);

const { Title } = Typography;
const { RangePicker } = DatePicker;

// ─── Dummy data ─────────────────────────────
interface PurchaseOrder {
  id: number;
  reference: string;
  supplier: string;
  category: string;
  orderDate: string;
  expectedDate: string;
  status: string;
  total: number;
  currency: string;
}

const statuses = ['Draft', 'Confirmed', 'Done', 'Cancelled'];
const categories = ['Raw Material', 'Finished Good', 'Service', 'Asset'];
const suppliers = [
  'PT. Sumber Berkah',
  'CV. Maju Jaya',
  'UD. Sentosa Abadi',
  'PT. Indah Logistics',
  'CV. Bumi Teknik',
];

function generateDummyData(): PurchaseOrder[] {
  const data: PurchaseOrder[] = [];
  for (let i = 1; i <= 50; i++) {
    const day = String(Math.floor(Math.random() * 28) + 1).padStart(2, '0');
    const month = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0');
    data.push({
      id: i,
      reference: `PO-2024-${String(i).padStart(4, '0')}`,
      supplier: suppliers[Math.floor(Math.random() * suppliers.length)],
      category: categories[Math.floor(Math.random() * categories.length)],
      orderDate: `2024-${month}-${day}`,
      expectedDate: `2024-${month}-${String(Math.min(Number(day) + 7, 28)).padStart(2, '0')}`,
      status: statuses[Math.floor(Math.random() * statuses.length)],
      total: Math.floor(Math.random() * 50000000) + 500000,
      currency: 'IDR',
    });
  }
  return data;
}

// ─── Cell renderers ─────────────────────────
function StatusCell(params: ICellRendererParams) {
  const colorMap: Record<string, string> = {
    Draft: 'orange',
    Confirmed: 'blue',
    Done: 'green',
    Cancelled: 'red',
  };
  return (
    <span
      style={{
        color: colorMap[params.value] || '#666',
        fontWeight: 600,
        fontSize: 11,
      }}
    >
      {params.value}
    </span>
  );
}

function CurrencyCell(params: ICellRendererParams) {
  return (
    <span style={{ fontSize: 11 }}>
      Rp {Number(params.value).toLocaleString('id-ID')}
    </span>
  );
}

export default function ListPage() {
  const gridRef = useRef<AgGridReact>(null);

  // ── State ──
  const [rowData] = useState<PurchaseOrder[]>(generateDummyData);
  const [quickFilter, setQuickFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [selectedRows, setSelectedRows] = useState<PurchaseOrder[]>([]);
  const [columnVisible, setColumnVisible] = useState<Record<string, boolean>>({
    reference: true,
    supplier: true,
    category: true,
    orderDate: true,
    expectedDate: true,
    status: true,
    total: true,
    currency: true,
  });

  // ── Selection + Row Number columns (always shown, pinned left) ──
  const selectionCol: ColDef = useMemo(
    () => ({
      field: '_selection',
      headerName: '',
      width: 44,
      minWidth: 44,
      maxWidth: 44,
      checkboxSelection: true,
      headerCheckboxSelection: true,
      resizable: false,
      sortable: false,
      filter: false,
      floatingFilter: false,
      pinned: 'left',
      lockPinned: true,
      suppressColumnsToolPanel: true,
      suppressMenu: true,
    }),
    []
  );

  const rowNoCol: ColDef = useMemo(
    () => ({
      field: '_rowNo',
      headerName: '#',
      width: 46,
      minWidth: 46,
      maxWidth: 46,
      valueGetter: (params) =>
        params.node?.rowIndex != null ? params.node.rowIndex + 1 : '',
      resizable: false,
      sortable: false,
      filter: false,
      floatingFilter: false,
      pinned: 'left',
      lockPinned: true,
      suppressColumnsToolPanel: true,
      suppressMenu: true,
      cellStyle: { textAlign: 'right', color: '#999' },
    }),
    []
  );

  // ── Column definitions ──
  const allColumns: ColDef<PurchaseOrder>[] = useMemo(
    () => [
      {
        field: 'reference',
        headerName: 'Reference',
        width: 140,
        filter: 'agTextColumnFilter',
      },
      {
        field: 'supplier',
        headerName: 'Supplier',
        width: 180,
        filter: 'agTextColumnFilter',
      },
      {
        field: 'category',
        headerName: 'Category',
        width: 130,
        filter: 'agTextColumnFilter',
      },
      {
        field: 'orderDate',
        headerName: 'Order Date',
        width: 130,
        filter: 'agDateColumnFilter',
        filterParams: { browserDatePicker: true },
      },
      {
        field: 'expectedDate',
        headerName: 'Expected',
        width: 130,
        filter: 'agDateColumnFilter',
        filterParams: { browserDatePicker: true },
      },
      {
        field: 'status',
        headerName: 'Status',
        width: 110,
        filter: 'agTextColumnFilter',
        cellRenderer: StatusCell,
      },
      {
        field: 'total',
        headerName: 'Total',
        width: 140,
        filter: 'agNumberColumnFilter',
        cellRenderer: CurrencyCell,
      },
      {
        field: 'currency',
        headerName: 'Currency',
        width: 90,
        filter: 'agTextColumnFilter',
      },
    ],
    []
  );

  // ── Visible columns (row no + selection + filtered data cols) ──
  const columns = useMemo(
    () => [rowNoCol, selectionCol, ...allColumns.filter((col) => columnVisible[col.field!])],
    [rowNoCol, selectionCol, allColumns, columnVisible]
  );

  // ── Default col def ──
  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      sortable: true,
      floatingFilter: true,
      filter: true,
      menuTabs: ['filterMenuTab', 'generalMenuTab', 'columnsMenuTab'],
    }),
    []
  );

  // ── Quick filter ──
  const onQuickFilter = useCallback((val: string) => {
    setQuickFilter(val);
  }, []);

  // ── Selection ──
  const onSelectionChanged = useCallback(() => {
    const rows = gridRef.current?.api.getSelectedRows() || [];
    setSelectedRows(rows);
  }, []);

  // ── External filters ──
  const isExternalFilterPresent = useCallback(() => {
    return !!statusFilter || !!categoryFilter || !!dateRange;
  }, [statusFilter, categoryFilter, dateRange]);

  const doesExternalFilterPass = useCallback(
    (node: { data: PurchaseOrder }) => {
      const d = node.data;
      if (statusFilter && d.status !== statusFilter) return false;
      if (categoryFilter && d.category !== categoryFilter) return false;
      if (dateRange) {
        const dDate = new Date(d.orderDate).getTime();
        const [start, end] = dateRange;
        if (dDate < new Date(start).getTime() || dDate > new Date(end).getTime()) return false;
      }
      return true;
    },
    [statusFilter, categoryFilter, dateRange]
  );

  // ── Bulk actions ──
  const bulkMenuItems = [
    {
      key: 'delete',
      label: 'Delete Selected',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        if (selectedRows.length === 0) {
          message.warning('No rows selected');
          return;
        }
        message.success(`${selectedRows.length} row(s) deleted (demo)`);
      },
    },
    {
      key: 'export',
      label: 'Export CSV',
      icon: <DownloadOutlined />,
      onClick: () => {
        gridRef.current?.api.exportDataAsCsv({ fileName: 'purchase-orders.csv' });
      },
    },
  ];

  // ── Column visibility toggles ──
  const colToggleMenuItems = allColumns.map((col) => ({
    key: col.field!,
    label: (
      <Checkbox
        checked={columnVisible[col.field!]}
        onChange={() => {
          setColumnVisible((prev) => ({
            ...prev,
            [col.field!]: !prev[col.field!],
          }));
        }}
      >
        {col.headerName}
      </Checkbox>
    ),
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Title level={4} style={{ margin: 0 }}>
        Purchase Orders
      </Title>

      {/* ═══ TOOLBAR ═══ */}
      <Card styles={{ body: { padding: '8px 12px' } }}>
        <Space wrap size={[8, 8]} style={{ width: '100%' }}>
          {/* Global search */}
          <Input
            placeholder="Search..."
            prefix={<SearchOutlined />}
            value={quickFilter}
            onChange={(e) => onQuickFilter(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />

          {/* Filter by status */}
          <Select
            placeholder="Status"
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            options={statuses.map((s) => ({ value: s, label: s }))}
            style={{ width: 120 }}
          />

          {/* Filter by category */}
          <Select
            placeholder="Category"
            allowClear
            value={categoryFilter}
            onChange={setCategoryFilter}
            options={categories.map((c) => ({ value: c, label: c }))}
            style={{ width: 140 }}
          />

          {/* Filter by date range */}
          <RangePicker
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setDateRange(null);
              }
            }}
            style={{ width: 220 }}
          />

          {/* Show/Hide columns */}
          <Dropdown menu={{ items: colToggleMenuItems }} trigger={['click']}>
            <Button icon={<SettingOutlined />}>
              Columns
            </Button>
          </Dropdown>

          {/* Bulk actions */}
          <Dropdown menu={{ items: bulkMenuItems }} trigger={['click']}>
            <Button icon={<FilterOutlined />}>
              Bulk ({selectedRows.length}) <DownOutlined />
            </Button>
          </Dropdown>
        </Space>
      </Card>

      {/* ═══ AG GRID ═══ */}
      <Card styles={{ body: { padding: 0 } }}>
        <div style={{ height: 520, width: '100%' }}>
          <AgGridReact
            ref={gridRef}
            rowData={rowData}
            columnDefs={columns}
            defaultColDef={defaultColDef}
            // Selection
            rowSelection="multiple"
            onSelectionChanged={onSelectionChanged}
            // Quick filter
            quickFilterText={quickFilter}
            // External filters
            isExternalFilterPresent={isExternalFilterPresent}
            doesExternalFilterPass={doesExternalFilterPass}
            // Pagination
            pagination
            paginationPageSize={20}
            paginationPageSizeSelector={[10, 20, 50, 100]}
            // Styling
            suppressMovableColumns={false}
            animateRows
            theme={themeBalham}
          />
        </div>
      </Card>
    </div>
  );
}
