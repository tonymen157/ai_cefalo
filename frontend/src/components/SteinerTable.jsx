import React, { useState } from 'react';
import { CEPHALOMETRIC_NORMS } from '../constants/analysisNorms';

function SteinerTable({ results }) {
  const [activeCategory, setActiveCategory] = useState('todas');

  const getInterpretation = (val, item, results) => {
    if (val == null || isNaN(val)) return { text: '-', color: 'text-gray-400' };

    // Prioridad: usar interpretacion del backend si existe (ej: Silla_interp, Cuerpo_Mandibular_interp)
    const interpKey = item.id + '_interp';
    if (results && results[interpKey] && results[interpKey] !== 'None') {
      const backendText = results[interpKey];
      // Determinar color basado en si sugiere Clase II o III
      if (backendText.includes('Clase III')) {
        return { text: backendText, color: 'text-orange-600 bg-orange-50' };
      } else if (backendText.includes('Clase II')) {
        return { text: backendText, color: 'text-red-600 bg-red-50' };
      }
      return { text: backendText, color: 'text-green-700 bg-green-50' };
    }

    // Lógica local de respaldo
    if (val > item.normal + item.sd) return { text: `↑ ${item.high}`, color: 'text-red-600 bg-red-50' };
    if (val < item.normal - item.sd) return { text: `↓ ${item.low}`, color: 'text-orange-600 bg-orange-50' };

    const textToDisplay = item.normalText ? `✓ ${item.normalText}` : '✓ Normal';
    return { text: textToDisplay, color: 'text-green-700 bg-green-50' };
  };

  // Buscador inteligente (Búsqueda Recursiva)
  const findDynamicValue = (apiData, targetId) => {
    if (!apiData || typeof apiData !== 'object') return null;
    const lowerTarget = targetId.toLowerCase();

    const search = (data) => {
      if (typeof data !== 'object' || data === null) return null;

      if (Array.isArray(data)) {
        for (let item of data) {
          const res = search(item);
          if (res !== null) return res;
        }
        return null;
      }

      for (const [key, value] of Object.entries(data)) {
        if (key.toLowerCase() === lowerTarget) return value;
        if (typeof value === 'object' && value !== null) {
          const res = search(value);
          if (res !== null) return res;
        }
      }
      return null;
    };

    return search(apiData);
  };

  // Determinar color de la clase esqueletal
  const getClaseColor = (clase) => {
    if (clase === 'Clase III') return 'bg-orange-100 text-orange-800 border-orange-300';
    if (clase === 'Clase II') return 'bg-red-100 text-red-800 border-red-300';
    return 'bg-green-100 text-green-800 border-green-300';
  };

  const claseEsqueletal = results?.clase_esqueletal;

  return (
    <div className="mt-6 space-y-4">
      {/* BANNER DE CLASE ESQUELETAL */}
      {claseEsqueletal && (
        <div className={`text-center py-2 px-4 rounded-lg border font-bold text-sm ${getClaseColor(claseEsqueletal)}`}>
          Diagnostico Esqueletal: {claseEsqueletal}
          {results?.ANB != null && ` (ANB: ${parseFloat(results.ANB).toFixed(1)}°, Wits: ${results.WITS != null ? parseFloat(results.WITS).toFixed(1) + 'mm' : 'N/A'})`}
        </div>
      )}

      {/* CABECERA CON EL MENU DESPLEGABLE */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-gray-200 pb-3 gap-3">
        <h3 className="text-lg font-bold text-gray-800">Resultados Clinicos</h3>
        <div className="flex items-center space-x-2">
          <label htmlFor="category-filter" className="text-sm font-semibold text-gray-600 whitespace-nowrap">
            Filtro:
          </label>
          <select
            id="category-filter"
            value={activeCategory}
            onChange={(e) => setActiveCategory(e.target.value)}
            className="bg-white border border-gray-300 text-gray-700 py-1.5 px-3 rounded-lg shadow-sm text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            <option value="todas">Mostrar Todo</option>
            <option value="esqueletal">Esqueletal (Steiner/Wits)</option>
            <option value="dental">Inclinacion Dental</option>
            <option value="estetico">Estetico (Ricketts)</option>
            <option value="jarabak_lineal">Lineales (Jarabak)</option>
            <option value="jarabak_angular">Angulares (Jarabak)</option>
          </select>
        </div>
      </div>

      {/* RENDERIZADO DINAMICO DE LAS TABLAS */}
      {Object.entries(CEPHALOMETRIC_NORMS)
        .filter(([key]) => activeCategory === 'todas' || activeCategory === key)
        .map(([key, category]) => (
          <div key={key} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="bg-blue-50/50 px-4 py-2.5 font-semibold text-sm text-blue-800 border-b border-gray-200">
              {category.title}
            </div>
            <table className="w-full table-fixed text-sm">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-2 py-4 w-[25%]">Medida</th>
                  <th className="text-center px-2 py-4 w-[20%]">Norma</th>
                  <th className="text-center px-2 py-4 w-[20%]">Paciente</th>
                  <th className="text-center px-2 py-4 w-[35%]">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {category.measurements.map((item) => {
                  const rawVal = findDynamicValue(results, item.id);
                  const patientVal = rawVal !== null && rawVal !== undefined && rawVal !== ''
                    ? parseFloat(rawVal)
                    : null;

                  const status = getInterpretation(patientVal, item, results);

                  return (
                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                      <td className="text-left px-2 py-4 font-medium text-gray-800">{item.id}</td>
                      <td className="text-center px-2 py-4 text-gray-500">{item.normal}{item.unit} (±{item.sd})</td>
                      <td className="text-center px-2 py-4 font-bold text-gray-900">
                        {patientVal !== null && !isNaN(patientVal) ? `${patientVal.toFixed(2)}${item.unit}` : '-'}
                      </td>
                      <td className={`text-center px-2 py-4 text-xs font-semibold ${status.color} whitespace-normal`}>
                        <span className="px-2 py-1 rounded-full">{status.text}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
    </div>
  );
}

export default SteinerTable;
