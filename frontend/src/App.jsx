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
