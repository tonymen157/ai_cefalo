import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function ProcessingStep() {
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState('idle') // idle | pending | processing | completed | failed
  const [progress, setProgress] = useState(0)
  const [landmarks, setLandmarks] = useState(null)
  const navigate = useNavigate()
  const { post, get } = useApi()

  // GUARD DE SEGURIDAD AISLADO
  useEffect(() => {
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    if (!imageId) {
      navigate('/upload', { replace: true })
    }
  }, [navigate])

  useEffect(() => {
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    const mmpp = sessionStorage.getItem('calibration_mmpp')
    if (!imageId) {
      navigate('/upload')
      return
    }

    const startJob = async () => {
      setStatus('pending')
      try {
        const data = await post('/analyze', { image_id: imageId, calibration_mmpp: mmpp ? parseFloat(mmpp) : null })
        setJobId(data.job_id)
        sessionStorage.setItem('job_id', data.job_id)
        localStorage.setItem('job_id', data.job_id)
        pollStatus(data.job_id)
      } catch (err) {
        setStatus('failed')
      }
    }
    startJob()
  }, [])

  const pollStatus = (jobId) => {
    const interval = setInterval(async () => {
      try {
        const data = await get(`/jobs/${jobId}`)
        setStatus(data.status)
        setProgress(data.progress || 0)
        if (data.status === 'completed') {
          clearInterval(interval)
          setLandmarks(data.landmarks)
          sessionStorage.setItem('landmarks', JSON.stringify(data.landmarks))
          setTimeout(() => navigate('/results'), 1000)
        } else if (data.status === 'failed') {
          clearInterval(interval)
        }
      } catch (err) {
        clearInterval(interval)
        setStatus('failed')
      }
    }, 2000)
  }

  return (
    <div className="max-w-2xl mx-auto text-center">
      <h2 className="text-2xl font-bold mb-6">Paso 3: Procesando...</h2>
      {status === 'pending' && <p className="text-gray-600">Iniciando análisis...</p>}
      {status === 'processing' && (
        <div>
          <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
            <div
              className="bg-blue-600 h-4 rounded-full transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <p className="text-gray-600">Progreso: {Math.round(progress * 100)}%</p>
        </div>
      )}
      {status === 'completed' && (
        <p className="text-green-600">¡Análisis completado! Redirigiendo...</p>
      )}
      {status === 'failed' && (
        <p className="text-red-500">Error en el procesamiento. Intenta de nuevo.</p>
      )}
    </div>
  )
}

export default ProcessingStep
