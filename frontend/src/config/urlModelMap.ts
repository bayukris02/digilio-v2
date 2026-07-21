/** 
 * URL ↔ model name translator.
 * URL = _model_name langsung — tidak perlu map lagi.
 * Setiap model baru auto-detect tanpa konfigurasi.
 */

export function modelNameToApi(name: string): string {
  return name;
}

export function apiToUrlName(name: string): string {
  return name;
}
