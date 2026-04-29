import { getAngleColor, getSkeletalClassification } from '../constants/steinerRanges'

function SteinerTable({ results }) {
  if (!results) return null

  // Mapear formato correcto del backend:
  // results.angulos = { SNA: 82.12, SNB: 80.45, ANB: 1.67 } (números planos)
  // results.evaluacion = { SNA: {estado:"OK",lim_inf:80,lim_sup:84}, ... }
  const angulosFormat = [
    { nombre: 'SNA', valor: results.angulos?.SNA, estado: results.evaluacion?.SNA?.estado, lim_inf: results.evaluacion?.SNA?.lim_inf, lim_sup: results.evaluacion?.SNA?.lim_sup },
    { nombre: 'SNB', valor: results.angulos?.SNB, estado: results.evaluacion?.SNB?.estado, lim_inf: results.evaluacion?.SNB?.lim_inf, lim_sup: results.evaluacion?.SNB?.lim_sup },
    { nombre: 'ANB', valor: results.angulos?.ANB, estado: results.evaluacion?.ANB?.estado, lim_inf: results.evaluacion?.ANB?.lim_inf, lim_sup: results.evaluacion?.ANB?.lim_sup },
  ]

  const classification = results.clase_esqueletica

  const getEstadoTexto = (item) => {
    if (item.estado === 'OK') return '✓ Normal'
    // Lógica direccional clínico-ortodóntica
    if (item.nombre === 'SNA') {
      // SNA > 84 = maxilar protrusivo (↑ Aumentado)
      // SNA < 80 = maxilar retrusivo (↓ Disminuido)
      if (item.valor > item.lim_sup) return '↑ Aumentado'
      if (item.valor < item.lim_inf) return '↓ Disminuido'
    }
    if (item.nombre === 'SNB') {
      // SNB > 82 = mandibular protrusiva (↑ Aumentado)
      // SNB < 78 = mandibular retrusiva (↓ Disminuido)
      if (item.valor > item.lim_sup) return '↑ Aumentado'
      if (item.valor < item.lim_inf) return '↓ Disminuido'
    }
    if (item.nombre === 'ANB') {
      // ANB > 4 = Clase II (↑ Aumentado)
      // ANB < 0 = Clase III (↓ Disminuido)
      // 0.0 <= ANB <= 1.0: Límite inferior (tendencia a Clase III)
      if (item.valor > item.lim_sup) return '↑ Aumentado'
      if (item.valor < item.lim_inf) return '↓ Disminuido'
      if (item.valor >= 0.0 && item.valor <= 1.0) return '↓ Límite inf. (Tendencia a Clase III)'
    }
    return '⚠️ Alterado'
  }

  const getColorClase = (item) => {
    if (item.estado === 'OK') return 'bg-green-100 text-green-800'
    if (item.estado === 'FUERA') return 'bg-orange-100 text-orange-800'
    return 'bg-yellow-100 text-yellow-800'
  }

  const classificationColor = () => {
    if (!classification) return 'bg-gray-100'
    if (classification.includes('Clase I')) return 'bg-green-100 text-green-800'
    if (classification.includes('Clase II')) return 'bg-red-100 text-red-800'
    if (classification.includes('Clase III')) return 'bg-yellow-100 text-yellow-800'
    return 'bg-gray-100'
  }

  return (
    <div className="mb-6">
      <h3 className="text-lg font-bold mb-3">Análisis de Steiner</h3>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2 text-left">Ángulo</th>
            <th className="border p-2 text-left">Valor</th>
            <th className="border p-2 text-left">Estado</th>
          </tr>
        </thead>
        <tbody>
          {angulosFormat.map((a) => (
            <tr key={a.nombre}>
              <td className="border p-2 font-medium">{a.nombre}</td>
              <td className={`border p-2 font-bold ${a.valor !== undefined ? getColorClase(a) : ''}`}>
                {a.valor !== undefined ? `${a.valor.toFixed(2)}°` : 'N/A'}
              </td>
              <td className={`border p-2 ${getColorClase(a)}`}>
                {getEstadoTexto(a)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {classification && (
        <div className={`mt-4 p-3 rounded-lg ${classificationColor()}`}>
          <strong>Clasificación esquelética:</strong> {classification}
        </div>
      )}
    </div>
  )
}

export default SteinerTable
