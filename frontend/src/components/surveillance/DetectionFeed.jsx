import React from 'react'
import { ClassBadge, PriorityBadge } from '../common/StatusBadge'
import { formatConfidence } from '../../utils/formatConfidence'
import { timeAgo } from '../../utils/formatDate'
import EmptyState from '../common/EmptyState'
import { Scan } from 'lucide-react'

export default function DetectionFeed({ events = [], maxRows = 20 }) {
  const visible = events.slice(0, maxRows)
  if (!visible.length) {
    return <EmptyState icon={Scan} title="No detections" message="Upload an image or video to see results here." />
  }
  return (
    <div className="divide-y divide-forest-800">
      {visible.map((ev, i) => (
        <div key={ev.event_id ?? i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-700 transition-colors">
          <ClassBadge className={ev.class_name} />
          <span className="text-xs font-mono text-slate-300 tabular-nums">
            {formatConfidence(ev.confidence)}
          </span>
          {ev.alert_priority === 'high' && <PriorityBadge priority="high" />}
          <span className="flex-1 text-xs text-slate-500 truncate">
            {ev.pole_id ?? ev.camera_id ?? '—'}
          </span>
          <span className="text-xs text-slate-600 whitespace-nowrap">
            {timeAgo(ev.server_ts)}
          </span>
        </div>
      ))}
    </div>
  )
}
