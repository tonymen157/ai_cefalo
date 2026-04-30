import { useEffect, useRef, useState, useCallback } from 'react'
import LANDMARKS from '../constants/landmarks'

function LandmarkCanvas({
  imageId,
  imageUrl,
  landmarks = [],
  showPoints = true,
  showLines = true,
  showGrid = false,
  showLabels = true,
  pointRadius = null,
  selectedLandmark,
  onSelectLandmark,
  calibrationMmPp,
  zoom = 100,
  activeFilter = 'steiner',
  analysisResults = null,
  labelFontSize = 13,
}) {
  const canvasRef = useRef(null)
  const imgRef = useRef(null)
  const [imgLoaded, setImgLoaded] = useState(false)
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

  // Cargar imagen una vez
  useEffect(() => {
    const finalUrl = getFinalUrl()
    if (!finalUrl) {
      setImgLoaded(false)
      setImgSize({ w: 0, h: 0 })
      imgRef.current = null
      return
    }
    setImgLoaded(false)
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      if (img.width > 0 && img.height > 0) {
        imgRef.current = img
        setImgSize({ w: img.width, h: img.height })
        setImgLoaded(true)
      }
    }
    img.onerror = () => {
      console.error("Error cargando imagen:", finalUrl)
      setImgLoaded(false)
      imgRef.current = null
    }
    img.src = finalUrl
    return () => { img.onload = null; img.onerror = null }
  }, [imageId, imageUrl])

  // Dibujar
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !imgLoaded || !imgRef.current) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = imgSize.w * dpr
    canvas.height = imgSize.h * dpr

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    try {
      ctx.save()
      ctx.scale(dpr, dpr)

      // Dibujar imagen desde cache
      ctx.drawImage(imgRef.current, 0, 0, imgSize.w, imgSize.h)

      const valid = (p) => p && p.x != null && !isNaN(p.x) && !isNaN(p.y)

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

      // Líneas
      if (showLines && landmarks.length >= 29) {
        ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
        ctx.shadowBlur = 3
        const lineWidth = 2.5

        const drawLine = (idx1, idx2, color) => {
          const p1 = landmarks[idx1]
          const p2 = landmarks[idx2]
          if (!valid(p1) || !valid(p2)) return
          ctx.beginPath()
          ctx.strokeStyle = color
          ctx.lineWidth = lineWidth
          ctx.moveTo(p1.x, p1.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()
        }

        const drawLabel = (text, x, y, color, offsetX = 6, offsetY = -6) => {
          if (!text && text !== 0) return
          if (!showLabels) return
          ctx.save()
          ctx.font = `bold ${labelFontSize}px sans-serif`
          ctx.textBaseline = 'top'
          const metrics = ctx.measureText(text)
          const pad = 4
          const lx = x + offsetX
          const ly = y + offsetY
          ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
          ctx.fillRect(lx - pad, ly - pad, metrics.width + pad * 2, 16 + pad * 2)
          ctx.fillStyle = color
          ctx.fillText(text, lx, ly)
          ctx.restore()
        }

        const res = analysisResults || {}

        // --- STEINER ---
        if (activeFilter === 'steiner') {
          drawLine(10, 4, '#EF4444')   // S-N
          drawLine(4, 0, '#3B82F6')    // N-A
          drawLine(4, 2, '#22C55E')    // N-B
          drawLine(14, 13, '#F59E0B')  // Go-Gn

          const nPt = landmarks[4], sPt = landmarks[10]
          const aPt = landmarks[0], bPt = landmarks[2]

          if (valid(nPt) && valid(sPt)) {
            drawLabel(`${res.SNA?.toFixed(1) ?? '--'}°`, (nPt.x + sPt.x) / 2, (nPt.y + sPt.y) / 2, '#EF4444')
          }
          if (valid(nPt) && valid(sPt)) {
            drawLabel(`${res.SNB?.toFixed(1) ?? '--'}°`, (nPt.x + sPt.x) / 2, (nPt.y + sPt.y) / 2 + 16, '#3B82F6')
          }
          if (valid(aPt) && valid(bPt) && valid(nPt)) {
            const anbText = res.ANB != null ? `ANB: ${res.ANB.toFixed(1)}°` : 'ANB: --°'
            drawLabel(anbText, (aPt.x + bPt.x) / 2, nPt.y - 20, '#8B5CF6')
          }
          if (res.WITS != null && valid(aPt)) {
            const witsText = `Wits: ${res.WITS >= 0 ? '+' : ''}${res.WITS.toFixed(1)}mm`
            drawLabel(witsText, aPt.x + 10, aPt.y + 30, '#06B6D4')
          }
        }

        // --- WITS ---
        if (activeFilter === 'wits') {
          const m1 = landmarks[18], m2 = landmarks[19]
          const i1 = landmarks[21], i2 = landmarks[17]
          if (valid(m1) && valid(m2) && valid(i1) && valid(i2)) {
            const molarMid = { x: (m1.x + m2.x) / 2, y: (m1.y + m2.y) / 2 }
            const incisorMid = { x: (i1.x + i2.x) / 2, y: (i1.y + i2.y) / 2 }

            ctx.beginPath()
            ctx.strokeStyle = '#EC4899'
            ctx.lineWidth = lineWidth
            ctx.moveTo(molarMid.x, molarMid.y)
            ctx.lineTo(incisorMid.x, incisorMid.y)
            ctx.stroke()
            drawLabel('Plano Oclusal', (molarMid.x + incisorMid.x) / 2, molarMid.y - 12, '#EC4899')

            const drawPerp = (ptIdx, label) => {
              const pt = landmarks[ptIdx]
              if (!valid(pt)) return
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
              drawLabel(label, (pt.x + projX) / 2, (pt.y + projY) / 2, '#06B6D4', 8, -8)
            }

            if (res.WITS != null) {
              drawPerp(0, `A: ${res.WITS.toFixed(1)}mm`)
              drawPerp(2, `B: ${res.WITS.toFixed(1)}mm`)
            } else {
              drawPerp(0, 'A')
              drawPerp(2, 'B')
            }
          }
        }

        // --- RICKETTS ---
        if (activeFilter === 'ricketts') {
          drawLine(28, 27, '#8B5CF6') // Sn -> Pog'
          drawLabel('Linea E', (landmarks[28]?.x + landmarks[27]?.x) / 2 || 0, ((landmarks[28]?.y + landmarks[27]?.y) / 2 || 0) - 12, '#8B5CF6')

          const lsPt = landmarks[25]
          const liPt = landmarks[24]
          if (res.Ls_E != null && valid(lsPt)) {
            drawLabel(`Ls: ${res.Ls_E >= 0 ? '+' : ''}${res.Ls_E.toFixed(1)}mm`, lsPt.x + 10, lsPt.y, '#8B5CF6')
          }
          if (res.Li_E != null && valid(liPt)) {
            drawLabel(`Li: ${res.Li_E >= 0 ? '+' : ''}${res.Li_E.toFixed(1)}mm`, liPt.x + 10, liPt.y, '#8B5CF6')
          }
        }

        // --- JARABAK ---
        if (activeFilter === 'jarabak') {
          const pts = [4, 10, 11, 14, 3, 4]
          ctx.beginPath()
          ctx.strokeStyle = '#10B981'
          ctx.lineWidth = lineWidth
          pts.forEach((idx, i) => {
            const p = landmarks[idx]
            if (!valid(p)) return
            if (i === 0) ctx.moveTo(p.x, p.y)
            else ctx.lineTo(p.x, p.y)
          })
          ctx.stroke()

          const drawAngle = (vIdx, txt) => {
            const v = landmarks[vIdx]
            if (!valid(v)) return
            drawLabel(txt, v.x + 8, v.y - 8, '#10B981')
          }
          if (res.Silla != null) drawAngle(10, `Silla: ${res.Silla.toFixed(1)}°`)
          if (res.Articular != null) drawAngle(11, `Art: ${res.Articular.toFixed(1)}°`)
          if (res.Goniaco != null) drawAngle(14, `Gon: ${res.Goniaco.toFixed(1)}°`)
          if (res.Base_Craneal_Ant != null && valid(landmarks[4]) && valid(landmarks[10])) {
            drawLabel(`N-S: ${res.Base_Craneal_Ant.toFixed(1)}mm`, (landmarks[4].x + landmarks[10].x) / 2, (landmarks[4].y + landmarks[10].y) / 2, '#10B981', 0, 14)
          }
          if (res.Cuerpo_Mandibular != null && valid(landmarks[14]) && valid(landmarks[3])) {
            drawLabel(`Go-Me: ${res.Cuerpo_Mandibular.toFixed(1)}mm`, (landmarks[14].x + landmarks[3].x) / 2, (landmarks[14].y + landmarks[3].y) / 2, '#10B981', 0, 14)
          }
        }

        ctx.shadowColor = 'transparent'
        ctx.shadowBlur = 0
      }

      // Puntos
      if (showPoints) {
        const rect = canvas.getBoundingClientRect()
        const stretchRatio = rect.width ? (rect.width / imgSize.w) : 1
        const dynRadius = radius ?? (4 / stretchRatio)
        landmarks.forEach((lm, idx) => {
          if (!lm || lm.x == null || isNaN(lm.x) || isNaN(lm.y)) return
          const info = LANDMARKS[idx]
          if (!info) return
          ctx.beginPath()
          ctx.arc(lm.x, lm.y, idx === selectedLandmark ? dynRadius * 1.5 : dynRadius, 0, Math.PI * 2)
          ctx.fillStyle = idx === selectedLandmark ? '#FFD700' : info.color
          ctx.fill()
          ctx.strokeStyle = '#FFFFFF'
          ctx.lineWidth = 1.5 / stretchRatio
          ctx.stroke()
        })
      }

      // Tooltip
      if (hoverIdx !== null && tooltip.show) {
        const info = LANDMARKS[hoverIdx]
        if (info) {
          const rect = canvas.getBoundingClientRect()
          const stretchRatio = rect.width ? (rect.width / imgSize.w) : 1
          const fontSize = 14 / stretchRatio
          ctx.font = `${fontSize}px sans-serif`
          const text = `${info.id}: ${info.name}`
          const metrics = ctx.measureText(text)
          const padX = 12 / stretchRatio
          const boxH = 24 / stretchRatio
          const offX = 10 / stretchRatio
          const offY = 30 / stretchRatio
          ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
          ctx.fillRect(tooltip.x + offX, tooltip.y - offY, metrics.width + padX, boxH)
          ctx.fillStyle = '#FFFFFF'
          ctx.textBaseline = 'middle'
          ctx.fillText(text, tooltip.x + offX + padX / 2, tooltip.y - offY + boxH / 2)
        }
      }

      ctx.restore()
    } catch (e) {
      console.error('Error dibujando canvas:', e)
    }
  }, [imgLoaded, imgSize, landmarks, showPoints, showLines, showGrid, radius, selectedLandmark, hoverIdx, tooltip, zoom, activeFilter, analysisResults, labelFontSize, showLabels])

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

  // Mouse move
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
      if (!lm || lm.x == null || isNaN(lm.x)) return
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

  // Click: toggle selección (clic en punto seleccionado = deseleccionar)
  const handleClick = () => {
    if (hoverIdx !== null) {
      if (hoverIdx === selectedLandmark) {
        // Toggle: deseleccionar
        if (onSelectLandmark) onSelectLandmark(null, 0, 0, false)
      } else {
        if (onSelectLandmark) onSelectLandmark(hoverIdx, 0, 0, false)
      }
    }
  }

  if (!imgLoaded) return null

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
