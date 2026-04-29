import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function DownloadStep() {
  const [downloading, setDownloading] = useState(false)
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  const baseUrl = apiBase.replace('/api', '')
  const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
  const navigate = useNavigate()

  useEffect(() => {
    if (!imageId) {
      navigate('/upload', { replace: true })
    }
  }, [navigate])

  const handleDownload = async () => {
    if (!imageId) {
      alert('No hay imagen activa. Por favor, procesa una radiografía primero.')
      return
    }

    setDownloading(true)
    const imageUrl = `${baseUrl}/api/preview/pred_${imageId}`

    try {
      // Usamos fetch y Blob para forzar la descarga en el navegador
      // en lugar de que el navegador simplemente abra la imagen
      const response = await fetch(imageUrl)
      if (!response.ok) throw new Error('Imagen no encontrada')

      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = blobUrl
      a.download = `Cefalometria_AI_${imageId.substring(0, 8)}.jpg`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      alert(err.message || 'Error al descargar la imagen')
    } finally {
      setDownloading(false)
    }
  }

  const handlePreview = () => {
    if (!imageId) {
      alert('No hay imagen activa.')
      return
    }
    window.open(`${baseUrl}/api/preview/pred_${imageId}`, '_blank')
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Paso 5: Descargar Resultados</h2>
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg mb-6">
        <p className="text-blue-800 font-medium mb-2">✅ Análisis Completado</p>
        <p className="text-gray-600 text-sm">Descarga tu radiografía en máxima calidad con los 29 landmarks y el trazado anatómico generado por la IA.</p>
      </div>

      <button
        onClick={handleDownload}
        disabled={downloading}
        className="mt-4 w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400 text-lg font-medium transition"
      >
        {downloading ? 'Procesando descarga...' : '💾 Descargar Radiografía (Alta Resolución)'}
      </button>

      <div className="mt-4">
        <button
          onClick={handlePreview}
          className="w-full bg-gray-200 text-gray-700 py-3 rounded-lg hover:bg-gray-300 font-medium transition"
        >
          👁️ Abrir imagen en nueva pestaña
        </button>
      </div>
    </div>
  )
}

export default DownloadStep
