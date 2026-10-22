import React from 'react'
import PageHeader from '../components/layout/PageHeader'
import ErrorState from '../components/common/ErrorState'
import EmptyState from '../components/common/EmptyState'
import LoadingState from '../components/common/LoadingState'
import PoleStatusCard from '../components/events/PoleStatusCard'
import usePoles from '../hooks/usePoles'
import { Cpu } from 'lucide-react'
import { formatDate } from '../utils/formatDate'

export default function DeviceManagement() {
  const { poles, loading, error, refresh } = usePoles()
  return (
    <div className="space-y-5 max-w-[1400px] mx-auto">
      <PageHeader title="Pole and device status" subtitle="Heartbeat and latest event information reported by the backend" />
      <PoleStatusCard />
      <section className="panel">
        <div className="panel-header"><h2 className="panel-title">Configured pole records</h2></div>
        {loading ? <LoadingState message="Loading poles…" /> : error ? <ErrorState message={error} onRetry={refresh} /> : !poles.length ? (
          <EmptyState icon={Cpu} title="No pole records" message="The backend creates a pole record after a camera heartbeat or detection is recorded." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead><tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-forest-800">
                <th className="px-4 py-3 font-medium">Pole</th><th className="px-4 py-3 font-medium">Location</th><th className="px-4 py-3 font-medium">Camera</th><th className="px-4 py-3 font-medium">Heartbeat</th><th className="px-4 py-3 font-medium">Status</th>
              </tr></thead>
              <tbody className="divide-y divide-forest-800">{poles.map((pole) => (
                <tr key={pole.pole_id} className="text-xs">
                  <td className="px-4 py-3 text-slate-200">{pole.pole_name || pole.pole_id}<span className="block text-slate-500 mt-1">{pole.pole_id}</span></td>
                  <td className="px-4 py-3 text-slate-400">{pole.location || 'Not configured'}</td>
                  <td className="px-4 py-3 text-slate-400">{pole.camera_id || '—'}</td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(pole.last_heartbeat)}</td>
                  <td className="px-4 py-3"><span className={pole.online ? 'text-forest-300' : 'text-slate-500'}>{pole.online ? 'Online' : 'Offline'}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
