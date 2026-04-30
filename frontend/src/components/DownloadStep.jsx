import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import html2pdf from 'html2pdf.js'
import SteinerTable from './SteinerTable'
import { BASE_URL } from '../config'

function DownloadStep() {
  const [loading, setDownloading] = useState(false)
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const [analysisResults, setAnalysisResults] = useState(null)
  const reportRef = useRef(null)
  const baseUrl = BASE_URL
  const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
  const navigate = useNavigate()
  const location = useLocation()

  // Obtener la imagen: primero de React Router state, luego sessionStorage (fallback)
  const capturedImage = location.state?.capturedImage || sessionStorage.getItem('captured_image') || null

  // Cargar resultados del análisis desde sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem('analysis_results')
    if (stored) {
      try {
        setAnalysisResults(JSON.parse(stored))
      } catch (e) {
        console.error('Error leyendo resultados:', e)
      }
    }
  }, [])

  // SI NO HAY IMAGEN CAPTURADA: redirigir a upload (NO a results)
  useEffect(() => {
    // Si no hay capturedImage y no hay imageId -> upload
    // Si hay imageId pero no capturedImage -> tb debería ir a upload
    // (porque no hay canvas en Paso 5 para recapturar)
    if (!capturedImage && !imageId) {
      navigate('/upload', { replace: true })
    } else if (!capturedImage && imageId) {
      // Hay imageId pero no capturedImage (se recargó Paso 5)
      // Redirigir a upload con mensaje
      console.warn('No hay imagen capturada. Volviendo al inicio...')
      alert('No hay imagen capturada. Volviendo al inicio...')
      navigate('/upload', { replace: true })
    }
  }, [capturedImage, imageId, navigate])

  // Volver a edición (Paso 4)
  const handleBackToEdit = () => {
    navigate('/results')
  }

  // Abrir imagen en nueva pestaña
  const handlePreview = () => {
    if (capturedImage) {
      if (capturedImage.startsWith('data:')) {
        const byteString = atob(capturedImage.split(',')[1])
        const mimeString = capturedImage.split(',')[0].split(':')[1].split(';')[0]
        const ab = new ArrayBuffer(byteString.length)
        const ia = new Uint8Array(ab)
        for (let i = 0; i < byteString.length; i++) {
          ia[i] = byteString.charCodeAt(i)
        }
        const blob = new Blob([ab], { type: mimeString })
        const blobUrl = window.URL.createObjectURL(blob)
        window.open(blobUrl, '_blank')
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 5000)
      } else {
        window.open(capturedImage, '_blank')
      }
    } else if (imageId) {
      window.open(`${baseUrl}/api/images/pred_${imageId}`, '_blank')
    }
  }

  // Descargar imagen original
  const handleDownloadImage = async () => {
    if (!imageId) {
      alert('No hay imagen activa. Por favor, procesa una radiografía primero.')
      return
    }

    setDownloading(true)
    const imageUrl = `${baseUrl}/api/images/pred_${imageId}`

    try {
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

  // Generar PDF completo
  const handleGeneratePDF = async () => {
    if (!reportRef.current) return
    setPdfGenerating(true)

    try {
      const opt = {
        margin: 10,
        filename: `Reporte_Cefalometrico_AI_${imageId?.substring(0, 8) || 'reporte'}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      }

      await html2pdf().set(opt).from(reportRef.current).save()
    } catch (err) {
      console.error('Error generando PDF:', err)
      alert('Error al generar el PDF. Por favor intenta de nuevo.')
    } finally {
      setPdfGenerating(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Paso 5: Descargar Resultados</h2>

      {/* Botón prominente para volver a edición */}
      <div className="mb-6">
        <button
          onClick={handleBackToEdit}
          className="bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700 font-medium text-lg transition flex items-center gap-2"
        >
          ← Volver a Edición (Paso 4)
        </button>
        <p className="text-xs text-gray-500 mt-1">
          Conserva tus ediciones y configuraciones visuales intactas
        </p>
      </div>

      {/* Reporte para PDF */}
      <div ref={reportRef} className="bg-white p-8">
        {/* Encabezado */}
        <div className="text-center mb-6 border-b-2 border-gray-800 pb-4">
          <h1 className="text-2xl font-bold text-gray-800">Reporte Cefalométrico AI-Céfalo</h1>
          <p className="text-sm text-gray-600 mt-1">
            Análisis generado por Inteligencia Artificial
          </p>
          <p className="text-xs text-gray-500">
            Fecha: {new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* Imagen final capturada */}
        <div className="mb-6 text-center">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">Radiografía con Trazados</h3>
          {capturedImage ? (
            <img
              src={capturedImage}
              alt="Radiografía con trazados"
              className="max-w-full mx-auto border border-gray-300 rounded"
              style={{ maxHeight: '500px' }}
            />
          ) : (
            <div className="bg-gray-100 p-8 rounded border border-gray-300">
              <p className="text-gray-500">No hay imagen capturada disponible</p>
              {imageId && (
                <img
                  src={`${baseUrl}/api/images/pred_${imageId}`}
                  alt="Radiografía"
                  className="max-w-full mx-auto mt-4"
                  style={{ maxHeight: '400px' }}
                />
              )}
            </div>
          )}
        </div>

        {/* Resultados Clínicos: Solo el componente real (sin duplicados) */}
        <div className="mb-6">
          {analysisResults && <SteinerTable results={analysisResults} isPdfMode={true} />}
        </div>

        {/* Disclaimer */}
        <div className="mt-8 pt-4 border-t border-gray-300 text-center">
          <p className="text-xs text-gray-500">
            AI-Céfalo es una herramienta de apoyo educativo para estudiantes.
            Los resultados NO reemplazan el diagnóstico profesional certificado.
          </p>
        </div>

        {/* Branding y Contacto del Desarrollador (Footer del PDF) */}
        <div className="mt-6 pt-4 border-t-2 border-gray-400 text-center">
          <p className="text-xs text-gray-600 font-semibold">
            Software desarrollado por: <span className="text-gray-800">Anthony Mendoza - Ingeniero de Software</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Contacto: tonymen157@gmail.com | Tel: 0995126586
          </p>
        </div>
      </div>

      {/* Botones de acción */}
      <div className="mt-6 space-y-3">
        <button
          onClick={handleGeneratePDF}
          disabled={pdfGenerating}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-lg font-medium transition"
        >
          {pdfGenerating ? 'Generando PDF...' : '📄 Descargar Reporte Completo (PDF)'}
        </button>

        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={handleDownloadImage}
            disabled={loading}
            className="bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium transition"
          >
            {loading ? 'Procesando...' : '💾 Descargar Radiografía'}
          </button>

          <button
            onClick={handlePreview}
            className="bg-gray-200 text-gray-700 py-3 rounded-lg hover:bg-gray-300 font-medium transition"
          >
            👁️ Abrir Imagen
          </button>
        </div>
      </div>
    </div>
  )
}

export default DownloadStep
