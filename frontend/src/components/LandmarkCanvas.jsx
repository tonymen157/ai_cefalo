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
  analysisResults = null,
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

  // Helper: dibujar texto con fondo para legibilidad
  const drawLabel = (ctx, text, x, y, color, offsetX = 6, offsetY = -6) => {
    const finalX = x + offsetX
    const finalY = y + offsetY
    ctx.font = 'bold 13px sans-serif'
    const metrics = ctx.measureText(text)
    const pad = 4

    // Fondo semitransparente
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
    ctx.fillRect(finalX - pad, finalY - 11 + pad, metrics.width + pad * 2, 16)

    ctx.fillStyle = color
    ctx.textBaseline = 'top'
    ctx.fillText(text, finalX, finalY - 11)
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
    const lineWidth = 2.5

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    canvas.width = imgSize.w * dpr
    canvas.height = imgSize.h * dpr
    ctx.scale(dpr, dpr)

    const finalUrl = getFinalUrl()
    if (finalUrl) {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, 0, 0, imgSize.w, imgSize.h)

        // Grilla
        if (showGrid) {
          ctx.beginPath()
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
          ctx.lineWidth = Math.max(1, radius * 0.1)
          const step = imgSize.w / 40
          for (let x = 0; x <= imgSize.w; x += step) {
            ctx.moveTo(x, 0)
            ctx.lineTo(x, imgSize.h)
          }
          for (let y = 0; y <= imgSize.h; y += step) {
            ctx.moveTo(0, y)
            ctx.lineTo(imgSize.w, y)
          }
          ctx.stroke()
        }

        if (showLines && landmarks.length >= 29) {
          // Configuracion de sombra para contraste
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
          ctx.shadowBlur = 3

          const drawLine = (idx1, idx2, color) => {
            const p1 = landmarks[idx1]
            const p2 = landmarks[idx2]
            if (!p1 || !p2 || p1.x == null || p2.x == null) return
            ctx.beginPath()
            ctx.strokeStyle = color
            ctx.lineWidth = lineWidth
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.stroke()
          }

          // Obtener valores del analisis para etiquetas
          const res = analysisResults || {}

          // ---------- STEINER ----------
          if (activeFilter === 'steiner') {
            drawLine(10, 4, '#EF4444')   // S-N (Rojo)
            drawLine(4, 0, '#3B82F6')    // N-A (Azul)
            drawLine(4, 2, '#22C55E')    // N-B (Verde)
            drawLine(14, 13, '#F59E0B')  // Go-Gn (Naranja)

            // Etiquetas de angulos
            const nPt = landmarks[4]   // Nasion
            const sPt = landmarks[10]  // Sella
            const aPt = landmarks[0]   // A-point
            const bPt = landmarks[2]   // B-point

            if (nPt && sPt) drawLabel(ctx, `${res.SNA?.toFixed(1) ?? '--'}°`, (nPt.x + sPt.x) / 2, (nPt.y + sPt.y) / 2, '#EF4444')
            if (nPt && sPt) drawLabel(ctx, `${res.SNB?.toFixed(1) ?? '--'}°`, (nPt.x + sPt.x) / 2, (nPt.y + sPt.y) / 2 + 16, '#3B82F6')
            if (aPt && bPt && nPt) {
              const anbText = res.ANB != null ? `${res.ANB.toFixed(1)}°` : '--°'
              drawLabel(ctx, `ANB: ${anbText}`, (aPt.x + bPt.x) / 2, nPt.y - 20, '#8B5CF6')
            }
            if (res.WITS != null) {
              const witsText = `${res.WITS >= 0 ? '+' : ''}${res.WITS.toFixed(1)}mm`
              drawLabel(ctx, `Wits: ${witsText}`, (aPt?.x ?? 0) + 10, (aPt?.y ?? 0) + 30, '#06B6D4')
            }
          }

          // ---------- WITS ----------
          if (activeFilter === 'wits') {
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
              ctx.strokeStyle = '#EC4899'
              ctx.lineWidth = lineWidth
              ctx.moveTo(molarMid.x, molarMid.y)
              ctx.lineTo(incisorMid.x, incisorMid.y)
              ctx.stroke()

              drawLabel(ctx, 'Plano Oclusal', (molarMid.x + incisorMid.x) / 2, molarMid.y - 12, '#EC4899')

              const drawPerp = (ptIdx, label) => {
                const pt = landmarks[ptIdx]
                if (!pt || pt.x == null) return
                const vx = incisorMid.x - molarMid.x
                const vy = incisorMid.y - molarMid.y
                const vLen = Math.sqrt(vx * vx + vy * vy)
                if (vLen === 0) return
                const t = ((pt.x - molarMid.x) * vx + (pt.y - molarMid.y) * vy) / (vLen * vLen)
                const projX = molarMid.x + t * vx
                const projY = molarMid.y + t * vy

                ctx.beginPath()
                ctx.strokeStyle = '#06B6D4'
                ctx.lineWidth = lineWidth
                ctx.setLineDash([6, 4])
                ctx.moveTo(pt.x, pt.y)
                ctx.lineTo(projX, projY)
                ctx.stroke()
                ctx.setLineDash([])

                // Etiqueta mm
                const mmText = label
                drawLabel(ctx, mmText, (pt.x + projX) / 2, (pt.y + projY) / 2, '#06B6D4', 8, -8)
              }

              if (res.WITS != null) {
                const witsVal = res.WITS.toFixed(1)
                drawPerp(0, `A: ${witsVal}mm`)  // A-point
                drawPerp(2, `B: ${witsVal}mm`)  // B-point
              } else {
                drawPerp(0, 'A')
                drawPerp(2, 'B')
              }
            }
          }

          // ---------- RICKETTS ----------
          if (activeFilter === 'ricketts') {
            drawLine(28, 27, '#8B5CF6') // Sn -> Pog' (Morado)

            // Etiquetas de distancia
            const lsPt = landmarks[25]  // Ls (Upper Lip)
            const liPt = landmarks[24]  // Li (Lower Lip)

            if (lsPt && res.Ls_E != null) {
              const val = res.Ls_E.toFixed(1)
              const sign = res.Ls_E >= 0 ? '+' : ''
              drawLabel(ctx, `Ls: ${sign}${val}mm`, lsPt.x + 10, lsPt.y, '#8B5CF6')
            }
            if (liPt && res.Li_E != null) {
              const val = res.Li_E.toFixed(1)
              const sign = res.Li_E >= 0 ? '+' : ''
              drawLabel(ctx, `Li: ${sign}${val}mm`, liPt.x + 10, liPt.y, '#8B5CF6')
            }

            // Linea E etiqueta
            drawLabel(ctx, 'Linea E', (landmarks[28]?.x + landmarks[27]?.x) / 2 || 0, (landmarks[28]?.y + landmarks[27]?.y) / 2 || 0, '#8B5CF6', 0, -12)
          }

          // ---------- JARABAK ----------
          if (activeFilter === 'jarabak') {
            const jarabakPoints = [4, 10, 11, 14, 3, 4] // N-S-Ar-Go-Me-N
            ctx.beginPath()
            ctx.strokeStyle = '#10B981'
            ctx.lineWidth = lineWidth
            jarabakPoints.forEach((idx, i) => {
              const p = landmarks[idx]
              if (!p || p.x == null) return
              if (i === 0) ctx.moveTo(p.x, p.y)
              else ctx.lineTo(p.x, p.y)
            })
            ctx.stroke()

            // Etiquetas de angulos en los vertices
            const drawAngleLabel = (idx1, idx2, idx3, value, label) => {
              const p1 = landmarks[idx1]
              const vertex = landmarks[idx2]
              const p3 = landmarks[idx3]
              if (!p1 || !vertex || !p3) return
              const text = label || `${value != null ? value.toFixed(1) : '--'}°`
              drawLabel(ctx, text, vertex.x + 8, vertex.y - 8, '#10B981')
            }

            if (res.Silla != null) drawAngleLabel(4, 10, 11, res.Silla, `Silla: ${res.Silla.toFixed(1)}°`)
            if (res.Articular != null) drawAngleLabel(10, 11, 14, res.Articular, `Art: ${res.Articular.toFixed(1)}°`)
            if (res.Goniaco != null) drawAngleLabel(11, 14, 3, res.Goniaco, `Gon: ${res.Goniaco.toFixed(1)}°`)

            // Etiquetas lineales
            if (res.Base_Craneal_Ant != null) drawLabel(ctx, `N-S: ${res.Base_Craneal_Ant.toFixed(1)}mm`, (landmarks[4]?.x + landmarks[10]?.x) / 2, (landmarks[4]?.y + landmarks[10]?.y) / 2, '#10B981', 0, 14)
            if (res.Cuerpo_Mandibular != null) drawLabel(ctx, `Go-Me: ${res.Cuerpo_Mandibular.toFixed(1)}mm`, (landmarks[14]?.x + landmarks[3]?.x) / 2, (landmarks[14]?.y + landmarks[3]?.y) / 2, '#10B981', 0, 14)
          }

          // Limpiar sombra
          ctx.shadowColor = 'transparent'
          ctx.shadowBlur = 0
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
            ctx.lineWidth = 1.5 / stretchRatio
            ctx.stroke()
          })
        }

        // Tooltip Dinamico
        if (hoverIdx !== null && tooltip.show) {
          const info = LANDMARKS[hoverIdx]
          if (info) {
            const fontSize = 14 / stretchRatio
            ctx.font = `${fontSize}px sans-serif`
            const text = `${info.id}: ${info.name}`
            const metrics = ctx.measureText(text)

            const paddingX = 12 / stretchRatio
            const boxHeight = 24 / stretchRatio
            const offsetX = 10 / stretchRatio
            const offsetY = 30 / stretchRatio

            ctx.fillStyle = 'rgba(0,0,0,0.8)'
            ctx.fillRect(tooltip.x + offsetX, tooltip.y - offsetY, metrics.width + paddingX, boxHeight)

            ctx.fillStyle = '#FFFFFF'
            ctx.textBaseline = 'middle'
            ctx.fillText(text, tooltip.x + offsetX + paddingX / 2, tooltip.y - offsetY + boxHeight / 2)
          }
        }
      }
      img.src = finalUrl
    }
  }, [imageId, imageUrl, landmarks, showPoints, showLines, showGrid, radius, selectedLandmark, hoverIdx, tooltip, imgSize, zoom, activeFilter, analysisResults])

  // Teclado
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

  // Mouse
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current
    if (!canvas || !imgSize.w) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = imgSize.w / rect.width
    const scaleY = imgSize.h / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY

    let found = null
    landmarks.forEach((lm, idx) => {
      if (!lm || lm.x == null) return
      const dist = Math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
      if (dist < radius + 8) found = idx
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
