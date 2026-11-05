export function duration(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${ms} ms`;
  const seconds = ms / 1000;
  const rounded = Math.round(seconds);
  return seconds < 60 ? `${seconds.toFixed(1)} s` : `${Math.floor(rounded / 60)}m ${rounded % 60}s`;
}

export function dateTime(date: string | null): string {
  return date ? new Date(date).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—';
}

export function percent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)}%`;
}
