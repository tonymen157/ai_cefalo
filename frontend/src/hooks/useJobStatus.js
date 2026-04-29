import { useState, useEffect } from 'react'
import { useApi } from './useApi'

export function useJobStatus(jobId, onComplete, onError) {
  const [status, setStatus] = useState('pending')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const { get } = useApi()

  useEffect(() => {
    if (!jobId) return

    const interval = setInterval(async () => {
      try {
        const data = await get(`/jobs/${jobId}`)
        setStatus(data.status)
        setProgress(data.progress || 0)
        if (data.status === 'completed') {
          clearInterval(interval)
          if (onComplete) onComplete(data)
        } else if (data.status === 'failed') {
          clearInterval(interval)
          setError(data.error || 'Job failed')
          if (onError) onError(data.error)
        }
      } catch (err) {
        clearInterval(interval)
        setError(err.message)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [jobId])

  return { status, progress, error }
}
