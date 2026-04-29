import { useState } from 'react'
import { useApi } from '../hooks/useApi'

function AdminPanel() {
  const [password, setPassword] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [count, setCount] = useState(10)
  const [stats, setStats] = useState(null)
  const [codes, setCodes] = useState([])
  const [scale, setScale] = useState('')
  const [message, setMessage] = useState('')
  const { post, get } = useApi()

  const handleLogin = (e) => {
    e.preventDefault()
    if (password === 'aicefalo2025') {
      setAuthenticated(true)
      loadStats()
    } else {
      setMessage('Contraseña incorrecta')
    }
  }

  const loadStats = async () => {
    try {
      const data = await get('/admin/codes/stats')
      setStats(data)
    } catch (err) {
      console.error('Error loading stats', err)
    }
  }

  const handleGenerate = async () => {
    try {
      const data = await post('/admin/generate-codes', { count })
      setCodes(data.codes)
      loadStats()
      setMessage(`Generados ${data.count} códigos`)
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Error')
    }
  }

  const handleExportCsv = () => {
    window.open('/api/admin/codes/export-csv', '_blank')
  }

  const handleSaveScale = async () => {
    try {
      await post('/admin/scanner-scale', { value: parseFloat(scale) })
      setMessage('Escala guardada')
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Error')
    }
  }

  if (!authenticated) {
    return (
      <div className="max-w-md mx-auto mt-20">
        <h2 className="text-2xl font-bold mb-4 text-center">Panel de Administración</h2>
        <form onSubmit={handleLogin} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña"
            className="w-full border p-3 rounded-lg"
          />
          <button type="submit" className="w-full bg-blue-600 text-white py-3 rounded-lg">
            Entrar
          </button>
          {message && <p className="text-red-500">{message}</p>}
        </form>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Panel de Administración</h2>

      {message && (
        <p className="bg-green-100 text-green-800 p-3 rounded mb-4">{message}</p>
      )}

      {stats && (
        <div className="bg-gray-100 p-4 rounded-lg mb-6 grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats.available}</div>
            <div className="text-sm text-gray-600">Disponibles</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{stats.used}</div>
            <div className="text-sm text-gray-600">Usados</div>
          </div>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="font-bold mb-4">Generar Códigos</h3>
        <div className="flex gap-4">
          <input
            type="number"
            value={count}
            onChange={(e) => setCount(parseInt(e.target.value))}
            className="border p-2 rounded flex-1"
          />
          <button
            onClick={handleGenerate}
            className="bg-blue-600 text-white px-6 py-2 rounded"
          >
            Generar lote
          </button>
        </div>
        {codes.length > 0 && (
          <div className="mt-4">
            <p className="font-medium mb-2">Códigos generados:</p>
            <div className="bg-gray-50 p-3 rounded max-h-40 overflow-y-auto">
              {codes.map((c) => (
                <div key={c} className="font-mono text-sm">{c}</div>
              ))}
            </div>
            <button
              onClick={handleExportCsv}
              className="mt-2 text-blue-600 underline"
            >
              Exportar CSV
            </button>
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="font-bold mb-4">Escala del Escáner (mm/píxel)</h3>
        <div className="flex gap-4">
          <input
            type="number"
            step="0.01"
            value={scale}
            onChange={(e) => setScale(e.target.value)}
            placeholder="Ej: 0.1"
            className="border p-2 rounded flex-1"
          />
          <button
            onClick={handleSaveScale}
            className="bg-blue-600 text-white px-6 py-2 rounded"
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
