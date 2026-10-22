/**
 * Format a 0–1 confidence score as a percentage string.
 * Returns '—' for null/undefined.
 */
export function formatConfidence(value) {
  if (value == null) return '—'
  const pct = Math.round(value * 100)
  return `${pct}%`
}

/**
 * Return a Tailwind colour class based on confidence level.
 * High ≥ 0.75, Medium ≥ 0.50, Low < 0.50
 */
export function confidenceColour(value) {
  if (value == null) return 'text-slate-500'
  if (value >= 0.75) return 'text-forest-300'
  if (value >= 0.50) return 'text-amber-400'
  return 'text-red-400'
}
