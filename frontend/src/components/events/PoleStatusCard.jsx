import React from 'react'
import { MapPin, Radio, ShieldAlert } from 'lucide-react'
import usePoles from '../../hooks/usePoles'
import { formatDate } from '../../utils/formatDate'
import { formatConfidence } from '../../utils/formatConfidence'
import LoadingState from '../common/LoadingState'
import ErrorState from '../common/ErrorState'
import EmptyState from '../common/EmptyState'
import { ClassBadge, PriorityBadge } from '../common/StatusBadge'

export default function PoleStatusCard() {
  const { poles, loading, error, refresh } = usePoles()

  return (
    <section className="panel min-w-0">
      <div className="panel-header">
        <h2 className="panel-title">Pole monitoring</h2>
        <span className="text-[11px] text-slate-500">{poles.length} configured</span>
      </div>
      {loading ? <LoadingState message="Loading pole status…" rows={2} /> : error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : !poles.length ? (
        <EmptyState icon={Radio} title="No poles configured" message="A pole appears here after the backend stores its first heartbeat or detection." />
      ) : (
        <div className="divide-y divide-forest-800">
          {poles.map((pole) => {
            const event = pole.latest_event
            const online = pole.online === true
            return (
              <article key={pole.pole_id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-200 truncate">{pole.pole_name || pole.pole_id || 'Unnamed pole'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{pole.pole_id || '—'} · {pole.camera_id || 'No camera assigned'}</p>
                  </div>
                  <span className={`badge border shrink-0 ${online ? 'bg-forest-950 text-forest-300 border-forest-700' : 'bg-surface-700 text-slate-400 border-forest-800'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-forest-400' : 'bg-slate-500'}`} />
                    {online ? 'Online' : 'Offline'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
                  <div className="flex gap-2 min-w-0 text-slate-400">
                    <MapPin className="w-3.5 h-3.5 shrink-0 text-slate-500 mt-0.5" />
                    <span className="truncate">{pole.location || 'Location not configured'}</span>
                  </div>
                  <p className="text-slate-500">Heartbeat: <span className="text-slate-300">{formatDate(pole.last_heartbeat)}</span></p>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-forest-800">
                  {event ? (
                    <>
                      <ClassBadge className={event.class_name} />
                      <span className="text-xs text-slate-400">{formatConfidence(event.confidence)}</span>
                      <PriorityBadge priority={event.alert_priority} />
                      <span className="text-[11px] text-slate-500 ml-auto">Latest {formatDate(event.server_ts)}</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-xs text-slate-500">No detections recorded</span>
                    </>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
