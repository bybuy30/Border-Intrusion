// Alert level definitions — mirrors the backend alert_engine.py constants

export const ALERT_PRIORITY = {
  HIGH:   'high',
  NORMAL: 'normal',
}

export const REVIEW_STATUS = {
  PENDING:   'pending',
  REVIEWED:  'reviewed',
  DISMISSED: 'dismissed',
}

export const CLASS_NAMES = ['animal', 'person', 'firearm']

// Tailwind colour tokens per class
export const CLASS_COLOURS = {
  animal:  { dot: 'bg-forest-400',  text: 'text-forest-300',  badge: 'bg-forest-900 text-forest-300 border-forest-700' },
  person:  { dot: 'bg-blue-400',    text: 'text-blue-300',    badge: 'bg-blue-950 text-blue-300 border-blue-800' },
  firearm: { dot: 'bg-red-500',     text: 'text-red-400',     badge: 'bg-red-950 text-red-400 border-red-800' },
}

export const PRIORITY_COLOURS = {
  high:   'bg-red-950 text-red-400 border-red-800',
  critical: 'bg-red-950 text-red-300 border-red-700',
  normal: 'bg-surface-700 text-slate-400 border-forest-800',
}

export const REVIEW_COLOURS = {
  pending:   'bg-amber-950 text-amber-400 border-amber-800',
  reviewed:  'bg-forest-950 text-forest-300 border-forest-800',
  dismissed: 'bg-surface-700 text-slate-500 border-forest-900',
}
