import { useState, useEffect, useCallback } from 'react'
import { fetchDashboardSummary, fetchHealth } from './dashboardService'
import { useWebSocketEvent } from '../../hooks/useWebSocket'

export function useDashboard() {
  const [summary, setSummary] = useState(null)
  const [health,  setHealth]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const [s, h] = await Promise.all([fetchDashboardSummary(), fetchHealth()])
      setSummary(s)
      setHealth(h)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 30000)
    return () => window.clearInterval(timer)
  }, [load])

  useWebSocketEvent('new_detection', () => {
    load()
  })

  return { summary, health, loading, error, refresh: load }
}
