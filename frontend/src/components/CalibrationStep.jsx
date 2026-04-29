import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function CalibrationStep() {
  const [calibrationMode, setCalibrationMode] = useState('auto') // 'auto' | 'standard' | 'manual'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [manualValue, setManualValue] = useState('0.100')
  const [presets, setPresets] = useState([])
  const [selectedPreset, setSelectedPreset] = useState('carestream_cs8100')
  const [fixedScale, setFixedScale] = useState(null)
  const [autoDetectedScale, setAutoDetectedScale] = useState(null)
  const [calibrationResult, setCalibrationResult] = useState(null)
  const [imageId, setImageId] = useState(null)
  const navigate = useNavigate()
  const { get, post } = useApi()

  // GUARD DE SEGURIDAD AISLADO
  useEffect(() => {
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    if (!imageId) {
      navigate('/upload', { replace: true })
    }
  }, [navigate])

  useEffect(() => {
    const imgId = sessionStorage.getItem('image_id')
    if (imgId) {
      setImageId(imgId)
      // Try auto-detection from CSV first
      detectAutoScale(imgId)
    } else {
      // Also check localStorage as fallback
      const localImageId = localStorage.getItem('image_id')
      if (localImageId) {
        setImageId(localImageId)
        detectAutoScale(localImageId)
      }
    }

    // Load available presets
    const loadPresets = async () => {
      try {
        const data = await get('/calibrate/presets')
        setPresets(data.presets || [])
        if (data.presets && data.presets.length > 0) {
          setSelectedPreset(data.presets[0].id)
        }
      } catch (err) {
        console.error('Failed to load presets:', err)
      }
    }

    loadPresets()

    // Load fixed scale if available
    const loadFixedScale = async () => {
      try {
        const data = await get('/calibrate/fixed-scale')
        if (data.configured) {
          setFixedScale(data.mm_per_pixel)
        }
      } catch (err) {
        console.error('Failed to load fixed scale:', err)
      }
    }

    loadFixedScale()
  }, [get])

  const detectAutoScale = async (imgId) => {
    try {
      const data = await get(`/calibrate/auto?image_id=${imgId}`)
      if (data.mm_per_pixel) {
        setAutoDetectedScale(data.mm_per_pixel)
      }
    } catch (err) {
      // Auto-detection not available, that's fine
      setAutoDetectedScale(null)
    }
  }

  const handleApplyPreset = async () => {
    setLoading(true)
    setError('')
    setSuccess(false)
    try {
      const data = await post('/calibrate/apply-preset', {
        image_id: imageId,
        preset_id: selectedPreset,
      })

      sessionStorage.setItem('calibration_mmpp', data.mm_per_pixel.toString())
      sessionStorage.setItem('calibration_source', data.preset_id)
      setCalibrationResult(data)
      setSuccess(true)

      setTimeout(() => {
        navigate('/process')
      }, 800)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al aplicar preset')
      setLoading(false)
    }
  }

  const handleFixedScale = async () => {
    setLoading(true)
    setError('')
    setSuccess(false)
    try {
      const data = await get('/calibrate/fixed-scale')
      if (!data.configured) {
        setError('No hay escala fija configurada por el administrador.')
        setLoading(false)
        return
      }

      sessionStorage.setItem('calibration_mmpp', data.mm_per_pixel.toString())
      sessionStorage.setItem('calibration_source', 'scanner_fixed')
      setCalibrationResult({
        image_id: imageId,
        mm_per_pixel: data.mm_per_pixel,
        preset_id: 'scanner_fixed',
        preset_name: 'Escala Fija del Escáner',
        calibration_source: 'scanner_fixed',
        validated: true,
        method: 'fixed_scale',
      })
      setSuccess(true)

      setTimeout(() => {
        navigate('/process')
      }, 800)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error con escala fija')
      setLoading(false)
    }
  }

  const handleManual = async () => {
    const val = parseFloat(manualValue)
    if (!val || val <= 0 || val > 1.0) {
      setError('Por favor ingresa un valor válido (ej: 0.100 para 0.1 mm/px)')
      return
    }

    setLoading(true)
    setError('')
    setSuccess(false)
    try {
      const data = await post('/calibrate/manual', {
        x1: 0, y1: 0, x2: 1000, y2: 0,
        real_distance_mm: 100,
      })

      // Override with manual value
      const mmpp = parseFloat(manualValue)
      sessionStorage.setItem('calibration_mmpp', mmpp.toString())
      sessionStorage.setItem('calibration_source', 'manual_value')
      setCalibrationResult({
        ...data,
        mm_per_pixel: mmpp,
        image_id: imageId,
        preset_name: 'Calibración Manual',
        calibration_source: 'manual',
        validated: true,
        method: 'manual',
      })
      setSuccess(true)

      setTimeout(() => {
        navigate('/process')
      }, 800)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error en calibración manual')
      setLoading(false)
    }
  }

  const handleStandard = async () => {
    setLoading(true)
    setError('')
    setSuccess(false)
    try {
      // Use standard 0.100 mm/px
      sessionStorage.setItem('calibration_mmpp', '0.100')
      sessionStorage.setItem('calibration_source', 'standard_0.100')
      setCalibrationResult({
        image_id: imageId,
        mm_per_pixel: 0.100,
        preset_id: 'standard_0.100',
        preset_name: 'Valor Estándar (0.100 mm/px)',
        calibration_source: 'standard',
        validated: true,
        method: 'standard',
      })
      setSuccess(true)

      setTimeout(() => {
        navigate('/process')
      }, 800)
    } catch (err) {
      setError(err.message || 'Error al aplicar valor estándar')
      setLoading(false)
    }
  }

  const selectedPresetInfo = presets.find(p => p.id === selectedPreset)

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-2">Paso 2: Calibración</h2>
      <p className="text-gray-600 mb-6">
        Configura la escala (mm/píxel) para mediciones clínicas precisas.
      </p>

      {/* Unified Configurador de Escala - Dropdown */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Método de Calibración
        </label>
        <select
          value={calibrationMode}
          onChange={(e) => {
            setCalibrationMode(e.target.value)
            setError('')
            setSuccess(false)
          }}
          className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="auto">Equipo Detectado Automáticamente</option>
          <option value="standard">Valor Estándar (0.100 mm/px)</option>
          <option value="manual">Valor Manual</option>
        </select>
      </div>

      {/* Auto-detected equipment badge */}
      {calibrationMode === 'auto' && autoDetectedScale && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-green-700 font-medium">
              Equipo detectado automáticamente: {autoDetectedScale.toFixed(4)} mm/px
            </span>
          </div>
          <p className="text-green-600 text-sm mt-1">
            Calibración precisa basada en los metadatos de la imagen
          </p>
          <button
            onClick={() => {
              sessionStorage.setItem('calibration_mmpp', autoDetectedScale.toString())
              sessionStorage.setItem('calibration_source', 'auto_from_csv')
              setCalibrationResult({
                image_id: imageId,
                mm_per_pixel: autoDetectedScale,
                preset_id: 'auto_csv',
                preset_name: 'Auto-detectado',
                calibration_source: 'auto_from_csv',
                validated: true,
                method: 'auto',
              })
              setSuccess(true)
              setError('')
              setTimeout(() => navigate('/process'), 800)
            }}
            className="mt-3 w-full bg-green-600 text-white py-2.5 rounded-lg hover:bg-green-700 transition-colors font-medium"
          >
            Usar Calibración Detectada
          </button>
        </div>
      )}

      {calibrationMode === 'auto' && !autoDetectedScale && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-yellow-700">
              No se detectó equipo automáticamente para esta imagen.
            </span>
          </div>
          <p className="text-yellow-600 text-sm mt-1">
            Por favor selecciona otro método de calibración.
          </p>
        </div>
      )}

      {/* Standard Value */}
      {calibrationMode === 'standard' && (
        <div className="bg-blue-50 p-4 rounded-lg mb-4">
          <p className="text-blue-800 mb-3 font-medium">
            Valor Estándar Cefalométrico
          </p>
          <p className="text-sm text-blue-700 mb-4">
            Usa el valor estándar de 0.100 mm/px para equipos cefalométricos digitales modernos.
            Este es un valor típico ampliamente aceptado cuando no se dispone de información específica.
          </p>
          <div className="bg-white p-4 rounded-lg border border-blue-200 text-center">
            <span className="text-sm text-blue-600 mr-2">Calibración:</span>
            <span className="text-2xl font-bold text-blue-700">0.100</span>
            <span className="text-lg text-blue-500 ml-1">mm/px</span>
            <div className="text-xs text-blue-400 mt-2">Rango válido: 0.050 - 0.150 mm/px</div>
          </div>
          <button
            onClick={handleStandard}
            disabled={loading}
            className="mt-4 w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {loading ? 'Aplicando...' : 'Usar Valor Estándar (0.100 mm/px)'}
          </button>
        </div>
      )}

      {/* Manual Entry */}
      {calibrationMode === 'manual' && (
        <div className="bg-gray-50 p-4 rounded-lg mb-4">
          <p className="text-gray-700 mb-3 font-medium">
            Calibración Manual
          </p>
          <p className="text-sm text-gray-600 mb-4">
            Ingresa el valor de pixel size (mm/px) calculado manualmente o medido.
          </p>
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pixel Size (mm/px)
            </label>
            <input
              type="number"
              step="0.001"
              min="0.05"
              max="1.0"
              value={manualValue}
              onChange={(e) => {
                setManualValue(e.target.value)
                setError('')
              }}
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-lg"
              placeholder="0.100"
            />
          </div>
          <div className="bg-white p-3 rounded-lg border mb-4">
            <div className="text-center">
              <span className="text-sm text-gray-500">Calibración actual: </span>
              <span className="text-2xl font-bold text-gray-700">{parseFloat(manualValue || '0').toFixed(4)}</span>
              <span className="text-lg text-gray-500 ml-1">mm/px</span>
            </div>
            <div className="text-xs text-gray-400 mt-1 text-center">
              Ejemplos: 0.080 (alta resolución) | 0.100 (estándar) | 0.120 (baja resolución)
            </div>
          </div>
          <button
            onClick={handleManual}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {loading ? 'Aplicando...' : 'Aplicar Calibración Manual'}
          </button>
        </div>
      )}

      {/* Preset selection as alternative when auto not available */}
      {calibrationMode === 'auto' && presets.length > 0 && !autoDetectedScale && (
        <div className="bg-gray-50 p-4 rounded-lg mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            O selecciona un equipo manualmente:
          </label>
          <select
            value={selectedPreset}
            onChange={(e) => {
              setSelectedPreset(e.target.value)
              setError('')
            }}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {presets.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} - {p.mm_per_pixel} mm/px
                {p.valid ? ' ✓' : ' ⚠ fuera de rango'}
              </option>
            ))}
          </select>

          {selectedPresetInfo && (
            <div className="mt-3 p-3 bg-white rounded-lg border">
              <div className="text-sm text-gray-600">
                <span className="font-medium">{selectedPresetInfo.name}</span>
                <br />
                {selectedPresetInfo.description}
              </div>
            </div>
          )}

          <button
            onClick={handleApplyPreset}
            disabled={loading}
            className="mt-3 w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {loading ? 'Aplicando...' : 'Aplicar Calibración'}
          </button>
        </div>
      )}

      {error && <p className="text-red-500 mb-4 p-3 bg-red-50 rounded-lg">{error}</p>}

      {success && calibrationResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <div className="flex items-center text-green-700 mb-2">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-semibold">¡Calibración aplicada con éxito!</span>
          </div>
          <div className="text-sm text-green-700 space-y-1">
            <div><span className="font-medium">Escala:</span> {calibrationResult.mm_per_pixel} mm/px</div>
            <div><span className="font-medium">Método:</span> {calibrationResult.preset_name || calibrationResult.preset_id}</div>
          </div>
          <div className="text-xs text-green-500 mt-2">Redirigiendo al análisis...</div>
        </div>
      )}
    </div>
  )
}

export default CalibrationStep