import { useLocation } from 'react-router-dom'

const STEPS = [
  { path: '/upload', label: '1. Subir Imagen' },
  { path: '/calibrate', label: '2. Calibración' },
  { path: '/process', label: '3. Procesar' },
  { path: '/results', label: '4. Resultados' },
  { path: '/download', label: '5. Descargar' },
]

function StepIndicator() {
  const location = useLocation()
  const currentPath = location.pathname

  const getCurrentStep = () => {
    return STEPS.findIndex(step => currentPath.startsWith(step.path))
  }

  const currentStep = getCurrentStep()

  return (
    <nav className="flex flex-col md:flex-row justify-center gap-2 md:gap-4 mb-6">
      {STEPS.map((step, idx) => {
        const isActive = idx === currentStep
        const isCompleted = idx < currentStep
        const isFuture = idx > currentStep
        let className = 'px-4 py-2 rounded-lg text-sm font-medium transition-colors '
        if (isActive) className += 'bg-blue-600 text-white'
        else if (isCompleted) className += 'bg-green-100 text-green-800'
        else className += 'bg-gray-200 text-gray-400 cursor-default'

        return (
          <div key={step.path} className={className}>
            {step.label}
          </div>
        )
      })}
    </nav>
  )
}

export default StepIndicator
