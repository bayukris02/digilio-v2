/**
 * ============================================================================
 * PrintWizardModal — wizard tombol Print global (meta-driven)
 * ============================================================================
 * Dipakai tombol "Print" yang otomatis muncul di header SEMUA form model.
 * Kiri: daftar printout yang tersedia untuk model (dari `config.printouts`,
 * dibangun backend via BaseModel.get_printouts()). Kanan: print preview HTML
 * dari endpoint /api/print/<model>/<id>/<printout_key>/preview/.
 *
 * ATURAN: komponen generik — dilarang hardcode nama model / printout di sini.
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST:
 * 1. Daftar printout tampil di kiri; klik salah satu → preview kanan berganti.
 * 2. Printout pertama otomatis terpilih saat modal dibuka.
 * 3. Tombol Print → dialog print browser; Download PDF → file .pdf terunduh.
 * 4. Model tanpa printout → tombol Print tidak dirender (lihat ModelFormPage).
 * ============================================================================
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Empty, Modal, Space, Spin, message } from 'antd';
import { DownloadOutlined, PrinterOutlined } from '@ant-design/icons';

export interface PrintoutItem {
  key: string;
  label: string;
  template?: string;
}

export default function PrintWizardModal({
  open,
  onClose,
  modelName,
  recordId,
  printouts,
}: {
  open: boolean;
  onClose: () => void;
  modelName: string;
  recordId: number | null;
  printouts: PrintoutItem[];
}) {
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [html, setHtml] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const frameRef = useRef<HTMLIFrameElement>(null);

  const items = printouts || [];

  // Printout pertama otomatis terpilih saat modal dibuka
  useEffect(() => {
    if (!open) return;
    setActiveKey(items.length ? items[0].key : null);
    setHtml('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const previewUrl = useCallback(
    (key: string) => `/api/print/${modelName}/${recordId}/${key}/preview/`,
    [modelName, recordId],
  );
  const downloadUrl = useCallback(
    (key: string) => `/api/print/${modelName}/${recordId}/${key}/download/`,
    [modelName, recordId],
  );

  // Ambil HTML preview printout terpilih (JWT via Authorization header)
  useEffect(() => {
    if (!open || !activeKey || recordId == null) return;
    let cancelled = false;
    setLoading(true);
    const token = localStorage.getItem('access_token');
    fetch(previewUrl(activeKey), { headers: { Authorization: `Bearer ${token}` } })
      .then((resp) => resp.text())
      .then((text) => {
        if (!cancelled) setHtml(text);
      })
      .catch(() => {
        if (!cancelled) setHtml('');
        message.error('Gagal memuat print preview');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, activeKey, recordId, previewUrl]);

  const handlePrint = () => {
    const win = frameRef.current?.contentWindow;
    if (!win) {
      message.error('Preview belum siap');
      return;
    }
    win.focus();
    win.print();
  };

  const handleDownload = async () => {
    if (!activeKey) return;
    try {
      const token = localStorage.getItem('access_token');
      const resp = await fetch(downloadUrl(activeKey), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('download failed');
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `${modelName.replace(/\./g, '_')}_${activeKey}_${recordId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      message.error('Gagal mengunduh PDF');
    }
  };

  return (
    <Modal
      title={
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            width: '100%',
            paddingRight: 24,
          }}
        >
          <span>Print</span>
          <Space size={8}>
            <Button onClick={onClose}>Tutup</Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownload} disabled={!html}>
              Download PDF
            </Button>
            <Button type="primary" icon={<PrinterOutlined />} onClick={handlePrint} disabled={!html}>
              Print
            </Button>
          </Space>
        </div>
      }
      open={open}
      onCancel={onClose}
      width={1080}
      footer={null}
      style={{ top: 0 }}
      styles={{
        wrapper: { top: 0, paddingTop: 0, alignItems: 'flex-start' },
        container: { top: 0, marginTop: 0 },
        header: { padding: '10px 16px', marginBottom: 0 },
        body: { padding: '8px 12px 12px' },
      }}
    >
      <div style={{ display: 'flex', gap: 12, height: '72vh' }}>
        {/* Kiri: daftar printout yang tersedia */}
        <div
          style={{
            width: 240,
            flexShrink: 0,
            borderRight: '1px solid #f0f0f0',
            paddingRight: 8,
            overflowY: 'auto',
          }}
        >
          <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>Pilihan Printout</div>
          {items.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Belum ada printout" />}
          {items.map((p) => (
            <div
              key={p.key}
              onClick={() => setActiveKey(p.key)}
              style={{
                padding: '8px 10px',
                marginBottom: 4,
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                background: activeKey === p.key ? '#e6f4ff' : 'transparent',
                color: activeKey === p.key ? '#1677ff' : '#333',
                fontWeight: activeKey === p.key ? 600 : 400,
              }}
            >
              {p.label}
            </div>
          ))}
        </div>

        {/* Kanan: print preview */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex' }}>
          {loading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spin />
            </div>
          ) : html ? (
            <iframe
              ref={frameRef}
              title="print-preview"
              srcDoc={html}
              style={{ flex: 1, border: '1px solid #d9d9d9', borderRadius: 6, background: '#fff' }}
            />
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Preview tidak tersedia" />
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
