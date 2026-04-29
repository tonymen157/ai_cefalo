// Calibration utility functions

export function calculateMmPerPixel(x1, y1, x2, y2, realDistanceMm) {
  const dx = x2 - x1
  const dy = y2 - y1
  const pixelDistance = Math.sqrt(dx * dx + dy * dy)
  if (pixelDistance === 0) throw new Error('Los puntos deben ser diferentes')
  if (realDistanceMm <= 0) throw new Error('La distancia real debe ser positiva')
  return realDistanceMm / pixelDistance
}

export function convertToMm(pixels, mmPerPixel) {
  return pixels * mmPerPixel
}

export function convertToPixels(mm, mmPerPixel) {
  return mm / mmPerPixel
}
