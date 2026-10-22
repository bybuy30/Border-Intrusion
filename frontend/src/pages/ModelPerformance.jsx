import React, { useEffect, useState } from 'react'
import { fetchHealth, fetchModelMetrics } from '../services/forestApi'
import PageHeader from '../components/layout/PageHeader'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'

export default function ModelPerformance() {
  const [health, setHealth] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([fetchHealth(), fetchModelMetrics()])
      .then(([system, metrics]) => { setHealth(system); setResult(metrics) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-5 max-w-[1200px] mx-auto">
      <PageHeader title="Model status" subtitle="Model readiness and saved evaluation output" />
      {loading ? <LoadingState message="Loading model information…" /> : error ? <ErrorState message={error} /> : (
        <>
          <section className="panel p-4 grid sm:grid-cols-2 gap-4">
            <div><p className="text-xs text-slate-500">Checkpoint available</p><p className={`text-sm mt-1 ${health?.model_ready ? 'text-forest-300' : 'text-amber-300'}`}>{health?.model_ready ? 'Ready' : 'Not found'}</p></div>
            <div><p className="text-xs text-slate-500">Backend database</p><p className={`text-sm mt-1 ${health?.database_connected ? 'text-forest-300' : 'text-amber-300'}`}>{health?.database_connected ? 'Connected' : 'Unavailable'}</p></div>
          </section>
          <section className="panel p-4">
            <h2 className="panel-title mb-3">Evaluation metrics</h2>
            {result?.available ? (
              <pre className="overflow-auto text-xs text-slate-300 bg-surface-900 p-4 rounded-md">{JSON.stringify(result, null, 2)}</pre>
            ) : <p className="text-xs text-slate-400">{result?.message || 'No evaluation results have been saved.'}</p>}
          </section>
        </>
      )}
    </div>
  )
}
