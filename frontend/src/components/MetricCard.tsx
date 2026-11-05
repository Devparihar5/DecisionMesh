export function MetricCard({ label, value, note, accent = false }: { label: string; value: string; note: string; accent?: boolean }) {
  return <article className={`metric-card ${accent ? 'accent' : ''}`}>
    <span className="quiet-label">{label}</span><strong>{value}</strong><small>{note}</small>
  </article>;
}
