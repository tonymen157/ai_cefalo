import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import SteinerTable from './SteinerTable'
import LandmarkCanvas from './LandmarkCanvas'
import ToolPanel from './ToolPanel'

function ResultsStep() {
  const [analysisResults, setAnalysisResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { post } = useApi()

  // Estados de visualización
  const [showPoints, setShowPoints] = useState(true)
  const [showLines, setShowLines] = useState(true)
  const [showGrid, setShowGrid] = useState(false)
  const [showLabels, setShowLabels] = useState(true)
  const [pointRadius, setPointRadius] = useState(null)
  const [selectedLandmark, setSelectedLandmark] = useState(null)
  const [imageSize, setImageSize] = useState({ w: 0, h: 0 })
  const [zoom, setZoom] = useState(100)
  const [activeFilter, setActiveFilter] = useState('steiner')
  const [labelFontSize, setLabelFontSize] = useState(13)

  // Landmarks editables (copia local)
  const [editableLandmarks, setEditableLandmarks] = useState([])
  const [calibrationMmpp, setCalibrationMmpp] = useState(null)

  useEffect(() => {
    const landmarks = sessionStorage.getItem('landmarks')
    const mmpp = sessionStorage.getItem('calibration_mmpp')
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    const jobId = sessionStorage.getItem('job_id') || localStorage.getItem('job_id')

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

    const parsedMmpp = parseFloat(mmpp)
    setCalibrationMmpp(parsedMmpp || null)

    const parsedLandmarks = JSON.parse(landmarks)
    const formatted = parsedLandmarks.map((lm, idx) => ({
      x: Array.isArray(lm) ? lm[0] : lm.x ?? lm[0] ?? 0,
      y: Array.isArray(lm) ? lm[1] : lm.y ?? lm[1] ?? 0,
    }))
    setEditableLandmarks(formatted)

    const calculate = async () => {
      if (!parsedMmpp || isNaN(parsedMmpp) || parsedMmpp <= 0) {
        setError('Calibración no válida. Por favor configura la escala en el paso anterior.')
        setLoading(false)
        return
      }

      try {
        const data = await post('/steiner-analysis', {
          landmarks: parsedLandmarks,
          calibration_mmpp: parsedMmpp,
        })
        setAnalysisResults(data)
      } catch (err) {
        setError(err.response?.data?.detail || 'Error calculando ángulos de Steiner')
      } finally {
        setLoading(false)
      }
    }
    calculate()
  }, [])

  // Mover landmark (paso de 0.1mm en píxeles)
  const handleMoveLandmark = useCallback((idx, dx, dy, isDelta = true) => {
    setEditableLandmarks(prev => {
      const next = [...prev]
      if (!next[idx]) return prev
      if (isDelta) {
        next[idx] = { ...next[idx], x: next[idx].x + dx, y: next[idx].y + dy }
      } else {
        next[idx] = { ...next[idx], x: dx, y: dy }
      }
      return next
    })
  }, [])

  // Seleccionar landmark (click en canvas) - TOGGLE
  const handleSelectLandmark = useCallback((idx, dx, dy, isDelta) => {
    if (isDelta) {
      handleMoveLandmark(idx, dx, dy, true)
    } else {
      // Toggle: si ya está seleccionado, deseleccionar
      setSelectedLandmark(prev => prev === idx ? null : idx)
    }
  }, [handleMoveLandmark])

  // Recálculo de análisis con landmarks editados
  const handleRecalculate = async () => {
    if (!calibrationMmpp || !editableLandmarks.length) return
    setLoading(true)
    try {
      const payloadLandmarks = editableLandmarks.map(lm => [lm.x, lm.y])

      const data = await post('/steiner-analysis', {
        landmarks: payloadLandmarks,
        calibration_mmpp: calibrationMmpp,
      })
      setAnalysisResults(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error recalculando análisis')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    navigate('/download')
  }

  const handleResetLandmarks = async () => {
    if (window.confirm("¿Seguro que deseas descartar los cambios y volver a los puntos originales de la IA?")) {
      const originalStr = sessionStorage.getItem('landmarks') || '[]'
      const original = JSON.parse(originalStr)
      const formatted = original.map((lm) => ({
        x: Array.isArray(lm) ? lm[0] : lm.x ?? lm[0] ?? 0,
        y: Array.isArray(lm) ? lm[1] : lm.y ?? lm[1] ?? 0,
      }))

      setEditableLandmarks(formatted)
      setSelectedLandmark(null) // ← Limpiar selección

      if (!calibrationMmpp) return
      setLoading(true)
      try {
        const payloadLandmarks = formatted.map(lm => [lm.x, lm.y])
        const data = await post('/steiner-analysis', {
          landmarks: payloadLandmarks,
          calibration_mmpp: calibrationMmpp,
        })
        setAnalysisResults(data)
      } catch (err) {
        console.error("Error al restaurar análisis:", err)
      } finally {
        setLoading(false)
      }
    }
  }

  if (loading) return <p className="text-center py-8">Calculando ángulos de Steiner...</p>
  if (error) return <p className="text-red-500 text-center py-8">{error}</p>

  const previewUrl = sessionStorage.getItem('preview_url')
  const imageId = sessionStorage.getItem('image_id')

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-6">Paso 4: Resultados</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Canvas principal (2/3 del ancho) */}
        <div className="md:col-span-2">
          {(previewUrl || imageId) && (
            <LandmarkCanvas
              imageId={imageId}
              imageUrl={previewUrl}
              landmarks={editableLandmarks}
              showPoints={showPoints}
              showLines={showLines}
              showGrid={showGrid}
              showLabels={showLabels}
              pointRadius={pointRadius}
              selectedLandmark={selectedLandmark}
              onSelectLandmark={handleSelectLandmark}
              calibrationMmpp={calibrationMmpp}
              zoom={zoom}
              activeFilter={activeFilter}
              analysisResults={analysisResults}
              labelFontSize={labelFontSize}
            />
          )}
        </div>

        {/* Panel lateral (1/3 del ancho) */}
        <div className="space-y-4">
          <ToolPanel
            showPoints={showPoints}
            setShowPoints={setShowPoints}
            showLines={showLines}
            setShowLines={setShowLines}
            showGrid={showGrid}
            setShowGrid={setShowGrid}
            showLabels={showLabels}
            setShowLabels={setShowLabels}
            pointRadius={pointRadius ?? Math.max(4, Math.min(12, (imageSize.w || 512) / 150))}
            setPointRadius={setPointRadius}
            imageWidth={imageSize.w}
            selectedLandmark={selectedLandmark}
            landmarks={editableLandmarks}
            calibrationMmpp={calibrationMmpp}
            onMoveLandmark={handleMoveLandmark}
            onRecalculate={handleRecalculate}
            analysisResults={analysisResults}
            zoom={zoom}
            setZoom={setZoom}
            onReset={handleResetLandmarks}
            activeFilter={activeFilter}
            setActiveFilter={setActiveFilter}
            labelFontSize={labelFontSize}
            setLabelFontSize={setLabelFontSize}
          />

          <SteinerTable results={analysisResults} />

          <button
            onClick={handleDownload}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700"
          >
            Continuar a Descarga →
          </button>
        </div>
      </div>
    </div>
  )
}

export default ResultsStep
