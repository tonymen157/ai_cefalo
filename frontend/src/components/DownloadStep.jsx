import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import html2pdf from 'html2pdf.js'
import SteinerTable from './SteinerTable'

function DownloadStep() {
  const [downloading, setDownloading] = useState(false)
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const [analysisResults, setAnalysisResults] = useState(null)
  const reportRef = useRef(null)
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  const baseUrl = apiBase.replace('/api', '')
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

  // Obtener valor de resultado de forma segura
  const getResult = (key, decimals = 1) => {
    const val = analysisResults?.[key]
    if (val == null || isNaN(val)) return '--'
    return `${parseFloat(val).toFixed(decimals)}`
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

        {/* Tablas clínicas COMPLETAS */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">Resultados Clínicos Completos</h3>

          {/* Diagnóstico de Clase Esqueletal */}
          {analysisResults?.clase_esqueletal && (
            <div className={`text-center py-2 px-4 rounded-lg border font-bold text-sm mb-4 ${
              analysisResults.clase_esqueletal === 'Clase III'
                ? 'bg-orange-100 text-orange-800 border-orange-300'
                : analysisResults.clase_esqueletal === 'Clase II'
                ? 'bg-red-100 text-red-800 border-red-300'
                : 'bg-green-100 text-green-800 border-green-300'
            }`}>
              Diagnóstico Esqueletal: {analysisResults.clase_esqueletal}
              {analysisResults?.ANB != null && ` (ANB: ${parseFloat(analysisResults.ANB).toFixed(1)}°, Wits: ${analysisResults.WITS != null ? parseFloat(analysisResults.WITS).toFixed(1) + 'mm' : 'N/A'})`}
            </div>
          )}

          {/* 1. Medidas Clase Esqueletal (SNA, SNB, ANB, Wits) */}
          <div className="mb-6">
            <h4 className="text-md font-bold text-gray-700 mb-2 border-b pb-1">1. Medidas Clase Esqueletal</h4>
            <table className="w-full text-sm border-collapse mb-4">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-3 py-2 border-b">Medida</th>
                  <th className="text-center px-3 py-2 border-b">Valor Normal</th>
                  <th className="text-center px-3 py-2 border-b">Paciente</th>
                  <th className="text-center px-3 py-2 border-b">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">SNA</td>
                  <td className="text-center px-3 py-2 text-gray-500">82° (±3.5)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('SNA')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.SNA_interp?.includes('Clase') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.SNA_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">SNB</td>
                  <td className="text-center px-3 py-2 text-gray-500">80° (±3.5)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('SNB')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.SNB_interp?.includes('Clase') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.SNB_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">ANB</td>
                  <td className="text-center px-3 py-2 text-gray-500">2° (±2)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('ANB')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.ANB_interp?.includes('Clase III') ? 'bg-orange-100 text-orange-800'
                      : analysisResults?.ANB_interp?.includes('Clase II') ? 'bg-red-100 text-red-800'
                      : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.ANB_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Wits</td>
                  <td className="text-center px-3 py-2 text-gray-500">0.5mm (±2.5)</td>
                  <td className="text-center px-3 py-2 font-bold">{analysisResults?.WITS != null ? getResult('WITS') + 'mm' : '--'}</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.WITS_interp?.includes('Clase') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.WITS_interp || '--'}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 2. Inclinación Dental (Steiner & Ricketts) */}
          <div className="mb-6">
            <h4 className="text-md font-bold text-gray-700 mb-2 border-b pb-1">2. Inclinación Dental (Steiner)</h4>
            <table className="w-full text-sm border-collapse mb-4">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-3 py-2 border-b">Medida</th>
                  <th className="text-center px-3 py-2 border-b">Valor Normal</th>
                  <th className="text-center px-3 py-2 border-b">Paciente</th>
                  <th className="text-center px-3 py-2 border-b">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">1 Sup (Steiner)</td>
                  <td className="text-center px-3 py-2 text-gray-500">109° (±6)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('1_Sup')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.Dental_1Sup_interp?.includes('↓') ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.Dental_1Sup_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">1 Inf (Steiner)</td>
                  <td className="text-center px-3 py-2 text-gray-500">93° (±6)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('1_Inf')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      analysisResults?.Dental_1Inf_interp?.includes('↓') ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'
                    }`}>{analysisResults?.Dental_1Inf_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">1 Sup (Ricketts)</td>
                  <td className="text-center px-3 py-2 text-gray-500">110° (±5)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Ricketts_1Sup')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Ricketts_1Sup_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">1 Inf (Ricketts)</td>
                  <td className="text-center px-3 py-2 text-gray-500">90° (±5)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Ricketts_1Inf')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Ricketts_1Inf_interp || '--'}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 3. Línea Estética de Ricketts */}
          <div className="mb-6">
            <h4 className="text-md font-bold text-gray-700 mb-2 border-b pb-1">3. Línea Estética (Ricketts)</h4>
            <table className="w-full text-sm border-collapse mb-4">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-3 py-2 border-b">Medida</th>
                  <th className="text-center px-3 py-2 border-b">Valor Normal</th>
                  <th className="text-center px-3 py-2 border-b">Paciente</th>
                  <th className="text-center px-3 py-2 border-b">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Ls - Línea E</td>
                  <td className="text-center px-3 py-2 text-gray-500">-1mm (±2)</td>
                  <td className="text-center px-3 py-2 font-bold">{analysisResults?.Ls_E != null ? `${analysisResults.Ls_E >= 0 ? '+' : ''}${parseFloat(analysisResults.Ls_E).toFixed(1)}mm` : '--'}</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Ls_E_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Li - Línea E</td>
                  <td className="text-center px-3 py-2 text-gray-500">0mm (±2)</td>
                  <td className="text-center px-3 py-2 font-bold">{analysisResults?.Li_E != null ? `${analysisResults.Li_E >= 0 ? '+' : ''}${parseFloat(analysisResults.Li_E).toFixed(1)}mm` : '--'}</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Li_E_interp || '--'}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 4. Medidas Lineales Jarabak */}
          <div className="mb-6">
            <h4 className="text-md font-bold text-gray-700 mb-2 border-b pb-1">4. Medidas Lineales (Jarabak)</h4>
            <table className="w-full text-sm border-collapse mb-4">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-3 py-2 border-b">Medida</th>
                  <th className="text-center px-3 py-2 border-b">Valor Normal</th>
                  <th className="text-center px-3 py-2 border-b">Paciente</th>
                  <th className="text-center px-3 py-2 border-b">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Silla (S-N-S-Ar)</td>
                  <td className="text-center px-3 py-2 text-gray-500">126° (±6)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Silla')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Silla_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Articular (N-S-Ar)</td>
                  <td className="text-center px-3 py-2 text-gray-500">120° (±6)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Articular')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Articular_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Goniaco (Ar-Go-Me)</td>
                  <td className="text-center px-3 py-2 text-gray-500">130° (±6)</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Goniaco')}°</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Goniaco_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Base Craneal Ant (N-S)</td>
                  <td className="text-center px-3 py-2 text-gray-500">~70mm</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Base_Craneal_Ant')}mm</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Base_Craneal_Ant_interp || '--'}</span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Cuerpo Mandibular (Go-Me)</td>
                  <td className="text-center px-3 py-2 text-gray-500">~75mm</td>
                  <td className="text-center px-3 py-2 font-bold">{getResult('Cuerpo_Mandibular')}mm</td>
                  <td className="text-center px-3 py-2">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">{analysisResults?.Cuerpo_Mandibular_interp || '--'}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* SteinerTable original (si está disponible) */}
          {analysisResults && <SteinerTable results={analysisResults} />}
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
