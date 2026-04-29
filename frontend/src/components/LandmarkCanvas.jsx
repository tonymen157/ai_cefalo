import { useEffect, useState } from 'react'

function LandmarkCanvas({ imageId }) {
  const [imgSrc, setImgSrc] = useState('')

  useEffect(() => {
    if (!imageId) return
    const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
    const baseUrl = apiBase.replace('/api', '')
    setImgSrc(`${baseUrl}/api/preview/pred_${imageId}`)
  }, [imageId])

  if (!imgSrc) return null

  return (
    <img
      src={imgSrc}
      alt="Radiografía con landmarks"
      className="w-full border border-gray-300 rounded-lg"
    />
  )
}

export default LandmarkCanvas
