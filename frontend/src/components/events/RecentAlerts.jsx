import React from 'react'
import { ArrowUpRight, BellRing } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ClassBadge, PriorityBadge } from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import ErrorState from '../common/ErrorState'
import LoadingState from '../common/LoadingState'
import { formatConfidence } from '../../utils/formatConfidence'
import { formatDate } from '../../utils/formatDate'

export default function RecentAlerts({ events = [], loading, error, onRetry, onSelect }) {
  return (
    <section className="panel min-w-0">
      <div className="panel-header">
        <h2 className="panel-title">Recent alerts</h2>
        <Link to="/incidents" className="text-xs text-forest-300 hover:text-forest-200 inline-flex items-center gap-1">
          Event history <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>
      {loading ? <LoadingState message="Loading recent events…" rows={4} /> : error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : events.length === 0 ? (
        <EmptyState icon={BellRing} title="No recent alerts" message="New detections stored by the backend will appear here." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-forest-800">
                <th className="font-medium px-4 py-2">Detection</th>
                <th className="font-medium px-4 py-2">Confidence</th>
                <th className="font-medium px-4 py-2">Priority</th>
                <th className="font-medium px-4 py-2">Pole</th>
                <th className="font-medium px-4 py-2">Images</th>
                <th className="font-medium px-4 py-2">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-forest-800">
              {events.map((event) => (
                <tr key={event.event_id} className="table-row-hover" onClick={() => onSelect(event.event_id)} tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onSelect(event.event_id) }}>
                  <td className="px-4 py-3">
                    <ClassBadge className={event.class_name} />
                    <span className="block text-[10px] text-slate-600 font-mono mt-1 break-all" title={event.event_id}>{event.event_id}</span>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-slate-300">{formatConfidence(event.confidence)}</td>
                  <td className="px-4 py-3"><PriorityBadge priority={event.alert_priority} /></td>
                  <td className="px-4 py-3 text-xs text-slate-400">{event.pole_id || '—'}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{event.image_count ?? 0} / 6</td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">{formatDate(event.server_ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
