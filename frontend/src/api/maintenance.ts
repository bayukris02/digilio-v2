import api from './client';

/** Baris ringkasan per model (label + jumlah baris). */
export interface PurgeRow {
  model: string;
  label: string;
  count: number;
}

/** Info data yang disisakan saat clear master data. */
export interface PurgeKept {
  company: { id: number; name: string } | null;
  branch: { id: number; name: string } | null;
  users: number;
  /** definisi Sequence (konfigurasi nomor dokumen) — tidak dihapus, counter-nya direset */
  sequences: number;
}

/** Satu opsi clear (transaksi / master data). */
export interface PurgeScope {
  title: string;
  desc: string;
  /** frasa konfirmasi yang harus diketik user, mis. "HAPUS TRANSAKSI" */
  phrase: string;
  rows: PurgeRow[];
  models: number;
  total: number;
  /** counter nomor dokumen yang direset (bukan dihapus sebagai data) */
  resets: PurgeRow[];
  chatter: number;
}

export interface PurgeOption { id: number; name: string }
export interface PurgeBranchOption extends PurgeOption { company_id: number }

export interface PurgePreview {
  transactions: PurgeScope;
  master: PurgeScope;
  kept: PurgeKept;
  /** pilihan Company/Branch yang bisa disisakan */
  options: { companies: PurgeOption[]; branches: PurgeBranchOption[] };
}

export interface PurgeResult {
  scope: 'transactions' | 'master';
  title: string;
  deleted: PurgeRow[];
  resets: PurgeRow[];
  total: number;
  backup: { ok: boolean; path: string; size?: number; error?: string };
  kept: PurgeKept;
}

export const maintenanceApi = {
  /** Ringkasan data yang akan dihapus (tidak mengubah data). */
  preview: async (): Promise<PurgePreview> => (await api.get('/maintenance/purge/preview/')).data,
  /**
   * Jalankan penghapusan; `confirm` harus sama dengan frasa pada preview.
   * `keep` (khusus scope 'master') menentukan Company & Branch yang disisakan.
   */
  run: async (
    scope: 'transactions' | 'master',
    confirm: string,
    keep?: { keep_company?: number | null; keep_branch?: number | null },
  ): Promise<PurgeResult> =>
    (await api.post('/maintenance/purge/', { scope, confirm, ...(keep ?? {}) })).data,
};
