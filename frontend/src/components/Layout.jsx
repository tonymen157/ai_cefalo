import { Outlet } from 'react-router-dom'
import DisclaimerBanner from './DisclaimerBanner'
import StepIndicator from './StepIndicator'

const STEPS = [
  { path: '/upload', label: 'Subir Imagen' },
  { path: '/calibrate', label: 'Calibración' },
  { path: '/process', label: 'Procesar' },
  { path: '/results', label: 'Resultados' },
  { path: '/download', label: 'Descargar' },
]

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <DisclaimerBanner />
      <div className="container mx-auto px-4 py-6 flex-1">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">AI-Cefalo</h1>
          <p className="text-gray-600">Análisis Cefalométrico Automático</p>
        </header>
        <StepIndicator steps={STEPS} />
        <main className="mt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
