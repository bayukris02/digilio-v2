import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Typography, Card, Button, Input, Table, Alert, Space, Tag, Modal, Spin, Select, message,
} from 'antd';
import { DeleteOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons';
import {
  maintenanceApi, type PurgeBranchOption, type PurgeOption, type PurgeResult, type PurgeRow, type PurgeScope,
} from '../../api/maintenance';

const { Title, Text } = Typography;

const labelStyle = { fontSize: 12 } as const;
const dangerBtn = { background: '#cf1322', borderColor: '#cf1322', color: '#fff' } as const;

/** Info data yang disisakan (dari preview) ditampilkan sebagai baris tag. */
function KeptInfo({
  company, branch, users, sequences,
}: {
  company?: string | null; branch?: string | null; users?: number; sequences?: number;
}) {
  return (
    <Space size={6} wrap>
      <Text type="secondary" style={labelStyle}>Disisakan:</Text>
      <Tag color="green">Company: {company ?? '—'}</Tag>
      <Tag color="green">Branch: {branch ?? '—'}</Tag>
      <Tag color="green">{users ?? 0} user (login)</Tag>
      <Tag color="blue">{sequences ?? 0} Sequence</Tag>
      <Text type="secondary" style={labelStyle}>(konfigurasi nomor tetap, counter direset ke 1)</Text>
    </Space>
  );
}

/** Baris keterangan untuk counter nomor dokumen yang direset (bukan dihapus). */
function ResetLine({ resets }: { resets?: PurgeRow[] }) {
  if (!resets?.length) return null;
  const total = resets.reduce((a, r) => a + r.count, 0);
  return (
    <div style={{ marginTop: 8 }}>
      <Text type="secondary" style={labelStyle}>
        <Tag color="orange">Reset</Tag>
        Counter nomor dokumen — <b>{total.toLocaleString('id-ID')}</b> baris counter dihapus supaya
        penomoran mulai dari <b>1</b> lagi. Definisi Sequence tidak dihapus.
      </Text>
    </div>
  );
}

/** Satu bagian clear: ringkasan + input konfirmasi + tombol hapus. */
function PurgeCard({
  scope,
  data,
  loading,
  keepOptions,
  keep,
  onKeepChange,
  onDone,
}: {
  scope: 'transactions' | 'master';
  data?: PurgeScope;
  loading: boolean;
  /** pilihan Company/Branch yang disisakan (hanya scope master) */
  keepOptions?: { companies: PurgeOption[]; branches: PurgeBranchOption[] };
  keep?: { company: number | null; branch: number | null };
  onKeepChange?: (next: { company: number | null; branch: number | null }) => void;
  onDone: (res: PurgeResult) => void;
}) {
  const [confirmText, setConfirmText] = useState('');
  const phrase = data?.phrase ?? '';
  const match = confirmText.trim().toUpperCase() === phrase;

  const mutation = useMutation({
    mutationFn: () =>
      maintenanceApi.run(
        scope,
        confirmText.trim(),
        scope === 'master'
          ? { keep_company: keep?.company ?? null, keep_branch: keep?.branch ?? null }
          : undefined,
      ),
    onSuccess: (res) => {
      setConfirmText('');
      onDone(res);
    },
    onError: (e: Error) => message.error(e.message || 'Gagal menghapus data'),
  });

  // Branch yang tersedia = milik Company yang dipilih (disisakan).
  const branchOptions = (keepOptions?.branches ?? []).filter(
    (b) => !keep?.company || b.company_id === keep.company,
  );

  return (
    <Card
      size="small"
      style={{ marginBottom: 12, borderColor: '#ffccc7' }}
      title={
        <Space>
          <DeleteOutlined style={{ color: '#cf1322' }} />
          <Text strong>{data?.title ?? (scope === 'transactions' ? 'Hapus Transaksi' : 'Hapus Master Data')}</Text>
        </Space>
      }
      extra={<Tag color="red">{data?.total ?? 0} baris</Tag>}
    >
      <Text type="secondary" style={labelStyle}>{data?.desc}</Text>

      {scope === 'master' && keepOptions ? (
        <Space size={16} wrap style={{ marginTop: 10 }}>
          <Space size={4}>
            <Text strong style={labelStyle}>Company disisakan:</Text>
            <Select
              size="small"
              style={{ width: 240 }}
              value={keep?.company ?? undefined}
              placeholder="Pilih company"
              options={keepOptions.companies.map((c) => ({ value: c.id, label: c.name }))}
              onChange={(v) => onKeepChange?.({ company: v as number, branch: null })}
            />
          </Space>
          <Space size={4}>
            <Text strong style={labelStyle}>Branch disisakan:</Text>
            <Select
              size="small"
              style={{ width: 200 }}
              value={keep?.branch ?? undefined}
              placeholder="Pilih branch"
              options={branchOptions.map((b) => ({ value: b.id, label: b.name }))}
              onChange={(v) => onKeepChange?.({ company: keep?.company ?? null, branch: v as number })}
            />
          </Space>
          <Text type="secondary" style={labelStyle}>
            User tidak dihapus (login tetap aman). Company/Branch lain ikut dihapus.
          </Text>
        </Space>
      ) : null}

      <div style={{ marginTop: 10 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
        ) : (
          <Table
            size="small"
            bordered
            rowKey="model"
            pagination={false}
            scroll={{ y: 240 }}
            dataSource={data?.rows ?? []}
            locale={{ emptyText: 'Tidak ada data untuk dihapus' }}
            columns={[
              {
                title: 'Model',
                dataIndex: 'label',
                key: 'label',
                render: (v: string, row: PurgeRow) => (
                  <>
                    {v}
                    <Text type="secondary" style={{ ...labelStyle, marginLeft: 8 }}>{row.model}</Text>
                  </>
                ),
              },
              {
                title: 'Jumlah',
                dataIndex: 'count',
                key: 'count',
                align: 'right' as const,
                width: 110,
                render: (v: number) => <Text strong>{v.toLocaleString('id-ID')}</Text>,
              },
            ]}
            summary={() =>
              (data?.rows?.length ?? 0) ? (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>
                    <Text strong>Total {data?.models ?? 0} model</Text>
                    {scope === 'transactions' && data?.chatter ? (
                      <Text type="secondary" style={{ marginLeft: 8, ...labelStyle }}>
                        + {data.chatter.toLocaleString('id-ID')} log chatter
                      </Text>
                    ) : null}
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="right">
                    <Text strong>{((data?.total ?? 0) + (scope === 'transactions' ? data?.chatter ?? 0 : 0)).toLocaleString('id-ID')}</Text>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              ) : null
            }
          />
        )}
        <ResetLine resets={data?.resets} />
      </div>

      <Space style={{ marginTop: 12 }} wrap>
        <Text strong style={labelStyle}>Ketik “{phrase}”:</Text>
        <Input
          size="small"
          style={{ width: 240 }}
          value={confirmText}
          placeholder={phrase}
          onChange={(e) => setConfirmText(e.target.value)}
          onPressEnter={() => { if (match) mutation.mutate(); }}
        />
        <Button
          size="small"
          icon={<DeleteOutlined />}
          style={match ? dangerBtn : undefined}
          danger={!match}
          disabled={!match || mutation.isPending}
          loading={mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {data?.title ?? 'Hapus'}
        </Button>
      </Space>
    </Card>
  );
}

/**
 * Pemeliharaan Data (Pengaturan) — clear database.
 *
 * Dua aksi:
 *   1. Hapus Transaksi      : semua dokumen/baris/pergerakan stok + log chatter.
 *   2. Hapus Master Data    : semua master data, menyisakan 1 Company, 1 Branch, user (auth).
 *
 * Backup otomatis (JSON) dibuat backend sebelum penghapusan; hasil ditampilkan setelah selesai.
 * Route: /settings/data_maintenance
 */
export default function DataMaintenancePage() {
  const qc = useQueryClient();
  const [result, setResult] = useState<PurgeResult | null>(null);
  /** Company & Branch yang disisakan (pilihan user; awalnya dari server). */
  const [keep, setKeep] = useState<{ company: number | null; branch: number | null } | null>(null);

  const preview = useQuery({
    queryKey: ['purge-preview'],
    queryFn: maintenanceApi.preview,
    staleTime: 0,
    refetchOnMount: 'always',
  });
  const kept = preview.data?.kept;
  const options = preview.data?.options;

  useEffect(() => {
    if (!keep && kept?.company) {
      setKeep({ company: kept.company.id, branch: kept.branch?.id ?? null });
    }
  }, [keep, kept]);

  /** Ganti company → branch otomatis ke branch pertama milik company tsb. */
  const handleKeepChange = (next: { company: number | null; branch: number | null }) => {
    if (next.branch || !next.company) {
      setKeep(next);
      return;
    }
    const first = (options?.branches ?? []).find((b) => b.company_id === next.company);
    setKeep({ company: next.company, branch: first?.id ?? null });
  };

  const selCompany = keep?.company ?? kept?.company?.id ?? null;
  const selBranch = keep?.branch ?? kept?.branch?.id ?? null;
  const companyName = options?.companies.find((c) => c.id === selCompany)?.name ?? kept?.company?.name ?? null;
  const branchName = options?.branches.find((b) => b.id === selBranch)?.name ?? kept?.branch?.name ?? null;

  const handleDone = (res: PurgeResult) => {
    setResult(res);
    preview.refetch();
    qc.invalidateQueries({ queryKey: ['model-records'] });
    qc.invalidateQueries({ queryKey: ['purge-preview'] });
    message.success(`${res.title}: ${res.total.toLocaleString('id-ID')} baris dihapus`);
  };

  return (
    <div style={{ padding: 8, width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>Pemeliharaan Data</Title>
          <Text type="secondary" style={labelStyle}>
            Bersihkan database: hapus data transaksi atau master data. Aksi ini permanen —
            backup JSON otomatis dibuat sebelum proses.
          </Text>
          <div style={{ marginTop: 6 }}>
            <KeptInfo company={companyName} branch={branchName} users={kept?.users} sequences={kept?.sequences} />
          </div>
        </div>
        <Button size="small" icon={<ReloadOutlined spin={preview.isFetching} />} onClick={() => preview.refetch()}>
          Refresh
        </Button>
      </div>

      <Alert
        type="warning"
        showIcon
        icon={<SafetyOutlined />}
        style={{ marginBottom: 12 }}
        message="Urutan yang disarankan"
        description={
          <Text style={labelStyle}>
            Jalankan <b>Hapus Transaksi</b> lebih dulu, baru <b>Hapus Master Data</b> — supaya tidak ada
            dokumen yang kehilangan relasi ke master. Nomor dokumen di-<b>reset mulai dari 1</b>
            (counter Sequence dikosongkan); definisi Sequence/prefix tidak dihapus dan tidak muncul
            sebagai data yang dihapus.
          </Text>
        }
      />

      {preview.isError ? (
        <Alert
          type="error"
          showIcon
          message="Gagal memuat ringkasan data"
          description={<Text style={labelStyle}>{(preview.error as Error)?.message}. Halaman ini hanya untuk admin (staff).</Text>}
        />
      ) : (
        <>
          <PurgeCard
            scope="transactions"
            data={preview.data?.transactions}
            loading={preview.isLoading}
            onDone={handleDone}
          />
          <PurgeCard
            scope="master"
            data={preview.data?.master}
            loading={preview.isLoading}
            keepOptions={options}
            keep={keep ?? undefined}
            onKeepChange={handleKeepChange}
            onDone={handleDone}
          />
        </>
      )}

      <Modal
        open={!!result}
        title={result?.title}
        onOk={() => setResult(null)}
        onCancel={() => setResult(null)}
        okText="Tutup"
        width={620}
      >
        <Text style={labelStyle}>
          Total <b>{result?.total.toLocaleString('id-ID')}</b> baris dihapus.
        </Text>
        <div style={{ marginTop: 8, marginBottom: 8 }}>
          <Text type="secondary" style={labelStyle}>Backup: </Text>
          {result?.backup?.ok ? (
            <Text code style={labelStyle}>{result.backup.path}</Text>
          ) : (
            <Text type="danger" style={labelStyle}>gagal dibuat — {result?.backup?.error}</Text>
          )}
        </div>
        {result?.deleted?.length ? (
          <Table
            size="small"
            bordered
            rowKey="model"
            pagination={false}
            scroll={{ y: 240 }}
            dataSource={result.deleted}
            columns={[
              { title: 'Model', dataIndex: 'label', key: 'label' },
              { title: 'Dihapus', dataIndex: 'count', key: 'count', align: 'right' as const, width: 110 },
            ]}
          />
        ) : null}
        <ResetLine resets={result?.resets} />
        {result?.scope === 'master' && result?.kept ? (
          <div style={{ marginTop: 10 }}>
            <KeptInfo
              company={result.kept.company?.name}
              branch={result.kept.branch?.name}
              users={result.kept.users}
              sequences={result.kept.sequences}
            />
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
