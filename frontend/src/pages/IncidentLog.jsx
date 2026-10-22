import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import PageHeader from '../components/layout/PageHeader'
import EventDetailsDialog from '../components/events/EventDetailsDialog'
import RecentAlerts from '../components/events/RecentAlerts'
import usePoles from '../hooks/usePoles'
import { useIncidents } from '../features/incidents/useIncidents'

function toIso(value, end = false) {
  if (!value) return undefined
  const date = new Date(value)
  if (end) date.setSeconds(59, 999)
  else date.setSeconds(0, 0)
  return date.toISOString()
}

export default function IncidentLog() {
  const { id } = useParams()
  const [filters, setFilters] = useState({ start: '', end: '', pole: '', className: '', priority: '' })
  const [applied, setApplied] = useState({})
  const [offset, setOffset] = useState(0)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const { poles } = usePoles()
  const params = useMemo(() => ({
    limit: 50,
    offset,
    ...(applied.start_date ? { start_date: applied.start_date } : {}),
    ...(applied.end_date ? { end_date: applied.end_date } : {}),
    ...(applied.pole_id ? { pole_id: applied.pole_id } : {}),
    ...(applied.class_name ? { class_name: applied.class_name } : {}),
    ...(applied.alert_priority ? { alert_priority: applied.alert_priority } : {}),
  }), [offset, applied])
  const { data, loading, error, refresh } = useIncidents(params)

  useEffect(() => {
    if (id) setSelectedEvent(id)
  }, [id])

  const applyFilters = (event) => {
    event.preventDefault()
    setOffset(0)
    setApplied({
      start_date: toIso(filters.start),
      end_date: toIso(filters.end, true),
      pole_id: filters.pole,
      class_name: filters.className,
      alert_priority: filters.priority,
    })
  }

  const clearFilters = () => {
    setFilters({ start: '', end: '', pole: '', className: '', priority: '' })
    setApplied({})
    setOffset(0)
  }

  return (
    <div className="space-y-5 max-w-[1600px] mx-auto">
      <PageHeader title="Event history" subtitle={`${data.total ?? 0} matching events`} />
      <form onSubmit={applyFilters} className="panel p-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-6 gap-3 items-end">
        <label><span className="block text-[11px] text-slate-500 mb-1">From</span><input className="input" type="datetime-local" value={filters.start} onChange={(e) => setFilters({ ...filters, start: e.target.value })} /></label>
        <label><span className="block text-[11px] text-slate-500 mb-1">To</span><input className="input" type="datetime-local" value={filters.end} onChange={(e) => setFilters({ ...filters, end: e.target.value })} /></label>
        <label>
          <span className="block text-[11px] text-slate-500 mb-1">Pole ID</span>
          <select className="select" value={filters.pole} onChange={(e) => setFilters({ ...filters, pole: e.target.value })}>
            <option value="">All poles</option>
            {poles.map((pole) => <option key={pole.pole_id} value={pole.pole_id}>{pole.pole_id}</option>)}
          </select>
        </label>
        <label>
          <span className="block text-[11px] text-slate-500 mb-1">Object class</span>
          <select className="select" value={filters.className} onChange={(e) => setFilters({ ...filters, className: e.target.value })}>
            <option value="">All classes</option>
            <option value="person">Person</option><option value="animal">Animal</option><option value="firearm">Firearm</option>
          </select>
        </label>
        <label>
          <span className="block text-[11px] text-slate-500 mb-1">Priority</span>
          <select className="select" value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
            <option value="">All priorities</option>
            <option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option>
          </select>
        </label>
        <div className="flex gap-2">
          <button className="btn-primary flex-1" type="submit">Apply</button>
          <button className="btn-secondary" type="button" onClick={clearFilters}>Clear</button>
        </div>
      </form>

      <RecentAlerts events={data.items} loading={loading} error={error} onRetry={refresh} onSelect={setSelectedEvent} />
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Showing {data.items.length ? offset + 1 : 0}–{offset + data.items.length} of {data.total ?? 0}</span>
        <div className="flex gap-2">
          <button className="btn-secondary" type="button" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - 50))}>Previous</button>
          <button className="btn-secondary" type="button" disabled={offset + data.items.length >= (data.total ?? 0) || loading} onClick={() => setOffset((value) => value + 50)}>Next</button>
        </div>
      </div>
      <EventDetailsDialog eventId={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  )
}
