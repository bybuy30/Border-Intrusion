import { useState, useEffect, useCallback } from 'react'
import { fetchDevices, fetchDevice } from './deviceService'

export function useDevices() {
  const [data,    setData]    = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await fetchDevices()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return { data, loading, error, refresh: load }
}

export function useDevice(poleId) {
  const [device,  setDevice]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    if (!poleId) { setLoading(false); return }
    setLoading(true)
    fetchDevice(poleId)
      .then(setDevice)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [poleId])

  return { device, loading, error }
}
