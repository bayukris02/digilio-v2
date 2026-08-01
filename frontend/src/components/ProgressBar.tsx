/**
 * ProgressBar — bar 0–100% dengan gradasi warna merah → hijau.
 * Dipakai sebagai AG Grid cellRenderer untuk field percentage dengan flag progress.
 */
export default function ProgressBar({ value }: { value: number | null | undefined }) {
  const pct = Math.max(0, Math.min(100, Number(value ?? 0)));
  // Hue 0 (merah) → 120 (hijau); saturasi/lightness dijaga agar tetap terbaca
  const hue = Math.round((pct / 100) * 120);
  const color = `hsl(${hue}, 70%, 42%)`;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
      <div
        style={{
          flex: 1,
          minWidth: 60,
          height: 10,
          borderRadius: 5,
          background: '#f0f0f0',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            borderRadius: 5,
            background: `linear-gradient(90deg, #ff4d4f, ${color})`,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <span style={{ width: 42, textAlign: 'right', fontSize: 12, color: color, fontWeight: 600 }}>
        {pct}%
      </span>
    </div>
  );
}
