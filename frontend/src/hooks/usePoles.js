import { useCallback, useEffect, useState } from 'react'
import { fetchPoles } from '../services/forestApi'

export default function usePoles() {
  const [poles, setPoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)
      setPoles(await fetchPoles())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 5000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return { poles, loading, error, refresh }
}
