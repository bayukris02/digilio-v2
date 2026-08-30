/**
 * ============================================================================
 * useUnsavedChangesGuard — dirty tracking + blocker navigasi (ModelFormPage)
 * ============================================================================
 * Hook ini menampung semua logika "unsaved changes" yang tadinya hidup di
 * ModelFormPage.tsx: snapshot form+lineItems, deteksi dirty, dan useBlocker
 * (React Router) yang menahan navigasi saat ada perubahan belum disimpan.
 *
 * API yang dikembalikan:
 *  - dirtyFlag / setDirtyFlag : state "ada perubahan belum disimpan" (dipakai
 *    UI header: titik/teks peringatan, dan blocker).
 *  - lastSnapshotRef          : ref JSON {form, lines} saat terakhir save/load;
 *    dibaca langsung oleh handleFormChange (cek dirty) & efek reset model.
 *  - computeDirty             : true kalau form/lineItems ≠ snapshot terakhir.
 *  - syncSaveSnapshot         : simpan snapshot baru + setDirtyFlag(false) —
 *    WAJIB dipanggil setelah save/load/action sukses (overrideLines utk kasus
 *    setState async lineItems).
 *  - skipBlockerRef           : bypass blocker utk navigasi SAH setelah save
 *    (setDirtyFlag(false) async, blocker cek ref bukan state).
 *  - lineItemsRef             : ref sinkron lineItems (dipakai computeDirty
 *    dan logika reload notebook di page).
 *
 * ATURAN: core frontend — WAJIB generik, tanpa model-specific logic.
 * ----------------------------------------------------------------------------
 * YANG HARUS DI-TEST setelah modifikasi:
 * 1. Edit field/baris notebook → muncul indikator "Perubahan belum disimpan";
 *    navigasi (menu/breadcrumb/◀▶/discard) → modal konfirmasi muncul.
 * 2. Klik "Ya, Tinggalkan" → lanjut; "Tetap di Sini" → kembali, data utuh.
 * 3. Save sukses → indikator hilang, navigasi langsung tanpa modal (bypass).
 * 4. Ubah field lalu balikin ke nilai semula → dirty hilang (snapshot match).
 * 5. Aksi status (Konfirmasi/dll), wizard, prev/next, discard → snapshot
 *    ter-resync, tidak ada false-positive "Perubahan belum disimpan".
 * 6. Pindah record via ◀▶ / menu antar-model (GR→PO→GR) → lineItems reset,
 *    dirty bersih, blocker tidak macet.
 * ============================================================================
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useBlocker, useLocation } from 'react-router-dom';
import { Modal } from 'antd';
import type { FormInstance } from 'antd';

export function useUnsavedChangesGuard(params: {
  form: FormInstance;
  lineItems: Record<string, Record<string, unknown>[]>;
  recordData: Record<string, unknown> | null;
}) {
  const { form, lineItems, recordData } = params;

  // ── Save status tracking ──
  // Snapshot mencakup form values DAN line items notebook — perubahan di
  // notebook (tambah/hapus/edit baris, drag) juga dihitung unsaved.
  const lastSnapshotRef = useRef<string>('');         // JSON {form, lines} saat terakhir save
  const [dirtyFlag, setDirtyFlag] = useState(false);
  const skipBlockerRef = useRef(false);
  // Ref sinkron lineItems — dipakai computeDirty & reload notebook di page
  const lineItemsRef = useRef(lineItems);
  lineItemsRef.current = lineItems;

  const makeSnapshot = useCallback(
    (formVals: Record<string, unknown>, lines: Record<string, Record<string, unknown>[]>) =>
      JSON.stringify({ form: formVals, lines }),
    [],
  );

  // Helper: true kalau form/lineItems berbeda dari snapshot terakhir
  const computeDirty = useCallback(() => {
    if (!lastSnapshotRef.current) return false;
    return makeSnapshot(form.getFieldsValue(), lineItemsRef.current) !== lastSnapshotRef.current;
  }, [form, makeSnapshot]);

  // Helper: sync snapshot dari current form values (+ lineItems).
  // overrideLines: untuk kasus load, state lineItems belum ter-update saat
  // dipanggil (setState async), jadi kirim nilai yang persis diset.
  const syncSaveSnapshot = useCallback((overrideLines?: Record<string, Record<string, unknown>[]>) => {
    lastSnapshotRef.current = makeSnapshot(
      form.getFieldsValue(),
      overrideLines ?? lineItemsRef.current,
    );
    setDirtyFlag(false);
  }, [form, makeSnapshot]);

  // Perubahan lineItems (notebook) → hitung dirty
  useEffect(() => {
    if (!lastSnapshotRef.current) return;
    setDirtyFlag(computeDirty());
  }, [lineItems, computeDirty]);

  // Re-sync snapshot SETELAH recordData berubah (load/action refresh).
  // Snapshot yang diambil synchronously di handleAction/handleWizardConfirm
  // terjadi SEBELUM React re-render — padahal re-render bisa mengubah
  // set/urutan Form.Item yang ter-register (mis. isReadOnly aktif setelah
  // konfirmasi, status baru, field rules) sehingga getFieldsValue() berikutnya
  // berbeda dari snapshot → false-positive "Perubahan belum disimpan".
  // Effect ini mengambil snapshot ulang saat field sudah ter-render.
  useEffect(() => {
    if (!recordData) return;
    syncSaveSnapshot();
  }, [recordData, syncSaveSnapshot]);

  // ── Block navigation when there are unsaved changes ──
  // useBlocker intercepts route changes (menu, breadcrumb, prev/next, discard)
  // so we can warn the user before data could be lost.
  // skipBlockerRef: bypass blocker utk navigasi SAH setelah save sukses
  // (setDirtyFlag(false) async, jadi blocker harus cek ref, bukan state).
  const location = useLocation();
  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }) =>
        !skipBlockerRef.current && dirtyFlag && currentLocation.pathname !== nextLocation.pathname,
      [dirtyFlag],
    ),
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      Modal.confirm({
        title: 'Perubahan Belum Disimpan',
        content: 'Ada perubahan yang belum disimpan. Yakin ingin meninggalkan halaman ini?',
        okText: 'Ya, Tinggalkan',
        cancelText: 'Tetap di Sini',
        onOk: () => blocker.proceed(),
        onCancel: () => blocker.reset(),
      });
    }
  }, [blocker]);

  // Reset bypass setelah navigasi selesai (pathname berubah)
  useEffect(() => {
    skipBlockerRef.current = false;
  }, [location.pathname]);

  return {
    dirtyFlag,
    setDirtyFlag,
    lastSnapshotRef,
    computeDirty,
    syncSaveSnapshot,
    skipBlockerRef,
    lineItemsRef,
  };
}
