import { useCallback, useEffect, useState } from 'react'
import {
  fetchCameras,
  fetchMonitorStatus,
  startMonitor as startMonitorRequest,
  stopMonitor as stopMonitorRequest,
} from '../services/forestApi'

export default function useMonitor() {
  const [cameras, setCameras] = useState([])
  const [status, setStatus] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState('')
  const [loadingCameras, setLoadingCameras] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [streamKey, setStreamKey] = useState(0)

  const discover = useCallback(async () => {
    setLoadingCameras(true)
    try {
      const found = await fetchCameras()
      setCameras(found)
      setSelectedIndex((current) => {
        if (current !== '' && found.some((camera) => String(camera.camera_index) === current)) return current
        return found.length ? String(found[0].camera_index) : ''
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingCameras(false)
    }
  }, [])

  const refreshStatus = useCallback(async () => {
    try {
      const next = await fetchMonitorStatus()
      setStatus(next)
      if (next.camera_index != null) setSelectedIndex(String(next.camera_index))
      return next
    } catch (err) {
      setError(err.message)
      return null
    }
  }, [])

  useEffect(() => {
    discover()
    refreshStatus()
    const timer = window.setInterval(refreshStatus, 2500)
    return () => window.clearInterval(timer)
  }, [discover, refreshStatus])

  const start = useCallback(async () => {
    const camera = cameras.find((item) => String(item.camera_index) === selectedIndex)
    if (!camera) {
      setError('Select an available camera before starting monitoring.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const next = await startMonitorRequest(camera.camera_index, camera.camera_id)
      setStatus(next)
      setStreamKey(Date.now())
    } catch (err) {
      setError(err.message)
      await refreshStatus()
    } finally {
      setBusy(false)
    }
  }, [cameras, selectedIndex, refreshStatus])

  const stop = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      setStatus(await stopMonitorRequest())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      await refreshStatus()
    }
  }, [refreshStatus])

  return {
    cameras, status, selectedIndex, setSelectedIndex, loadingCameras,
    busy, error, streamKey, discover, refreshStatus, start, stop,
  }
}
