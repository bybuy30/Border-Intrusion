import { ALERT_PRIORITY, CLASS_COLOURS, PRIORITY_COLOURS, REVIEW_COLOURS } from '../constants/alertLevels'

export function priorityBadgeClass(priority) {
  return PRIORITY_COLOURS[priority] ?? PRIORITY_COLOURS.normal
}

export function reviewBadgeClass(status) {
  return REVIEW_COLOURS[status] ?? REVIEW_COLOURS.pending
}

export function classBadgeClass(className) {
  return CLASS_COLOURS[className]?.badge ?? 'bg-surface-700 text-slate-400 border-forest-800'
}

export function classTextClass(className) {
  return CLASS_COLOURS[className]?.text ?? 'text-slate-400'
}

export function classDotClass(className) {
  return CLASS_COLOURS[className]?.dot ?? 'bg-slate-500'
}

export function isHighPriority(event) {
  return event?.alert_priority === ALERT_PRIORITY.HIGH
}
