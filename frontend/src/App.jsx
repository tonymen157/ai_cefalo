import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import UploadStep from './components/UploadStep'
import CalibrationStep from './components/CalibrationStep'
import ProcessingStep from './components/ProcessingStep'
import ResultsStep from './components/ResultsStep'
import DownloadStep from './components/DownloadStep'
import AdminPanel from './components/AdminPanel'

// Guardia global: redirigir a upload si no hay datos en pasos protegidos
function RequireData({ children }) {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
    const landmarks = sessionStorage.getItem('landmarks')
    const jobId = sessionStorage.getItem('job_id') || localStorage.getItem('job_id')

    // Solo verificar en rutas protegidas (no upload, no admin, no index)
    const isProtectedRoute = !['/', '/upload', '/admin'].includes(location.pathname)

    if (isProtectedRoute && !imageId) {
      console.warn(`No hay image_id. Redirigiendo a upload desde ${location.pathname}...`)
      navigate('/upload', { replace: true })
      return
    }

    // Paso 3 (process): requiere image_id (el job_id se crea al iniciar procesamiento)
    if (location.pathname === '/process' && !imageId) {
      console.warn('No hay image_id. Redirigiendo a upload...')
      navigate('/upload', { replace: true })
      return
    }

    // Paso 4/5 (results/download): requiere landmarks
    if ((location.pathname === '/results' || location.pathname === '/download') && (!landmarks || landmarks === '[]')) {
      console.warn('No hay landmarks. Redirigiendo a upload...')
      navigate('/upload', { replace: true })
      return
    }
  }, [location, navigate])

  return children
}

function App() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    // Detectar recarga (F5) y redirigir a index (upload)
    try {
      const entries = performance.getEntriesByType('navigation')
      if (entries.length > 0 && entries[0].type === 'reload') {
        navigate('/upload', { replace: true })
      }
    } catch (e) {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    // Prevención de pérdida de datos: advertir al usuario (no limpiar storage)
    const handleBeforeUnload = (e) => {
      const imageId = sessionStorage.getItem('image_id') || localStorage.getItem('image_id')
      const landmarks = sessionStorage.getItem('landmarks')

      // Solo advertir si hay datos cargados
      if (imageId || (landmarks && landmarks !== '[]')) {
        e.preventDefault()
        e.returnValue = 'Es posible que los cambios no se guarden. ¿Estás seguro de que deseas recargar la página?'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [location])

  return (
    <RequireData>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="upload" element={<UploadStep />} />
          <Route path="calibrate" element={<CalibrationStep />} />
          <Route path="process" element={<ProcessingStep />} />
          <Route path="results" element={<ResultsStep />} />
          <Route path="download" element={<DownloadStep />} />
        </Route>
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </RequireData>
  )
}

export default App
