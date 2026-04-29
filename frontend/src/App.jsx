import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import UploadStep from './components/UploadStep'
import CalibrationStep from './components/CalibrationStep'
import ProcessingStep from './components/ProcessingStep'
import ResultsStep from './components/ResultsStep'
import DownloadStep from './components/DownloadStep'
import AdminPanel from './components/AdminPanel'

function App() {
  const location = useLocation()

  useEffect(() => {
    // Protección nativa: Si el usuario refresca la página (F5) en una ruta que no es la inicial,
    // limpiamos el storage. Al recargar, los componentes (ej. UploadStep) no encontrarán los datos
    // y su propia lógica interna los expulsará al paso 1. Esto evita crashear React Router.
    const handleBeforeUnload = (e) => {
      if (location.pathname !== '/' && location.pathname !== '/upload') {
        sessionStorage.clear()
        localStorage.clear()
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [location])

  return (
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
  )
}

export default App
