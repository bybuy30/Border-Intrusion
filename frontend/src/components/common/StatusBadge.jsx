import React from 'react'
import { classBadgeClass, priorityBadgeClass, reviewBadgeClass } from '../../utils/severity'

export function ClassBadge({ className }) {
  if (!className) return null
  return (
    <span className={`badge border ${classBadgeClass(className)}`}>
      {className}
    </span>
  )
}

export function PriorityBadge({ priority }) {
  if (!priority) return null
  return (
    <span className={`badge border ${priorityBadgeClass(priority)}`}>
      {priority === 'critical' ? 'Critical' : priority === 'high' ? 'High' : 'Normal'}
    </span>
  )
}

export function ReviewBadge({ status }) {
  if (!status) return null
  const labels = { pending: 'Pending', reviewed: 'Reviewed', dismissed: 'Dismissed' }
  return (
    <span className={`badge border ${reviewBadgeClass(status)}`}>
      {labels[status] ?? status}
    </span>
  )
}
