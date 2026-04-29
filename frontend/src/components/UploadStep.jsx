import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function UploadStep() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)
  const navigate = useNavigate()
  const { post } = useApi()

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) {
      return
    }
    // (a) Archivo seleccionado

    if (!selectedFile.type.match(/image\/(jpeg|png|jpg)/)) {
      const msg = 'Solo se permiten imágenes JPG o PNG'
      setError(msg)
      return
    }

    setFile(selectedFile)
    setError('')
    const reader = new FileReader()
    reader.onload = (e) => {
      setPreview(e.target.result)
    }
    reader.onerror = () => {
      setError('Error al leer el archivo')
    }
    reader.readAsDataURL(selectedFile)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    handleFileSelect(droppedFile)
  }

  const handleUpload = async () => {
    if (!file) {
      return
    }

    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const data = await post('/upload-image', formData)

      sessionStorage.setItem('image_id', data.image_id)
      localStorage.setItem('image_id', data.image_id)
      sessionStorage.setItem('preview_url', data.preview_url)
      navigate('/calibrate')

    } catch (err) {

      const msg = !err.response
        ? `Error de red: ${err.message}. ¿Backend en puerto 8000?`
        : err.response.status === 413
        ? 'Imagen demasiado grande'
        : err.response.status === 400
        ? err.response?.data?.detail || 'Formato inválido'
        : err.response.status === 500
        ? `Error 500: ${err.response?.data?.detail || 'Fallo interno'}`
        : err.response?.data?.detail || 'Error al subir la imagen'

      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Paso 1: Subir Radiografía</h2>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer hover:border-blue-400 transition-colors"
      >
        {preview ? (
          <img src={preview} alt="Preview" className="max-h-64 mx-auto mb-4 rounded" />
        ) : (
          <div>
            <p className="text-gray-500 mb-2">Arrastra una imagen aquí o haz clic</p>
            <p className="text-sm text-gray-400">JPG o PNG</p>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          onChange={(e) => handleFileSelect(e.target.files[0])}
          className="hidden"
        />
      </div>
      {error && (
        <div className="mt-2">
          <p className="text-red-500 font-medium">{error}</p>
          <p className="text-xs text-gray-500">Revisa la consola (F12) para detalles</p>
        </div>
      )}
      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-4 w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {uploading ? 'Subiendo...' : 'Continuar →'}
        </button>
      )}
    </div>
  )
}

export default UploadStep
