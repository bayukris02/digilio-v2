import * as XLSX from 'xlsx';

/**
 * Export array-of-arrays ke file .xlsx (unduh via browser).
 * Baris pertama sampai baris kosong pertama dianggap blok judul/filter —
 * sel-selnya digabung render apa adanya.
 */
export function exportXlsx(opts: {
  filename: string;
  sheetName?: string;
  rows: (string | number | null | undefined)[][];
  /** Lebar kolom (opsional), index per kolom dalam karakter */
  colWidths?: number[];
}) {
  const { filename, sheetName = 'Sheet1', rows, colWidths } = opts;
  const ws = XLSX.utils.aoa_to_sheet(rows as (string | number)[][]);
  if (colWidths?.length) {
    ws['!cols'] = colWidths.map((wch) => ({ wch }));
  }
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  XLSX.writeFile(wb, filename);
}

/** Format qty konsisten dgn tampilan tabel (tanpa ribuan separator utk Excel). */
export function numCell(v: number | null | undefined): number | '' {
  return v == null || Number.isNaN(Number(v)) ? '' : Math.round(Number(v) * 1000) / 1000;
}
