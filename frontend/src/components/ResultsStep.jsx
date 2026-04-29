import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import SteinerTable from './SteinerTable'
import LandmarkCanvas from './LandmarkCanvas'

function ResultsStep() {
  const [steinerResults, setSteinerResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { post } = useApi()

  useEffect(() => {
    const landmarks = sessionStorage.getItem('landmarks')
    const mmpp = sessionStorage.getItem('calibration_mmpp')
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    const jobId = sessionStorage.getItem('job_id') || localStorage.getItem('job_id')

    // Persist to both storages
    if (imageId) {
      sessionStorage.setItem('image_id', imageId)
      localStorage.setItem('image_id', imageId)
    }
    if (jobId) {
      sessionStorage.setItem('job_id', jobId)
      localStorage.setItem('job_id', jobId)
    }

    if (!landmarks) {
      navigate('/upload')
      return
    }

    const calculate = async () => {
      try {
        const parsedLandmarks = JSON.parse(landmarks)
        const parsedMmpp = parseFloat(mmpp)

        if (!parsedMmpp || isNaN(parsedMmpp) || parsedMmpp <= 0) {
          setError('Calibración no válida. Por favor configura la escala en el paso anterior.')
          setLoading(false)
          return
        }

        const data = await post('/steiner-analysis', {
          landmarks: parsedLandmarks,
          calibration_mmpp: parsedMmpp,
        })
        setSteinerResults(data)
      } catch (err) {
        setError(err.response?.data?.detail || 'Error calculando ángulos de Steiner')
      } finally {
        setLoading(false)
      }
    }
    calculate()
  }, [])

  const handleDownload = () => {
    navigate('/download')
  }

  if (loading) return <p className="text-center py-8">Calculando ángulos de Steiner...</p>
  if (error) return <p className="text-red-500 text-center py-8">{error}</p>

  const previewUrl = sessionStorage.getItem('preview_url')
  const imageId = sessionStorage.getItem('image_id')
  const landmarks = JSON.parse(sessionStorage.getItem('landmarks') || '[]')
  const formattedLandmarks = landmarks.map((lm) => ({
    x: Array.isArray(lm) ? lm[0] : lm.x,
    y: Array.isArray(lm) ? lm[1] : lm.y
  }))

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Paso 4: Resultados</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          {(previewUrl || imageId) && (
            <LandmarkCanvas
              imageId={imageId}
              imageUrl={previewUrl}
              landmarks={formattedLandmarks}
              scaleFactor={1}
            />
          )}
        </div>
        <div>
          <SteinerTable results={steinerResults} />
          <button
            onClick={handleDownload}
            className="mt-4 w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700"
          >
            Continuar a Descarga →
          </button>
        </div>
      </div>
    </div>
  )
}

export default ResultsStep
