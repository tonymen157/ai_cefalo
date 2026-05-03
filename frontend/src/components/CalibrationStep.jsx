import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { BASE_URL } from '../config'

function CalibrationStep() {
  const navigate = useNavigate()
  const imgRef = useRef(null)

  // FASE 2.1: Prevención del Estado Fantasma - imageId como state
  const [imageId, setImageId] = useState(() => sessionStorage.getItem('image_id') || '')
  const [previewUrlState, setPreviewUrlState] = useState(() => sessionStorage.getItem('preview_url') || '')

  // Estados
  const [clicks, setClicks] = useState([])
  const [modalOpen, setModalOpen] = useState(false)
  const [distanceMm, setDistanceMm] = useState('')
  const [calibrationResult, setCalibrationResult] = useState(null)
  const [error, setError] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [imgLoaded, setImgLoaded] = useState(false)
  const [zoom, setZoom] = useState(100)
  const [pointSize, setPointSize] = useState(4)
  const [aspectRatio, setAspectRatio] = useState('auto')

  // FASE 2.1: useEffect que depende de imageId - Limpieza cuando cambia
  useEffect(() => {
    const currentImageId = sessionStorage.getItem('image_id')
    const currentPreviewUrl = sessionStorage.getItem('preview_url')

    if (!currentImageId) {
      navigate('/upload')
      return
    }

    setImageId(currentImageId)
    setPreviewUrlState(currentPreviewUrl || '')

    // SIEMPRE limpiar estado cuando cambie imageId
    setClicks([])
    setCalibrationResult(null)
    setDistanceMm('')
    setModalOpen(false)
    setError('')
    setImgLoaded(false)
    sessionStorage.removeItem('calibration_mmpp')
    sessionStorage.removeItem('calibration_clicks')

    // previewUrl es como '/api/images/xxx.jpg' (relativo al backend)
    const backendBase = BASE_URL.replace(/\/api$/, '')
    if (currentPreviewUrl) {
      setImageUrl(`${backendBase}${currentPreviewUrl}`)
    } else {
      setImageUrl(`${backendBase}/api/images/${currentImageId}.jpg`)
    }

    // Cargar estados guardados (solo si no acabamos de limpiar)
    const savedClicks = sessionStorage.getItem('calibration_clicks')
    let hasValidClicks = false

    if (savedClicks) {
      try {
        const parsedClicks = JSON.parse(savedClicks)
        if (Array.isArray(parsedClicks) && parsedClicks.length === 2) {
          setClicks(parsedClicks)
          hasValidClicks = true
        }
      } catch (e) {
        console.error('Error cargando clicks guardados:', e)
      }
    }

    // Solo restaurar calibrationResult si hay clicks válidos
    if (hasValidClicks) {
      const savedCalibration = sessionStorage.getItem('calibration_mmpp')
      if (savedCalibration && parseFloat(savedCalibration) > 0) {
        setCalibrationResult(parseFloat(savedCalibration))
      }
    }

    const savedPointSize = sessionStorage.getItem('calibration_pointsize')
    if (savedPointSize) {
      const parsed = parseInt(savedPointSize)
      if (parsed >= 1 && parsed <= 15) setPointSize(parsed)
    }
  }, [navigate, imageId])

  useEffect(() => {
    if (clicks.length > 0) {
      sessionStorage.setItem('calibration_clicks', JSON.stringify(clicks))
    }
  }, [clicks])

  useEffect(() => {
    sessionStorage.setItem('calibration_pointsize', pointSize.toString())
  }, [pointSize])

  const handleImageLoad = (e) => {
    setImgLoaded(true)
    setAspectRatio(`${e.target.naturalWidth} / ${e.target.naturalHeight}`)
  }

  // FASE 3: Matemática a Prueba de Zoom (Coordenadas Absolutas)
  const handleImageClick = (e) => {
    setClicks(prev => {
      if (prev.length >= 2) return prev

      const img = imgRef.current
      if (!img || !img.complete || img.naturalWidth === 0) return prev

      // PROHIBIDO offsetX/offsetY - Usar getBoundingClientRect + clientX/clientY
      const rect = img.getBoundingClientRect()
      const scaleX = img.naturalWidth / rect.width
      const scaleY = img.naturalHeight / rect.height

      const x = Math.round((e.clientX - rect.left) * scaleX)
      const y = Math.round((e.clientY - rect.top) * scaleY)

      if (prev.length === 0) {
        // Primer clic: guardar normalmente
        return [...prev, { x, y }]
      } else if (prev.length === 1) {
        // Segundo clic: BLOQUEO ORTOGONAL - Forzar X = clicks[0].x
        setTimeout(() => setModalOpen(true), 0)
        return [...prev, { x: prev[0].x, y }]
      }
      return prev
    })
  }

  // Distancia euclidiana usando solo el eje Y (por el bloqueo ortogonal)
  const getPixelDistance = () => {
    if (clicks.length !== 2) return 0
    const [p1, p2] = clicks
    return Math.abs(p2.y - p1.y)
  }

  // FASE 2.3: Relajar la Validación en el Modal (0.01 - 2.0)
  const handleCalculate = () => {
    // Validación estricta al inicio
    if (!clicks || clicks.length !== 2) {
      setError('No hay puntos marcados. Marca dos puntos en la imagen.')
      return
    }

    const mm = parseFloat(distanceMm)
    if (Number.isNaN(mm) || mm <= 0) {
      setError('Por favor ingresa una distancia válida en milímetros')
      return
    }

    setError('')

    const pixelDistance = getPixelDistance()
    if (pixelDistance === 0) {
      setError('Error calculando la distancia en píxeles. Verifica los puntos marcados.')
      return
    }

    const mmPerPixel = mm / pixelDistance

    // Rango amplio: 0.01-2.0 mm/px (cubre imágenes clínicas y redimensionadas)
    if (mmPerPixel < 0.01 || mmPerPixel > 2.0) {
      setError(
        `El valor calculado (${mmPerPixel.toFixed(4)} mm/px) está fuera del rango permitido (0.01 - 2.0 mm/px). ` +
        'Por favor verifica los puntos marcados e intenta de nuevo.'
      )
      return
    }

    // Fuera del rango clínico estándar (0.05-0.5) pero dentro del permitido: advertencia
    if (mmPerPixel < 0.05 || mmPerPixel > 0.5) {
      setError(`⚠️ Valor fuera del rango clínico estándar (0.05-0.5 mm/px). La precisión puede variar, pero puedes continuar.`)
      setCalibrationResult(mmPerPixel)
      sessionStorage.setItem('calibration_mmpp', mmPerPixel.toString())
      setModalOpen(false)
      return
    }

    setCalibrationResult(mmPerPixel)
    sessionStorage.setItem('calibration_mmpp', mmPerPixel.toString())
    setModalOpen(false)
  }

  // FASE 2.1: Fix de Estado Fantasma (Limpieza extrema)
  const handleReset = () => {
    setClicks([])
    setModalOpen(false)
    setDistanceMm('')
    setCalibrationResult(null)
    setError('')
    sessionStorage.removeItem('calibration_mmpp')
    sessionStorage.removeItem('calibration_clicks')
  }

  const handleContinue = () => {
    if (calibrationResult) {
      navigate('/process')
    }
  }

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 300))
  }

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 25))
  }

  const handleZoomReset = () => {
    setZoom(100)
  }

  // Renderizado de Puntos con porcentajes
  const getPercentPosition = (naturalPoint) => {
    const img = imgRef.current
    if (!img || !img.naturalWidth || !img.naturalHeight) return { left: '0%', top: '0%' }
    return {
      left: `${(naturalPoint.x / img.naturalWidth) * 100}%`,
      top: `${(naturalPoint.y / img.naturalHeight) * 100}%`,
    }
  }

  const getLinePropsPercent = () => {
    if (clicks.length !== 2) return null
    const [p1Natural, p2Natural] = clicks
    const img = imgRef.current
    if (!img || !img.naturalWidth || !img.naturalHeight) return null
    return {
      left1: `${(p1Natural.x / img.naturalWidth) * 100}%`,
      top1: `${(p1Natural.y / img.naturalHeight) * 100}%`,
      left2: `${(p2Natural.x / img.naturalWidth) * 100}%`,
      top2: `${(p2Natural.y / img.naturalHeight) * 100}%`,
    }
  }

  const linePercent = getLinePropsPercent()

  return (
    <div className="w-full max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Paso 2: Calibración</h2>

      <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
        <p className="text-blue-800">
          <strong>Instrucciones:</strong> Haz clic en dos puntos de la regla del cefalóstato
          en la radiografía. Luego ingresa la distancia real en milímetros entre esos puntos.
        </p>
      </div>

      {error && (
        <div className={`px-4 py-3 rounded mb-4 ${
          error.includes('⚠️') ? 'bg-orange-100 border border-orange-400 text-orange-700' : 'bg-red-100 border border-red-400 text-red-700'
        }`}>
          {error}
        </div>
      )}

      {calibrationResult && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          ✅ Calibración exitosa: {calibrationResult.toFixed(4)} mm/píxel
        </div>
      )}

      {/* Controles superiores: Zoom + Tamaño de punto */}
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        {/* Controles de zoom */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 font-bold"
            title="Alejar"
          >
            -
          </button>
          <span className="text-sm text-gray-600 min-w-[60px] text-center">
            {zoom}%
          </span>
          <button
            onClick={handleZoomIn}
            className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 font-bold"
            title="Acercar"
          >
            +
          </button>
          <button
            onClick={handleZoomReset}
            className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 text-xs"
            title="Tamaño original"
          >
            Reset
          </button>
        </div>

        {/* Slider de tamaño de punto */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Punto:</label>
          <input
            type="range"
            min="1"
            max="15"
            value={pointSize}
            onChange={(e) => setPointSize(parseInt(e.target.value))}
            className="w-24 cursor-pointer"
          />
          <span className="text-sm text-gray-600 min-w-[30px]">
            {pointSize}px
          </span>
        </div>
      </div>

      {/* Contenedor padre con overflow para permitir scroll en el zoom */}
      <div className="relative w-full h-[600px] bg-gray-100 rounded-lg overflow-auto border-2 border-gray-300 p-4">

        {/* Wrapper que abraza milimétricamente la imagen - zoom vía dimensiones de layout */}
        <div
          className="relative shadow-md cursor-crosshair bg-black flex-shrink-0"
          style={{
            width: zoom <= 100 ? 'auto' : `${zoom}%`,
            maxWidth: zoom <= 100 ? '100%' : 'none',
            maxHeight: zoom <= 100 ? '550px' : 'none',
            aspectRatio: aspectRatio,
            margin: zoom <= 100 ? 'auto' : '0',
          }}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Radiografía para calibrar"
            className="w-full h-full block select-none cursor-crosshair"
            onClick={handleImageClick}
            onLoad={handleImageLoad}
            onError={() => {
              console.error('Error cargando imagen:', imageUrl)
              setError(`Error cargando la imagen`)
            }}
            crossOrigin="anonymous"
          />

          {/* Capa de Puntos (Solo se renderiza si la imagen cargó) */}
          {imgLoaded && (
            <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
              {/* Línea de calibración */}
              {linePercent && (
                <svg
                  className="absolute top-0 left-0"
                  style={{ width: '100%', height: '100%' }}
                >
                  <line
                    x1={linePercent.left1}
                    y1={linePercent.top1}
                    x2={linePercent.left2}
                    y2={linePercent.top2}
                    stroke="red"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                </svg>
              )}

              {/* Puntos numerados */}
              {clicks.map((click, idx) => {
                const pos = getPercentPosition(click)
                return (
                  <div
                    key={idx}
                    style={{
                      position: 'absolute',
                      left: pos.left,
                      top: pos.top,
                      transform: 'translate(-50%, -50%)',
                      zIndex: 10,
                    }}
                  >
                    <div
                      style={{
                        width: `${pointSize}px`,
                        height: `${pointSize}px`,
                        borderRadius: '50%',
                        backgroundColor: 'red',
                        border: '2px solid white',
                        boxShadow: '0 0 3px rgba(0,0,0,0.5)',
                      }}
                    />
                    <span
                      style={{
                        position: 'absolute',
                        left: `${pointSize + 4}px`,
                        top: `-${pointSize}px`,
                        color: 'red',
                        fontSize: '12px',
                        fontWeight: 'bold',
                      }}
                    >
                      {idx + 1}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        {clicks.length === 0 && 'Haz clic en el primer punto de la regla...'}
        {clicks.length === 1 && 'Haz clic en el segundo punto de la regla...'}
        {clicks.length === 2 && !calibrationResult && 'Ingresa la distancia real en el modal...'}
        {clicks.length === 2 && calibrationResult && 'Calibración completada. Puedes continuar.'}
      </div>

      <div className="mt-6 flex gap-4">
        {clicks.length > 0 && (
          <button
            onClick={handleReset}
            className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
          >
            🗑️ Borrar Puntos
          </button>
        )}

        <button
          onClick={handleContinue}
          disabled={!calibrationResult}
          className="bg-blue-600 text-white px-6 py-3 rounded hover:bg-blue-700 disabled:bg-gray-400 font-medium"
        >
          Continuar al Análisis →
        </button>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4">Calibración</h3>
            <p className="mb-2 text-gray-700">
              Se han marcado dos puntos en la imagen.
            </p>
            <p className="mb-4 text-gray-600">
              ¿Cuántos milímetros reales hay entre esos dos puntos?
            </p>
            <input
              type="number"
              step="0.1"
              min="0"
              value={distanceMm}
              onChange={(e) => setDistanceMm(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded mb-4 focus:border-blue-500 focus:outline-none"
              placeholder="Distancia en mm"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCalculate()
              }}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setModalOpen(false); setClicks([]); }}
                className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400"
              >
                Cancelar
              </button>
              <button
                onClick={handleCalculate}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Calcular
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CalibrationStep
