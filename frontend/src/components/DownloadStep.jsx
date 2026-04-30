import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import html2pdf from 'html2pdf.js'

function DownloadStep() {
  const [downloading, setDownloading] = useState(false)
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const reportRef = useRef(null)
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  const baseUrl = apiBase.replace('/api', '')
  const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
  const navigate = useNavigate()

  // Obtener la imagen capturada del Paso 4
  const capturedImage = sessionStorage.getItem('captured_image') || null

  useEffect(() => {
    if (!imageId) {
      navigate('/upload', { replace: true })
    }
  }, [navigate])

  // Volver a edición (Paso 4)
  const handleBackToEdit = () => {
    navigate('/results')
  }

  // Abrir imagen en nueva pestaña
  const handlePreview = () => {
    if (capturedImage) {
      // Si es un Data URL muy largo, convertir a Blob URL
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
        // Limpiar el blob URL después de un tiempo
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 5000)
      } else {
        window.open(capturedImage, '_blank')
      }
    } else if (imageId) {
      window.open(`${baseUrl}/api/preview/pred_${imageId}`, '_blank')
    }
  }

  // Descargar imagen original
  const handleDownloadImage = async () => {
    if (!imageId) {
      alert('No hay imagen activa. Por favor, procesa una radiografía primero.')
      return
    }

    setDownloading(true)
    const imageUrl = `${baseUrl}/api/preview/pred_${imageId}`

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
                  src={`${baseUrl}/api/preview/pred_${imageId}`}
                  alt="Radiografía"
                  className="max-w-full mx-auto mt-4"
                  style={{ maxHeight: '400px' }}
                />
              )}
            </div>
          )}
        </div>

        {/* Tablas clínicas */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">Resultados Clínicos</h3>
          <div className="bg-gray-50 p-4 rounded border border-gray-200">
            <p className="text-sm text-gray-600">
              Los resultados del análisis cefalométrico se muestran a continuación.
              Este reporte es una herramienta de apoyo educativo.
            </p>
            {/* Aquí se pueden agregar las tablas de resultados dinámicamente */}
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-sm text-yellow-800">
                <strong>Nota:</strong> Para ver los valores detallados de los ángulos (SNA, SNB, ANB, Wits, etc.),
                por favor regresa al Paso 4 donde se muestran todas las tablas clínicas.
              </p>
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-8 pt-4 border-t border-gray-300 text-center">
          <p className="text-xs text-gray-500">
            AI-Céfalo es una herramienta de apoyo educativo para estudiantes.
            Los resultados NO reemplazan el diagnóstico profesional certificado.
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
            disabled={downloading}
            className="bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium transition"
          >
            {downloading ? 'Procesando...' : '💾 Descargar Radiografía'}
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
