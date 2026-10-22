/**
 * Format an ISO 8601 timestamp for display.
 * Returns '—' for null/undefined/invalid values.
 */
export function formatDate(iso, opts = {}) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (isNaN(d)) return '—'
    return d.toLocaleString('en-GB', {
      day:    '2-digit',
      month:  'short',
      year:   'numeric',
      hour:   '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      ...opts,
    })
  } catch {
    return '—'
  }
}

/** Return a short relative time label, e.g. "3m ago", "2h ago", "5d ago". */
export function timeAgo(iso) {
  if (!iso) return '—'
  try {
    const diff = Date.now() - new Date(iso).getTime()
    if (isNaN(diff)) return '—'
    const s = Math.floor(diff / 1000)
    if (s < 60)  return `${s}s ago`
    const m = Math.floor(s / 60)
    if (m < 60)  return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24)  return `${h}h ago`
    const day = Math.floor(h / 24)
    return `${day}d ago`
  } catch {
    return '—'
  }
}

/** Return only the date portion "21 Oct 2026". */
export function formatDateOnly(iso) {
  return formatDate(iso, { year: 'numeric', month: 'short', day: '2-digit', hour: undefined, minute: undefined, second: undefined })
}
