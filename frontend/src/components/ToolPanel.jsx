import { useState } from 'react'
import LANDMARKS from '../constants/landmarks'
import { CRANIAL_LANDMARKS, MANDIBULAR_LANDMARKS, DENTAL_LANDMARKS, SOFT_TISSUE_LANDMARKS } from '../constants/landmarks'

function ToolPanel({
  showPoints, setShowPoints,
  showLines, setShowLines,
  showGrid, setShowGrid,
  showLabels, setShowLabels,
  pointRadius, setPointRadius,
  imageWidth,
  selectedLandmark,
  landmarks,
  calibrationMmPp,
  onMoveLandmark,
  onRecalculate,
  analysisResults,
  zoom, setZoom, onReset,
  activeFilters, setActiveFilters,
  labelFontSize, setLabelFontSize,
  loading = false,
  hiddenPoints = [],
  setHiddenPoints,
  confidences,
}) {
  const BASE_IMAGE_WIDTH = 1000;
  const [showLegend, setShowLegend] = useState(false)

  const dynamicRadius = pointRadius ?? 4

  const handleRadiusChange = (delta) => {
    setPointRadius(prev => Math.max(2, Math.min(20, prev + delta)))
  }

  const getLandmarkInfo = (idx) => LANDMARKS.find(l => l.id === idx)

  const stepPx = calibrationMmPp ? 0.1 / calibrationMmPp : 1

  // Manejar cambio en checkboxes de trazados
  const handleFilterChange = (filterName) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterName]: !prev[filterName]
    }))
  }

  return (
    <div className="space-y-4">
      {/* Controles de visualización */}
      <div className="bg-gray-50 p-3 rounded-lg">
        <h4 className="font-bold text-sm mb-2">Visualización</h4>
        <label className="flex items-center space-x-2 text-sm mb-1">
          <input type="checkbox" checked={showPoints} onChange={e => setShowPoints(e.target.checked)} />
          <span>Mostrar Puntos</span>
        </label>
        <label className="flex items-center space-x-2 text-sm mb-1">
          <input type="checkbox" checked={showLines} onChange={e => setShowLines(e.target.checked)} />
          <span>Mostrar Líneas</span>
        </label>
        <label className="flex items-center space-x-2 text-sm mb-1">
          <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} />
          <span>Mostrar Grilla</span>
        </label>
        <label className="flex items-center space-x-2 text-sm">
          <input type="checkbox" checked={showLabels} onChange={e => setShowLabels(e.target.checked)} />
          <span>Mostrar Nombres/Valores</span>
        </label>

        {/* Checkboxes para múltiples trazados */}
        <div className="mt-3">
          <label className="text-xs font-semibold text-gray-600 block mb-1">Trazados a visualizar:</label>
          <label className="flex items-center space-x-2 text-sm mb-1">
            <input
              type="checkbox"
              checked={activeFilters.steiner}
              onChange={() => handleFilterChange('steiner')}
            />
            <span>Análisis de Steiner</span>
          </label>
          <label className="flex items-center space-x-2 text-sm mb-1">
            <input
              type="checkbox"
              checked={activeFilters.wits}
              onChange={() => handleFilterChange('wits')}
            />
            <span>Análisis de Wits</span>
          </label>
          <label className="flex items-center space-x-2 text-sm mb-1">
            <input
              type="checkbox"
              checked={activeFilters.ricketts}
              onChange={() => handleFilterChange('ricketts')}
            />
            <span>Perfil Ricketts</span>
          </label>
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={activeFilters.jarabak}
              onChange={() => handleFilterChange('jarabak')}
            />
            <span>Polígono de Jarabak</span>
          </label>
        </div>
      </div>

      {/* Tamaño de puntos */}
      <div className="bg-gray-50 p-3 rounded-lg">
        <h4 className="font-bold text-sm mb-2">Tamaño de Puntos</h4>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleRadiusChange(-1)}
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 font-bold"
          >-</button>
          <span className="text-sm font-mono w-12 text-center min-w-[3rem]">{(pointRadius ?? dynamicRadius).toFixed(1)}</span>
          <button
            onClick={() => handleRadiusChange(1)}
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 font-bold"
          >+</button>
          <span className="text-xs text-gray-500 ml-2">(Auto: 4)</span>
        </div>
      </div>

      {/* Tamaño de Etiquetas */}
      <div className="bg-gray-50 p-3 rounded-lg">
        <h4 className="font-bold text-sm mb-2">Tamaño de Etiquetas</h4>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setLabelFontSize(f => Math.max(8, f - 1))}
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 font-bold"
          >-</button>
          <span className="text-sm font-mono w-12 text-center">{labelFontSize}px</span>
          <button
            onClick={() => setLabelFontSize(f => Math.min(32, f + 1))}
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 font-bold"
          >+</button>
        </div>
        <input
          type="range"
          min="8"
          max="32"
          value={labelFontSize}
          onChange={e => setLabelFontSize(parseInt(e.target.value))}
          className="w-full mt-2"
        />
      </div>

      {/* Edición de punto seleccionado */}
      {selectedLandmark !== null && (
        <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg">
          <h4 className="font-bold text-sm mb-2">Editando Punto</h4>
          {(() => {
            const info = getLandmarkInfo(selectedLandmark)
            const lm = landmarks[selectedLandmark]
            if (!lm || !info) return null
            return (
              <div className="text-sm space-y-1">
                <p><span className="font-medium">#{info.id}:</span> {info.name}</p>
                <p>X: <span className="font-mono">{lm.x?.toFixed(2) || 0}</span> px</p>
                <p>Y: <span className="font-mono">{lm.y?.toFixed(2) || 0}</span> px</p>
                {calibrationMmPp && (
                  <p className="text-xs text-gray-600">
                    (~{(lm.x * calibrationMmPp).toFixed(2)}mm, {(lm.y * calibrationMmPp).toFixed(2)}mm)
                  </p>
                )}
                <div className="grid grid-cols-3 gap-1 mt-2">
                  <button onClick={() => onMoveLandmark(selectedLandmark, -stepPx, 0)} className="bg-gray-200 py-1 rounded text-xs hover:bg-gray-300">←</button>
                  <button onClick={() => onMoveLandmark(selectedLandmark, 0, -stepPx)} className="bg-gray-200 py-1 rounded text-xs hover:bg-gray-300">↑</button>
                  <button onClick={() => onMoveLandmark(selectedLandmark, stepPx, 0)} className="bg-gray-200 py-1 rounded text-xs hover:bg-gray-300">→</button>
                  <div></div>
                  <button onClick={() => onMoveLandmark(selectedLandmark, 0, stepPx)} className="bg-gray-200 py-1 rounded text-xs hover:bg-gray-300">↓</button>
                  <div></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">Paso: {stepPx.toFixed(4)} px (0.1mm)</p>
                <button
                  onClick={() => { if (onMoveLandmark) onMoveLandmark(null, 0, 0, false) }}
                  className="w-full mt-2 text-xs bg-gray-200 py-1 rounded hover:bg-gray-300"
                >
                  Deseleccionar
                </button>
              </div>
            )
          })()}
        </div>
      )}

      {/* Controles de Zoom */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Zoom de Imagen</h4>
        <div className="flex items-center space-x-3">
          <button onClick={() => setZoom(z => Math.max(50, z - 25))} className="w-8 h-8 rounded bg-gray-200 hover:bg-gray-300 flex items-center justify-center font-bold">-</button>
          <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
          <button onClick={() => setZoom(z => Math.min(300, z + 25))} className="w-8 h-8 rounded bg-gray-200 hover:bg-gray-300 flex items-center justify-center font-bold">+</button>
          <button onClick={() => setZoom(100)} className="text-xs text-blue-600 hover:underline ml-2">Auto</button>
        </div>
      </div>

      {/* Botón Reset */}
      <button onClick={onReset} className="w-full bg-red-100 text-red-700 py-2 rounded-lg hover:bg-red-200 mb-3 text-sm font-semibold transition-colors border border-red-300">
        ↺ Restablecer IA Original
      </button>

      {/* Botón de recálculo */}
      <button
        onClick={onRecalculate}
        className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 font-medium"
      >
        Recálcular Análisis
      </button>

      {/* Botón Leyenda */}
      <button
        onClick={() => setShowLegend(!showLegend)}
        className="w-full bg-gray-600 text-white py-2 rounded-lg hover:bg-gray-700 text-sm"
      >
        {showLegend ? 'Ocultar Leyenda' : 'Leyenda'}
      </button>

      {/* Panel de Leyenda */}
      {showLegend && (
        <div className="bg-white border border-gray-300 rounded-lg p-3 max-h-64 overflow-y-auto">
          <h4 className="font-bold text-sm mb-2">Diccionario de Landmarks</h4>
          {[
            { title: 'Craneales (Rojos)', items: CRANIAL_LANDMARKS },
            { title: 'Mandibulares (Azules)', items: MANDIBULAR_LANDMARKS },
            { title: 'Dentales (Verdes)', items: DENTAL_LANDMARKS },
            { title: 'Tejidos Blandos (Amarillos)', items: SOFT_TISSUE_LANDMARKS },
          ].map(section => (
            <div key={section.title} className="mb-2">
              <p className="text-xs font-bold text-gray-700">{section.title}</p>
              {section.items.map(l => {
                const isHidden = hiddenPoints.includes(l.id)
                const conf = confidences?.[l.id]
                const confPct = conf != null ? Math.round(conf * 100) : null
                return (
                  <div key={l.id} className="flex items-center text-xs text-gray-600 ml-2 py-0.5">
                    <button
                      onClick={() => isHidden
                        ? setHiddenPoints(h => h.filter(x => x !== l.id))
                        : setHiddenPoints(h => [...h, l.id])
                      }
                      className="mr-1.5 text-sm leading-none hover:scale-125 transition-transform"
                      title={isHidden ? 'Mostrar punto' : 'Ocultar punto'}
                    >
                      {isHidden ? '👁‍🗨' : '👁'}
                    </button>
                    <span className="flex-1">[{l.id}]: {l.name}</span>
                    {confPct != null && (
                      <span className={`ml-1 px-1 rounded text-[10px] font-mono ${confPct >= 80 ? 'bg-green-100 text-green-700' : confPct >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                        {confPct}%
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ToolPanel
