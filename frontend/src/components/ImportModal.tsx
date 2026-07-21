import { useState, useCallback } from 'react';
import {
  Modal, Upload, Button, Select, Table, Space, Alert, Typography, message, Progress,
} from 'antd';
import { UploadOutlined, DownloadOutlined, InboxOutlined } from '@ant-design/icons';
import type { UploadFile, RcFile } from 'antd/es/upload';
import { modelApi } from '../api/models';

const { Text, Title } = Typography;
const { Dragger } = Upload;

interface ImportModalProps {
  open: boolean;
  modelName: string;
  apiModelName: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface PreviewResult {
  sheets: string[];
  selected_sheet: string | null;
  total_rows: number;
  valid_count: number;
  error_count: number;
  field_mapping: Record<string, string>;
  unmapped_headers: string[];
  preview_rows: Record<string, unknown>[];
  error_rows: {
    row_index: number;
    values: Record<string, unknown>;
    errors: Record<string, string>;
  }[];
}

export default function ImportModal({ open, modelName, apiModelName, onClose, onSuccess }: ImportModalProps) {
  const [step, setStep] = useState<'upload' | 'preview' | 'result'>('upload');
  const [file, setFile] = useState<RcFile | null>(null);
  const [sheets, setSheets] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null);

  // ── Download template ──
  const handleDownloadTemplate = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/import/${apiModelName}/template/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to download template');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${modelName}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      message.error('Gagal download template: ' + (err as Error)?.message);
    }
  }, [apiModelName, modelName]);

  // ── Upload file & preview ──
  const uploadFile = useCallback(async (uploadedFile: RcFile, sheet?: string) => {
    setLoading(true);
    setProgress(0);
    setPreview(null);
    setImportResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', uploadedFile);
      if (sheet) {
        formData.append('sheet_name', sheet);
      }

      const response = await fetch(`/api/import/${apiModelName}/preview/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        message.error(data?.error || 'Preview gagal');
        setLoading(false);
        return;
      }

      setPreview(data);
      setSheets(data.sheets || []);
      if (data.sheets?.length > 1 && !sheet) {
        // Multi-sheet — user needs to select first
        setSelectedSheet(data.sheets[0]);
        setLoading(false);
        return;
      }
      setStep('preview');
    } catch (err) {
      message.error('Upload gagal: ' + (err as Error)?.message);
    }
    setLoading(false);
  }, [apiModelName]);

  // ── Handle file drop ──
  const handleFile = useCallback(async (rcFile: RcFile) => {
    setFile(rcFile);
    setSelectedSheet(null);
    await uploadFile(rcFile, undefined);
    return false; // Prevent default Upload behavior
  }, [uploadFile]);

  // ── Handle sheet change ──
  const handleSheetChange = useCallback(async (sheet: string) => {
    setSelectedSheet(sheet);
    if (file) {
      await uploadFile(file, sheet);
    }
  }, [file, uploadFile]);

  // ── Execute import ──
  const handleExecute = useCallback(async () => {
    if (!preview) return;
    setExecuting(true);
    setProgress(50);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/import/${apiModelName}/execute/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          valid_rows: preview.valid_rows,
          error_rows: preview.error_rows,
          field_mapping: preview.field_mapping,
          unmapped_headers: preview.unmapped_headers,
          child_groups: preview.child_groups || {},
        }),
      });

      const result = await response.json();
      setProgress(100);
      setImportResult(result);
      setStep('result');

      if (!response.ok) {
        message.error(result?.error || 'Import gagal');
      } else {
        const imported = result.imported ?? 0;
        if (imported > 0) {
          message.success(`Import selesai: ${imported} row berhasil`);
          onSuccess();
        } else {
          message.warning(`Import selesai: 0 row berhasil (${result.skipped ?? 0} error)`);
        }
      }
    } catch (err) {
      message.error('Execute gagal: ' + (err as Error)?.message);
    }
    setExecuting(false);
  }, [apiModelName, preview, onSuccess]);

  // ── Reset ──
  const handleClose = useCallback(() => {
    setStep('upload');
    setFile(null);
    setPreview(null);
    setSheets([]);
    setSelectedSheet(null);
    setLoading(false);
    setExecuting(false);
    setProgress(0);
    setImportResult(null);
    onClose();
  }, [onClose]);

  // ── Error rows columns ──
  const [suggestPopover, setSuggestPopover] = useState<{ field: string; suggestions: string[] } | null>(null);
  const errorColumns = [
    { title: 'Row', dataIndex: 'row_index', key: 'row_index', width: 60 },
    { title: 'Errors', key: 'errors', render: (_: unknown, record: { errors: Record<string, string> }) => (
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        {Object.entries(record.errors).map(([field, msg]) => {
          // Skip internal fields (_suggestions)
          if (field.endsWith('_suggestions')) return null;
          const suggestKey = `${field}_suggestions`;
          const suggestions = record.errors[suggestKey] as unknown as string[] | undefined;
          return (
            <li key={field}>
              <Text type="danger">{msg}</Text>
              {suggestions && suggestions.length > 0 && (
                <Button
                  type="link"
                  size="small"
                  style={{ padding: '0 4px' }}
                  onClick={() => setSuggestPopover({ field, suggestions })}
                >
                  Suggest Value ▾
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    )},
  ];

  // ── Preview columns (from field_mapping, but use field name as dataIndex) ──
  const previewColumns = preview
    ? Object.entries(preview.field_mapping).map(([header, field]) => ({
        title: header,
        dataIndex: field,
        key: field,
        ellipsis: true,
      }))
    : [];

  return (
    <Modal
      title="Import Data"
      open={open}
      onCancel={handleClose}
      width={800}
      footer={null}
      destroyOnClose
    >
      {/* ═══ Step 1: Upload ═══ */}
      {step === 'upload' && (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
            Download Template CSV
          </Button>

          <Dragger
            accept=".csv,.xlsx,.xls"
            showUploadList={false}
            beforeUpload={handleFile}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">Klik atau drag file CSV / Excel ke sini</p>
            <p className="ant-upload-hint">Support CSV dan Excel (.xlsx, .xls)</p>
          </Dragger>

          {sheets.length > 1 && (
            <Space>
              <Text>Pilih Sheet:</Text>
              <Select
                value={selectedSheet}
                onChange={handleSheetChange}
                options={sheets.map(s => ({ value: s, label: s }))}
                style={{ width: 200 }}
              />
            </Space>
          )}

          {loading && (
            <Progress percent={progress} status="active" />
          )}
        </Space>
      )}

      {/* ═══ Step 2: Preview ═══ */}
      {step === 'preview' && preview && (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Alert
            type={preview.error_count > 0 ? 'warning' : 'success'}
            message={`${preview.total_rows} rows ditemukan — ${preview.valid_count} valid, ${preview.error_count} error`}
            showIcon
          />

          {preview.unmapped_headers.length > 0 && (
            <Alert
              type="info"
              message={`Kolom tidak terdeteksi: ${preview.unmapped_headers.join(', ')}`}
              showIcon
            />
          )}

          {preview.preview_rows.length > 0 && (
            <>
              <Text strong>Preview (5 baris pertama):</Text>
              <Table
                dataSource={preview.preview_rows.map((row, i) => ({ ...row, _key: i }))}
                columns={previewColumns}
                rowKey="_key"
                pagination={false}
                size="small"
                scroll={{ x: 'max-content' }}
              />
            </>
          )}

          {preview.error_rows.length > 0 && (
            <>
              <Text strong type="danger">Error ({preview.error_count} row):</Text>
              <Table
                dataSource={preview.error_rows}
                columns={errorColumns}
                rowKey="row_index"
                pagination={{ pageSize: 5 }}
                size="small"
              />
            </>
          )}

          <Space>
            <Button onClick={() => setStep('upload')}>Kembali</Button>
            <Button
              type="primary"
              onClick={handleExecute}
              loading={executing}
              disabled={preview.valid_count === 0}
            >
              Import {preview.valid_count} Row Valid
            </Button>
          </Space>

          {executing && <Progress percent={progress} status="active" />}
        </Space>
      )}

      {/* ═══ Step 3: Result ═══ */}
      {step === 'result' && importResult && (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Alert
            type={importResult.imported > 0 ? 'success' : 'warning'}
            message={`${importResult.imported} row berhasil diimport`}
            showIcon
          />

          {importResult.errors && (importResult.errors as unknown[]).length > 0 && (
            <>
              <Text strong type="danger">Errors:</Text>
              <ul>
                {(importResult.errors as { row: number; message: string }[]).map((e, i) => (
                  <li key={i}>Row {e.row}: {e.message}</li>
                ))}
              </ul>
            </>
          )}

          <Button type="primary" onClick={handleClose}>Selesai</Button>
        </Space>
      )}

      {/* ═══ Suggest Value Modal ═══ */}
      <Modal
        title={`Available ${suggestPopover?.field ?? ''}`}
        open={!!suggestPopover}
        onCancel={() => setSuggestPopover(null)}
        footer={null}
        width={400}
      >
        {suggestPopover && (
          <ul style={{ maxHeight: 300, overflow: 'auto', paddingLeft: 16 }}>
            {suggestPopover.suggestions.map((s, i) => (
              <li key={i} style={{ padding: '4px 0' }}>{s}</li>
            ))}
          </ul>
        )}
      </Modal>
    </Modal>
  );
}
