import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function ProcessingStep() {
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState('idle') // idle | pending | processing | completed | failed
  const [progress, setProgress] = useState(0)
  const [landmarks, setLandmarks] = useState(null)
  const [pollAttempts, setPollAttempts] = useState(0)
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
        setPollAttempts(0)
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
        setPollAttempts(prev => prev + 1)

        if (data.status === 'completed') {
          clearInterval(interval)
          setLandmarks(data.landmarks)
          sessionStorage.setItem('landmarks', JSON.stringify(data.landmarks))
          if (data.confidences) {
            sessionStorage.setItem('confidences', JSON.stringify(data.confidences))
          }
          setTimeout(() => navigate('/results'), 1000)
        } else if (data.status === 'failed') {
          clearInterval(interval)
        }
      } catch (err) {
        clearInterval(interval)
        setStatus('failed')
      }

      // Límite: 30 intentos (60 segundos)
      setPollAttempts(prev => {
        if (prev >= 29) {
          clearInterval(interval)
          setStatus('failed')
        }
        return prev
      })
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
          <p className="text-xs text-gray-400 mt-2">Intento {pollAttempts + 1} de 30</p>
        </div>
      )}
      {status === 'completed' && (
        <p className="text-green-600">¡Análisis completado! Redirigiendo...</p>
      )}
      {status === 'failed' && (
        <div className="text-center">
          <p className="text-red-500 mb-4">⚠️ Error: El servidor no respondió después de 60 segundos o ocurrió un error.</p>
          <button
            onClick={() => {
              setStatus('idle')
              setPollAttempts(0)
              const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
              const mmpp = sessionStorage.getItem('calibration_mmpp')
              if (imageId) {
                setStatus('pending')
                post('/analyze', { image_id: imageId, calibration_mmpp: mmpp ? parseFloat(mmpp) : null })
                  .then(data => {
                    setJobId(data.job_id)
                    sessionStorage.setItem('job_id', data.job_id)
                    localStorage.setItem('job_id', data.job_id)
                    setPollAttempts(0)
                    pollStatus(data.job_id)
                  })
                  .catch(() => setStatus('failed'))
              }
            }}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 mr-4"
          >
            ↻ Volver a intentar
          </button>
          <button
            onClick={() => navigate('/upload')}
            className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400"
          >
            Regresar al inicio
          </button>
        </div>
      )}
    </div>
  )
}

export default ProcessingStep
