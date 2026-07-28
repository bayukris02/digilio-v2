import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Card, Input, Select, DatePicker, Space, Button, Dropdown, Checkbox, message, Spin, Popover, Radio, Modal, Tag,
} from 'antd';
import {
  SearchOutlined, DeleteOutlined, DownloadOutlined, SettingOutlined, FilterOutlined, DownOutlined, PlusOutlined, BarsOutlined, UploadOutlined,
} from '@ant-design/icons';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, ICellRendererParams } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry, themeBalham } from 'ag-grid-community';
import { RowGroupingModule } from 'ag-grid-enterprise';
import { modelApi, type ModelConfig, type FieldConfig } from '../../api/models';
import { formatDate, parseDate } from '../../utils/format';
import { modelNameToApi } from '../../config/urlModelMap';
import ImportModal from '../../components/ImportModal';

ModuleRegistry.registerModules([AllCommunityModule, RowGroupingModule]);

const { Title } = Typography;

export default function ModelListPage() {
  const { modelName } = useParams<{ modelName: string }>();
  const apiModelName = modelName ? modelNameToApi(modelName) : '';
  const navigate = useNavigate();
  const gridRef = useRef<AgGridReact>(null);

  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [quickFilter, setQuickFilter] = useState('');
  const [selectedRows, setSelectedRows] = useState<Record<string, unknown>[]>([]);
  const [filterValues, setFilterValues] = useState<Record<string, string | null>>({});
  const [groupByField, setGroupByField] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // ── AG Grid handles pagination & search client-side (all records loaded) ──

  // ── Fetch config + all records ──
  // Load all records once — AG Grid handles pagination & search client-side
  useEffect(() => {
    if (!apiModelName) return;
    setLoading(true);

    Promise.all([
      modelApi.getConfig(apiModelName),
      modelApi.listRecords(apiModelName, 1, 0),  // page_size=0 = all records
    ])
      .then(([cfg, resp]) => {
        setConfig(cfg);
        setRecords(resp.results);
      })
      .catch((err) => {
        message.error('Failed to load model: ' + (err?.message || 'Unknown error'));
      })
      .finally(() => setLoading(false));
  }, [apiModelName]);

  // ── Build AG Grid columns from field config ──
  const fieldList = useMemo(() => {
    if (!config) return [];
    const allFields = Object.entries(config.fields)
      .filter(([_, f]) => f.type !== 'one2many')
      .map(([key, field]) => ({ key, field }));

    // Use list_view.columns if defined (preserving order), else fallback to all fields
    const columnOrder = config.list_view?.columns;
    if (columnOrder && columnOrder.length > 0) {
      const fieldMap = new Map(allFields.map((f) => [f.key, f]));
      return columnOrder
        .filter((k: string) => fieldMap.has(k))
        .map((k: string) => fieldMap.get(k)!);
    }
    // Fallback: auto-generate columns, exclude long text fields
    return allFields.filter((f) => f.field.type !== 'text');
  }, [config]);

  const columns = useMemo<ColDef[]>(() => {
    return [
      // Row number column
      {
        field: '_row',
        headerName: '#',
        width: 56,
        minWidth: 56,
        resizable: false,
        sortable: false,
        filter: false,
        pinned: 'left' as const,
        valueGetter: (params) => {
          // Use forEachNodeAfterFilterAndSort so row numbers are sequential
          // even after quickFilterText or column filter is active
          if (params.api) {
            let idx = -1;
            params.api.forEachNodeAfterFilterAndSort((node, index) => {
              if (node.data?.id === params.data?.id) {
                idx = index;
              }
            });
            if (idx >= 0) return idx + 1;
          }
          return (params.node?.rowIndex ?? 0) + 1;
        },
      },
      ...fieldList.map(({ key, field }) => {
      const col: ColDef = {
        field: key,
        headerName: field.label,
        sortable: true,
        resizable: true,
        filter: true,
        floatingFilter: true,
      };

      if (field.type === 'monetary') {
        col.cellRenderer = (params: ICellRendererParams) => {
          const val = params.value;
          return <span>Rp {Number(val).toLocaleString('id-ID')}</span>;
        };
        col.filter = 'agNumberColumnFilter';
      } else if (field.type === 'date') {
        col.filter = 'agDateColumnFilter';
        col.filterParams = { browserDatePicker: true };
        col.cellRenderer = (params: ICellRendererParams) => (
          <span>{formatDate(params.value)}</span>
        );
      } else if (field.type === 'selection') {
        col.filter = 'agTextColumnFilter';
        const fieldColors = (field as Record<string, unknown>).colors as Record<string, string> | undefined;
        if (fieldColors) {
          col.cellRenderer = (params: ICellRendererParams) => {
            const label = field.options?.find(
              (o: { value: string; label: string }) => o.value === params.value,
            )?.label || params.value;
            const color = fieldColors[params.value as string] || 'default';
            return <Tag color={color}>{label}</Tag>;
          };
        }
      } else if (field.type === 'boolean') {
        col.cellRenderer = (params: ICellRendererParams) => (
          <span>{params.value ? '✅ Yes' : '❌ No'}</span>
        );
      } else if (field.type === 'integer') {
        col.filter = 'agNumberColumnFilter';
      } else if (field.type === 'many2one') {
        col.valueGetter = (params: Record<string, unknown>) => {
          const val = (params as any).data?.[key];
          return (val as Record<string, unknown>)?.name as string || '';
        };
        col.cellRenderer = (params: ICellRendererParams) => {
          return <span>{params.value}</span>;
        };
      }

      return col;
    }),
  ];
  }, [fieldList]);

  const defaultColDef = useMemo<ColDef>(() => ({
    resizable: true,
    sortable: true,
    floatingFilter: true,
    filter: true,
  }), []);

  // ── Filter configs from list_view ──
  const filterConfigs = useMemo(() => {
    if (!config?.list_view?.filters) return [];
    return config.list_view.filters
      .map((key: string) => {
        const field = config.fields[key];
        if (!field) return null;
        return { key, field };
      })
      .filter(Boolean) as { key: string; field: FieldConfig }[];
  }, [config]);

  // ── Filter change handler ──
  const onFilterChange = useCallback((fieldKey: string, value: string | null) => {
    setFilterValues((prev) => {
      const next = { ...prev };
      if (!value || value === '') {
        delete next[fieldKey];
      } else {
        next[fieldKey] = value;
      }
      // Apply to AG Grid filter model
      if (gridRef.current?.api) {
        const model = gridRef.current.api.getFilterModel() || {};
        if (next[fieldKey] === undefined) {
          delete model[fieldKey];
        } else {
          model[fieldKey] = { type: 'equals', filter: next[fieldKey] };
        }
        gridRef.current.api.setFilterModel(Object.keys(model).length > 0 ? model : null);
      }
      return next;
    });
  }, []);

  // ── Group by options from list_view ──
  const groupByOptions = useMemo(() => {
    if (!config?.list_view?.group_by) return [];
    return config.list_view.group_by
      .map((key: string) => {
        const field = config.fields[key];
        if (!field) return null;
        return { key, label: field.label };
      })
      .filter(Boolean) as { key: string; label: string }[];
  }, [config]);

  // ── Handlers ──
  const onQuickFilter = useCallback((val: string) => {
    setQuickFilter(val);
  }, []);

  const onSelectionChanged = useCallback(() => {
    const rows = gridRef.current?.api.getSelectedRows() || [];
    setSelectedRows(rows);
  }, []);

  // ── Apply row grouping via Column API (dynamic) ──
  useEffect(() => {
    if (!gridRef.current?.api) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gridApi = gridRef.current.api as any;
    if (groupByField) {
      gridApi.setRowGroupColumns([groupByField]);
    } else {
      gridApi.setRowGroupColumns([]);
    }
  }, [groupByField]);

  if (loading || !config) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>{config.verbose_name_plural}</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate(`/${modelName}/new`)}
        >
          New
        </Button>
      </div>

      {/* ═══ TOOLBAR ═══ */}
      <Card styles={{ body: { padding: '8px 12px' } }}>
        <Space wrap size={[8, 8]}>
          <Dropdown
            menu={{
              items: [
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
                    Modal.confirm({
                      title: `Delete ${selectedRows.length} record(s)?`,
                      content: 'This will soft-delete the selected records.',
                      okText: 'Yes, Delete',
                      okType: 'danger',
                      cancelText: 'Cancel',
                      onOk: async () => {
                        try {
                          for (const row of selectedRows) {
                            await modelApi.deleteRecord(apiModelName, row.id as number);
                          }
                          message.success(`${selectedRows.length} record(s) deleted`);
                          // Refresh list
                          const resp = await modelApi.listRecords(apiModelName, 1, 0);
                          setRecords(resp.results);
                          setSelectedRows([]);
                        } catch (err) {
                          message.error((err as Error)?.message || 'Delete failed');
                        }
                      },
                    });
                  },
                },
                {
                  key: 'export',
                  label: 'Export CSV',
                  icon: <DownloadOutlined />,
                  onClick: () => {
                    gridRef.current?.api.exportDataAsCsv({
                      fileName: `${modelName}.csv`,
                      columnKeys: fieldList.map(f => f.key),
                      processCellCallback: (params) => {
                        const val = params.value;
                        if (val && typeof val === 'object' && !Array.isArray(val)) {
                          return (val as Record<string, unknown>)?.name ?? '';
                        }
                        return val;
                      },
                    });
                  },
                },
                {
                  key: 'import',
                  label: 'Import CSV / Excel',
                  icon: <UploadOutlined />,
                  onClick: () => setImportModalOpen(true),
                },
              ],
            }}
            trigger={['click']}
          >
            <Button icon={<FilterOutlined />}>
              Bulk ({selectedRows.length}) <DownOutlined />
            </Button>
          </Dropdown>
          <Input
            placeholder="Search..."
            prefix={<SearchOutlined />}
            value={quickFilter}
            onChange={(e) => onQuickFilter(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          {filterConfigs.length > 0 && (
            <Popover
              trigger="click"
              placement="bottomLeft"
              title="Filter"
              content={
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 220 }}>
                  {filterConfigs.map(({ key, field }) => {
                    if (field.type === 'selection' && field.options) {
                      return (
                        <div key={key}>
                          <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{field.label}</div>
                          <Select
                            placeholder={`All ${field.label}`}
                            allowClear
                            style={{ width: '100%' }}
                            value={filterValues[key] || undefined}
                            onChange={(val) => onFilterChange(key, val ?? null)}
                            options={field.options.map((o) => ({ value: o.value, label: o.label }))}
                          />
                        </div>
                      );
                    }
                    if (field.type === 'date') {
                      return (
                        <div key={key}>
                          <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{field.label}</div>
                          <DatePicker
                            placeholder={field.label}
                            style={{ width: '100%' }}
                            value={filterValues[key] ? parseDate(filterValues[key]!) : undefined}
                            onChange={(date) => {
                              const val = date ? date.format('YYYY-MM-DD') : null;
                              onFilterChange(key, val);
                            }}
                          />
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>
              }
            >
              <Button icon={<FilterOutlined />}>
                Filter {Object.keys(filterValues).length > 0 && `(${Object.keys(filterValues).length})`}
              </Button>
            </Popover>
          )}
          {groupByOptions.length > 0 && (
            <Popover
              trigger="click"
              placement="bottomLeft"
              title="Group By"
              content={
                <div style={{ minWidth: 160 }}>
                  <Radio.Group
                    value={groupByField}
                    onChange={(e) => setGroupByField(e.target.value || null)}
                  >
                    <Space orientation="vertical" style={{ width: '100%' }}>
                      <Radio value="">None</Radio>
                      {groupByOptions.map((opt) => (
                        <Radio key={opt.key} value={opt.key}>{opt.label}</Radio>
                      ))}
                    </Space>
                  </Radio.Group>
                </div>
              }
            >
              <Button icon={<BarsOutlined />}>
                Group {groupByField ? `· ${groupByOptions.find(o => o.key === groupByField)?.label}` : ''}
              </Button>
            </Popover>
          )}
        </Space>
      </Card>

      {/* ═══ AG GRID ═══ */}
      <Card styles={{ body: { padding: 0 } }}>
        <div style={{ height: 520, width: '100%' }}>
          <AgGridReact
            ref={gridRef}
            rowData={records}
            columnDefs={columns}
            defaultColDef={defaultColDef}
            groupDefaultExpanded={0}
            rowSelection={{ mode: 'multiRow', selectAll: 'filtered' }}
            onSelectionChanged={onSelectionChanged}
            quickFilterText={quickFilter}
            pagination={true}
            paginationPageSize={50}
            paginationPageSizeSelector={[10, 20, 50, 100]}
            animateRows
            theme={themeBalham}
            onRowDoubleClicked={(e) => {
              if (e.data?.id) {
                navigate(`/${modelName}/${e.data.id}`);
              }
            }}
          />
        </div>
      </Card>
      <ImportModal
        open={importModalOpen}
        modelName={modelName!}
        apiModelName={apiModelName}
        onClose={() => setImportModalOpen(false)}
        onSuccess={async () => {
          const resp = await modelApi.listRecords(apiModelName, 1, 0);
          setRecords(resp.results);
        }}
      />
    </div>
  );
}
