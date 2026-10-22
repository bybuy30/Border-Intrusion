import React, { useState } from 'react'
import { Activity, AlertTriangle, Camera, Users } from 'lucide-react'
import { useDashboard } from '../features/dashboard/useDashboard'
import PageHeader from '../components/layout/PageHeader'
import StatCard from '../components/common/StatCard'
import ErrorState from '../components/common/ErrorState'
import CameraMonitor from '../components/surveillance/CameraMonitor'
import PoleStatusCard from '../components/events/PoleStatusCard'
import RecentAlerts from '../components/events/RecentAlerts'
import EventDetailsDialog from '../components/events/EventDetailsDialog'

export default function CommandCenter() {
  const { summary, loading, error, refresh } = useDashboard()
  const [monitorStatus, setMonitorStatus] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const highCount = summary?.high_priority_count ?? null
  const cameraValue = !monitorStatus ? 'Checking' :
    monitorStatus.connected ? 'Online' :
      monitorStatus.running ? 'Connecting' : 'Offline'
  const events = summary?.recent_events ?? []

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <PageHeader title="Command center" subtitle="Live monitoring and event overview" />

      {error && <ErrorState message={error} onRetry={refresh} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <StatCard label="Total events" value={summary?.total_events_all_time} sub="All recorded detections" icon={Activity} loading={loading && !summary} />
        <StatCard label="People detected" value={summary?.class_breakdown?.person ?? 0} sub="All-time person detections" icon={Users} accent="amber" loading={loading && !summary} />
        <StatCard label="High-priority alerts" value={highCount} sub="High and critical priority" icon={AlertTriangle} accent="high" loading={loading && !summary} />
        <StatCard label="Camera status" value={cameraValue} sub={monitorStatus?.camera_id || 'No active camera'} icon={Camera} accent={monitorStatus?.connected ? 'green' : 'default'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,1fr)] gap-4">
        <CameraMonitor onStatusChange={setMonitorStatus} />
        <PoleStatusCard />
      </div>

      <RecentAlerts
        events={events}
        loading={loading && !summary}
        error={error}
        onRetry={refresh}
        onSelect={setSelectedEvent}
      />
      <EventDetailsDialog eventId={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  )
}
