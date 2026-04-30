import { useEffect, useRef, useState } from 'react'
import LANDMARKS from '../constants/landmarks'

function LandmarkCanvas({
  imageId,
  imageUrl,
  landmarks = [],
  showPoints = true,
  showLines = true,
  showGrid = false,
  pointRadius = null,
  selectedLandmark,
  onSelectLandmark,
  calibrationMmPp,
  zoom = 100,
  activeFilter = 'steiner',
}) {
  const canvasRef = useRef(null)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })
  const [hoverIdx, setHoverIdx] = useState(null)
  const [tooltip, setTooltip] = useState({ show: false, x: 0, y: 0, text: '' })

  const radius = pointRadius ?? Math.max(4, Math.min(12, (imgSize.w || 512) / 150))

  const getFinalUrl = () => {
    const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
    const baseUrl = apiBase.replace(/\/api$/, '')
    if (imageUrl && imageUrl.startsWith('http')) return imageUrl
    if (imageUrl) return `${baseUrl}/${imageUrl.replace(/^\//, '')}`
    if (imageId) return `${baseUrl}/api/preview/pred_${imageId}`
    return null
  }

  // Cargar imagen
  useEffect(() => {
    const finalUrl = getFinalUrl()
    if (!finalUrl) return
    const img = new Image()
    img.onload = () => setImgSize({ w: img.width, h: img.height })
    img.onerror = () => console.error("Error cargando imagen:", finalUrl)
    img.src = finalUrl
  }, [imageId, imageUrl])

  // Dibujar Canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !imgSize.w) return

    const rect = canvas.getBoundingClientRect()
    const stretchRatio = rect.width ? (rect.width / imgSize.w) : 1
    const dynamicRadius = pointRadius ?? (4 / stretchRatio)
    const dynamicLineWidth = 1.5 / stretchRatio

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    // Configuración nativa del buffer (No tocar, asegura calidad médica)
    canvas.width = imgSize.w * dpr
    canvas.height = imgSize.h * dpr
    ctx.scale(dpr, dpr)

    // Dibujar imagen
    const finalUrl = getFinalUrl()
    if (finalUrl) {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, 0, 0, imgSize.w, imgSize.h)

        // Dibujar Grilla (Sobre la imagen)
        if (showGrid) {
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'; // Blanco semi-transparente
          ctx.lineWidth = Math.max(1, radius * 0.1);

          // Malla dinámica proporcional a la imagen
          const step = imgSize.w / 40;

          for (let x = 0; x <= imgSize.w; x += step) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, imgSize.h);
          }
          for (let y = 0; y <= imgSize.h; y += step) {
            ctx.moveTo(0, y);
            ctx.lineTo(imgSize.w, y);
          }
          ctx.stroke();
        }

        // Dibujar Líneas condicionales
        if (showLines && landmarks.length >= 29) {
          const drawLine = (idx1, idx2, color) => {
            const p1 = landmarks[idx1]
            const p2 = landmarks[idx2]
            if (!p1 || !p2 || p1.x == null || p2.x == null) return
            ctx.beginPath()
            ctx.strokeStyle = color
            ctx.lineWidth = dynamicLineWidth
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.stroke()
          }

          if (activeFilter === 'steiner') {
            drawLine(10, 4, '#EF4444')  // S-N (Rojo)
            drawLine(4, 0, '#3B82F6')   // N-A (Azul)
            drawLine(4, 2, '#22C55E')   // N-B (Verde)
            drawLine(14, 13, '#F59E0B') // Go-Gn Plano Mandibular (Naranja)
          }

          if (activeFilter === 'ricketts') {
            // Línea E de Ricketts: Sn(28, Nose Tip) → Pog'(27, Soft Pogonion)
            drawLine(28, 27, '#8B5CF6') // Morado
          }

          if (activeFilter === 'occlusal') {
            // Plano Oclusal: punto medio molares → punto medio incisivos
            const molarMid = {
              x: (landmarks[18].x + landmarks[19].x) / 2,
              y: (landmarks[18].y + landmarks[19].y) / 2
            }
            const incisorMid = {
              x: (landmarks[21].x + landmarks[17].x) / 2,
              y: (landmarks[21].y + landmarks[17].y) / 2
            }
            if (molarMid && incisorMid) {
              ctx.beginPath()
              ctx.strokeStyle = '#EC4899' // Rosa
              ctx.lineWidth = dynamicLineWidth
              ctx.moveTo(molarMid.x, molarMid.y)
              ctx.lineTo(incisorMid.x, incisorMid.y)
              ctx.stroke()
            }
          }

          if (activeFilter === 'jarabak') {
            // Polígono de Jarabak: N(4)-S(10)-Ar(11)-Go(14)-Me(3)-N(4)
            const jarabakPoints = [4, 10, 11, 14, 3, 4]
            ctx.beginPath()
            ctx.strokeStyle = '#10B981' // Verde
            ctx.lineWidth = dynamicLineWidth
            jarabakPoints.forEach((idx, i) => {
              const p = landmarks[idx]
              if (!p || p.x == null) return
              if (i === 0) ctx.moveTo(p.x, p.y)
              else ctx.lineTo(p.x, p.y)
            })
            ctx.stroke()
          }
        }

        // Dibujar Puntos
        if (showPoints) {
          landmarks.forEach((lm, idx) => {
            if (!lm || lm.x == null) return
            const info = LANDMARKS[idx]
            if (!info) return

            ctx.beginPath()
            ctx.arc(lm.x, lm.y, idx === selectedLandmark ? dynamicRadius * 1.5 : dynamicRadius, 0, Math.PI * 2)
            ctx.fillStyle = idx === selectedLandmark ? '#FFD700' : (info.color || '#EF4444')
            ctx.fill()
            ctx.strokeStyle = '#FFFFFF'
            ctx.lineWidth = dynamicLineWidth
            ctx.stroke()
          })
        }

        // Tooltip Dinámico
        if (hoverIdx !== null && tooltip.show) {
          const info = LANDMARKS[hoverIdx]
          if (info) {
            // 1. Escalar la fuente
            const fontSize = 14 / stretchRatio;
            ctx.font = `${fontSize}px sans-serif`;
            const text = `${info.id}: ${info.name}`;
            const metrics = ctx.measureText(text);

            // 2. Escalar dimensiones y posiciones de la caja
            const paddingX = 12 / stretchRatio;
            const boxHeight = 24 / stretchRatio;
            const offsetX = 10 / stretchRatio;
            const offsetY = 30 / stretchRatio;

            // 3. Dibujar fondo negro
            ctx.fillStyle = 'rgba(0,0,0,0.8)';
            ctx.fillRect(
              tooltip.x + offsetX,
              tooltip.y - offsetY,
              metrics.width + paddingX,
              boxHeight
            );

            // 4. Dibujar texto blanco centrado en su caja
            ctx.fillStyle = '#FFFFFF';
            ctx.textBaseline = 'middle';
            ctx.fillText(
              text,
              tooltip.x + offsetX + (paddingX / 2),
              tooltip.y - offsetY + (boxHeight / 2)
            );
          }
        }
      }
      img.src = finalUrl
    }
  }, [imageId, imageUrl, landmarks, showPoints, showLines, showGrid, radius, selectedLandmark, hoverIdx, tooltip, imgSize, zoom, activeFilter])

  // Teclado (Movimiento clínico en mm)
  useEffect(() => {
    if (selectedLandmark === null || !calibrationMmPp) return
    const handleKeyDown = (e) => {
      const stepPx = 0.1 / calibrationMmPp
      let dx = 0, dy = 0
      if (e.key === 'ArrowLeft') dx = -stepPx
      else if (e.key === 'ArrowRight') dx = stepPx
      else if (e.key === 'ArrowUp') dy = -stepPx
      else if (e.key === 'ArrowDown') dy = stepPx
      else return

      e.preventDefault()
      if (onSelectLandmark) onSelectLandmark(selectedLandmark, dx, dy, true)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedLandmark, calibrationMmPp, onSelectLandmark])

  // Mouse: Traducción de Coordenadas
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current
    if (!canvas || !imgSize.w) return
    const rect = canvas.getBoundingClientRect()

    // LA MAGIA: Traducir CSS a Píxeles Nativos
    const scaleX = imgSize.w / rect.width
    const scaleY = imgSize.h / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY

    let found = null
    landmarks.forEach((lm, idx) => {
      if (!lm || lm.x == null) return
      const dist = Math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
      if (dist < radius + 8) found = idx // Zona de click ligeramente ampliada
    })

    setHoverIdx(found)
    if (found !== null) {
      setTooltip({ show: true, x, y, text: '' })
      canvas.style.cursor = 'pointer'
    } else {
      setTooltip({ show: false, x: 0, y: 0, text: '' })
      canvas.style.cursor = 'crosshair'
    }
  }

  const handleClick = () => {
    if (hoverIdx !== null && onSelectLandmark) {
      onSelectLandmark(hoverIdx, 0, 0, false)
    }
  }

  if (!imgSize.w) return null

  return (
    <div className="w-full max-h-[80vh] overflow-auto border border-gray-300 rounded-lg bg-gray-100 shadow-inner p-1">
      <div
        className="relative mx-auto inline-block origin-top transition-all duration-200"
        style={{ width: `${zoom}%` }}
      >
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onClick={handleClick}
          className="w-full h-auto block"
        />
      </div>
    </div>
  )
}

export default LandmarkCanvas
