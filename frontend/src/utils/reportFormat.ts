import dayjs from 'dayjs';
import { DATE_FORMAT, formatDate } from './format';

/** Helper format angka/tanggal untuk SEMUA report (standar tunggal). */

/** Qty: id-ID, maks 3 desimal. */
export const fmtQty = (v: number | null | undefined): string =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 3 });

/** Uang: "Rp 1.234.567,89". */
export const fmtIDR = (v: number | null | undefined): string =>
  `Rp ${Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Bilangan bulat: id-ID. */
export const fmtNum = (v: number | null | undefined): string =>
  Number(v ?? 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

/** Tanggal tampilan (mengikuti DATE_FORMAT global di utils/format.ts). */
export const fmtReportDate = (v: string | null | undefined): string => formatDate(v) || '—';

/** Tanggal + jam (epoch ms / string / Date) — untuk keterangan "Data per". */
export const fmtDateTime = (v: number | string | Date | null | undefined): string => {
  if (!v) return '';
  const d = dayjs(v);
  return d.isValid() ? d.format(`${DATE_FORMAT} HH:mm`) : '';
};

/** Jumlah hari dari hari ini (untuk preset tanggal). */
export const daysAgo = (n: number) => dayjs().startOf('day').subtract(n, 'day');
