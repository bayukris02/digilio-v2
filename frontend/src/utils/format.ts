import dayjs from 'dayjs';

/**
 * Global date display format — DD-MMM-YYYY = "25-Jun-2024"
 * Ubah di sini saja untuk mengganti format semua tanggal di UI.
 */
export const DATE_FORMAT = 'DD-MMM-YYYY';

/**
 * Format date string ke tampilan user.
 * Menerima YYYY-MM-DD atau ISO datetime dari API.
 */
export function formatDate(val: string | null | undefined): string {
  if (!val) return '';
  const d = dayjs(val);
  return d.isValid() ? d.format(DATE_FORMAT) : '';
}

/**
 * Parse date string (dari API) ke dayjs object untuk DatePicker.
 * Return undefined kalau null/invalid (biar DatePicker gak error).
 */
export function parseDate(val: string | null | undefined): dayjs.Dayjs | undefined {
  if (!val) return undefined;
  const d = dayjs(val);
  return d.isValid() ? d : undefined;
}

/**
 * Format Date → human-readable "time ago" string.
 * <5s → "just now"
 * <60s → "Xs ago"
 * <60m → "Xm ago"
 * ≥60m → absolute HH:mm
 * Beda hari → include date
 */
export function formatTimeAgo(date: Date | null): string {
  if (!date) return '';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 5) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;

  // Absolute time for 1h+
  const isToday = date.toDateString() === now.toDateString();
  const opts: Intl.DateTimeFormatOptions = isToday
    ? { hour: '2-digit', minute: '2-digit' }
    : { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' };
  return date.toLocaleTimeString('id-ID', opts).replace(/\./g, ':');
}

/**
 * Format ISO datetime string → "admin - last update 4 jul 16.50"
 * or just "Last update 4 jul 16.50" if updated_by is absent.
 */
export function formatLastUpdate(isoStr: string | null | undefined, userName?: string | null): string {
  if (!isoStr) return '';
  const d = dayjs(isoStr);
  if (!d.isValid()) return '';
  const timeStr = d.format('D MMM HH:mm').toLowerCase().replace(':', '.');
  if (userName) {
    return `${userName} - last update ${timeStr}`;
  }
  return `Last update ${timeStr}`;
}
