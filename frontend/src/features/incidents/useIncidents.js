import { useState, useEffect, useCallback } from 'react'
import { fetchIncidents, fetchIncident, patchIncident } from './incidentService'
import { useWebSocketEvent } from '../../hooks/useWebSocket'

export function useIncidents(filters = {}) {
  const [data,    setData]    = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await fetchIncidents(filters)
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)]) // eslint-disable-line

  useEffect(() => { load() }, [load])

  useWebSocketEvent('new_detection', () => {
    load()
  })

  useWebSocketEvent('incident_updated', (msg) => {
    setData((prev) => ({
      ...prev,
      items: prev.items.map((ev) =>
        ev.event_id === msg.data.event_id ? msg.data : ev
      ),
    }))
  })

  return { data, loading, error, refresh: load }
}

export function useIncident(id) {
  const [incident, setIncident] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    if (!id) { setLoading(false); return }
    setLoading(true)
    fetchIncident(id)
      .then(setIncident)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  const updateStatus = useCallback(async (status, notes) => {
    const updated = await patchIncident(id, { review_status: status, operator_notes: notes })
    setIncident(updated)
    return updated
  }, [id])

  return { incident, loading, error, updateStatus }
}
