import React, { useEffect, useState } from 'react'
import PageHeader from '../components/layout/PageHeader'
import ActivityChart from '../components/charts/ActivityChart'
import AlertTrendChart from '../components/charts/AlertTrendChart'
import DetectionDistributionChart from '../components/charts/DetectionDistributionChart'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { fetchAnalytics } from '../services/forestApi'

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    fetchAnalytics(days)
      .then((data) => { if (active) setAnalytics(data) })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [days])

  return (
    <div className="space-y-5 max-w-[1500px] mx-auto">
      <PageHeader title="Analytics" subtitle="Detection aggregates from MongoDB" actions={
        <select className="select w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
        </select>
      } />
      {error ? <ErrorState message={error} /> : loading && !analytics ? <LoadingState message="Loading analytics…" /> : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <section className="panel p-4"><h2 className="panel-title mb-3">Detection activity</h2><ActivityChart data={analytics?.by_date ?? []} /></section>
            <section className="panel p-4"><h2 className="panel-title mb-3">Detection classes</h2><DetectionDistributionChart data={analytics?.by_class ?? {}} /></section>
          </div>
          <section className="panel p-4"><h2 className="panel-title mb-3">High-priority alerts</h2><AlertTrendChart data={analytics?.by_date ?? []} /></section>
        </>
      )}
    </div>
  )
}
