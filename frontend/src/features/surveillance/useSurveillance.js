import { useState, useCallback } from 'react'
import { detectImage, detectVideo } from './surveillanceService'

export function useSurveillance() {
  const [result,    setResult]    = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [progress,  setProgress]  = useState(null) // 'uploading' | 'processing' | null

  const runImageDetection = useCallback(async (file) => {
    try {
      setError(null)
      setResult(null)
      setLoading(true)
      setProgress('uploading')
      const data = await detectImage(file)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setProgress(null)
    }
  }, [])

  const runVideoDetection = useCallback(async (file) => {
    try {
      setError(null)
      setResult(null)
      setLoading(true)
      setProgress('uploading')
      const data = await detectVideo(file)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setProgress(null)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setLoading(false)
    setProgress(null)
  }, [])

  return { result, loading, error, progress, runImageDetection, runVideoDetection, reset }
}
