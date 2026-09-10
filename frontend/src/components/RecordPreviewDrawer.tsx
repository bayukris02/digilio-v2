import { useEffect, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Drawer, Table, Tag, Typography, Spin, Empty, Divider, Button, Space } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { modelApi, type FieldConfig, type ModelConfig, type PreviewViewConfig } from '../api/models';
import { formatDate } from '../utils/format';

const { Text } = Typography;

/**
 * Drawer preview meta-driven — muncul saat 1x klik baris di list view.
 *
 * Semua isi drawer dibaca dari `config.preview_view` (dibangun backend dari
 * meta model). Komponen ini 100% generik: tidak menyebut nama model/field
 * spesifik apa pun, sehingga berlaku untuk SEMUA model.
 * Model yang tidak punya `_preview_view` tetap dapat preview otomatis
 * (fallback field dari form/list view di backend).
 */
export default function RecordPreviewDrawer({
  open,
  modelName,
  recordId,
  config,
  onClose,
  onOpenRecord,
  ignoreOutsideRef,
}: {
  open: boolean;
  modelName: string;
  recordId: number | null;
  config: ModelConfig | null;
  onClose: () => void;
  onOpenRecord?: (id: number) => void;
  /** Klik di dalam elemen ini (list table) TIDAK menutup drawer — agar bisa pindah baris. */
  ignoreOutsideRef?: React.RefObject<HTMLElement | null>;
}) {
  const preview: PreviewViewConfig | null = config?.preview_view ?? null;

  // Tutup drawer saat klik di luar: di luar drawer & di luar list table.
  // Klik pada baris lain di list table tetap membiarkan drawer terbuka
  // (isi preview-nya berganti karena recordId berubah).
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      if (target.closest?.('.ant-drawer')) return; // di dalam drawer
      if (target.closest?.('.ag-popup, .ag-menu, .ag-picker-field-wrapper')) return; // popup grid
      if (ignoreOutsideRef?.current?.contains(target)) return; // di dalam list table
      closeRef.current();
    };
    document.addEventListener('mousedown', onPointerDown, true);
    return () => document.removeEventListener('mousedown', onPointerDown, true);
  }, [open, ignoreOutsideRef]);

  const detailQuery = useQuery({
    queryKey: ['record-preview', modelName, recordId],
    queryFn: () => modelApi.getRecord(modelName, recordId as number),
    enabled: open && !!modelName && recordId != null,
    staleTime: 15 * 1000,
  });

  const record = detailQuery.data ?? null;
  const fieldCfg = config?.fields ?? {};

  // ── Render nilai generik mengikuti konvensi list/form ──
  const renderValue = (field: FieldConfig | undefined, value: unknown): React.ReactNode => {
    if (value === null || value === undefined || value === '') return <Text type="secondary">—</Text>;
    const type = field?.type;
    if (type === 'monetary') return `Rp ${Number(value).toLocaleString('id-ID')}`;
    if (type === 'date' || type === 'datetime') return formatDate(value as string);
    if (type === 'boolean') return value ? '✅ Yes' : '❌ No';
    if (type === 'many2one') return (value as { name?: string })?.name ?? String(value);
    if (type === 'many2many')
      return Array.isArray(value)
        ? value.map((v) => (v as { name?: string })?.name ?? v).join(', ')
        : String(value);
    if (type === 'one2many') return Array.isArray(value) ? `${value.length} baris` : '—';
    if (type === 'selection') {
      const opt = field?.options?.find((o) => o.value === value);
      const label = opt?.label ?? String(value);
      const colors = (field as unknown as { colors?: Record<string, string> })?.colors;
      // Field ber-colors → Tag badge; tanpa colors → label polos (konsisten dengan list view)
      return colors ? <Tag color={colors[String(value)] || 'default'}>{label}</Tag> : label;
    }
    return String(value);
  };

  const Row = ({ name }: { name: string }) => {
    const field = fieldCfg[name];
    if (!field) return null;
    return (
      <div style={{ display: 'flex', gap: 12, padding: '5px 0', alignItems: 'flex-start' }}>
        <Text type="secondary" style={{ fontSize: 11, minWidth: 112, flex: '0 0 112px', lineHeight: '20px' }}>
          {field.label ?? name}
        </Text>
        <div style={{ fontSize: 13, flex: 1, wordBreak: 'break-word', lineHeight: '20px' }}>
          {renderValue(field, record?.[name])}
        </div>
      </div>
    );
  };

  const titleField = preview?.title ?? undefined;
  const statusField = preview?.status ?? undefined;
  const titleValue = titleField ? (record?.[titleField] as string | undefined) : undefined;
  const displayTitle = titleValue || (record?.display_name as string | undefined) || `#${recordId ?? ''}`;
  const statusValue = statusField ? record?.[statusField] : undefined;

  // ── Tabel baris anak (opsional) ──
  const lineColumns: ColumnsType<Record<string, unknown>> = useMemo(() => {
    const lc = preview?.lines;
    if (!lc) return [];
    const childCfg = lc.fields ?? {};
    return lc.columns.map((col) => ({
      title: lc.labels?.[col] ?? childCfg[col]?.label ?? col,
      dataIndex: col,
      key: col,
      ellipsis: true,
      render: (v: unknown) => renderValue(childCfg[col], v),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview]);

  const lineRows = preview?.lines ? ((record?.[preview.lines.field] as Record<string, unknown>[]) ?? []) : [];

  const hasContent =
    !!preview && (!!preview.sections?.length || !!preview.fields?.length || !!preview.lines);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={440}
      // Tanpa mask: list table & grid tetap bisa diklik (pindah baris tanpa
      // menutup drawer). Penutupan klik-di-luar ditangani listener mousedown
      // di atas (lihat useEffect) — klik di luar drawer & di luar list table.
      mask={false}
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text strong style={{ fontSize: 14 }}>
                {displayTitle}
              </Text>
              {statusField ? renderValue(fieldCfg[statusField], statusValue) : null}
            </div>
            {preview?.subtitle && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {renderValue(fieldCfg[preview.subtitle], record?.[preview.subtitle])}
              </Text>
            )}
          </div>
          {onOpenRecord && recordId != null && (
            <Button size="small" icon={<ExportOutlined />} onClick={() => onOpenRecord(recordId)}>
              Buka
            </Button>
          )}
        </div>
      }
      styles={{ body: { paddingTop: 12 } }}
    >
      {!hasContent ? (
        <Empty description="Preview belum tersedia untuk model ini" />
      ) : detailQuery.isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : (
        <>
          {preview?.sections?.length
            ? preview.sections.map((sec, i) => (
                <div key={sec.title || i} style={{ marginBottom: 12 }}>
                  {sec.title && (
                    <div
                      style={{
                        fontSize: 10,
                        letterSpacing: '0.6px',
                        textTransform: 'uppercase',
                        color: '#8c8c8c',
                        fontWeight: 600,
                        borderBottom: '1px solid #f0f0f0',
                        paddingBottom: 4,
                        marginBottom: 4,
                      }}
                    >
                      {sec.title}
                    </div>
                  )}
                  {sec.fields.map((f) => (
                    <Row key={f} name={f} />
                  ))}
                </div>
              ))
            : (preview?.fields ?? []).map((f) => <Row key={f} name={f} />)}

          {preview?.lines && (
            <>
              <Divider style={{ margin: '10px 0' }} />
              <div
                style={{
                  fontSize: 10,
                  letterSpacing: '0.6px',
                  textTransform: 'uppercase',
                  color: '#8c8c8c',
                  fontWeight: 600,
                  marginBottom: 6,
                }}
              >
                {preview.lines.title} ({lineRows.length})
              </div>
              <Table
                size="small"
                rowKey={(r) => String(r.id ?? Math.random())}
                columns={lineColumns}
                dataSource={lineRows}
                pagination={false}
                locale={{ emptyText: 'Tidak ada baris' }}
                scroll={{ x: 'max-content', y: 220 }}
              />
            </>
          )}

          {!record && !detailQuery.isLoading && (
            <Space style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Gagal memuat detail.
              </Text>
            </Space>
          )}
        </>
      )}
    </Drawer>
  );
}
