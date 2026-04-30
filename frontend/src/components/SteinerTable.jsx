import React, { useState } from 'react';
import { CEPHALOMETRIC_NORMS } from '../constants/analysisNorms';

function SteinerTable({ results }) {
  // Estado para el menú desplegable (por defecto muestra todo)
  const [activeCategory, setActiveCategory] = useState('todas');

  const getInterpretation = (val, item) => {
    if (val == null || isNaN(val)) return { text: '-', color: 'text-gray-400' };
    if (val > item.normal + item.sd) return { text: `↑ ${item.high}`, color: 'text-red-600 bg-red-50' };
    if (val < item.normal - item.sd) return { text: `↓ ${item.low}`, color: 'text-orange-600 bg-orange-50' };

    // Lógica dinámica para valores normales
    const textToDisplay = item.normalText ? `✓ ${item.normalText}` : '✓ Normal';
    return { text: textToDisplay, color: 'text-green-700 bg-green-50' };
  };

  // Buscador inteligente (Búsqueda Recursiva - reformulado para mayor seguridad)
  const findDynamicValue = (apiData, targetId) => {
    if (!apiData || typeof apiData !== 'object') return null;
    const lowerTarget = targetId.toLowerCase();

    const search = (data) => {
      if (typeof data !== 'object' || data === null) return null;

      // Si es un array, buscar en cada elemento
      if (Array.isArray(data)) {
        for (let item of data) {
          const res = search(item);
          if (res !== null) return res;
        }
        return null;
      }

      // Si es un objeto, revisar sus llaves (usando Object.entries para evitar propiedades de prototipo)
      for (const [key, value] of Object.entries(data)) {
        if (key.toLowerCase() === lowerTarget) return value;
        // Si la llave actual es otro objeto/array, entrar más profundo (recursividad)
        if (typeof value === 'object' && value !== null) {
          const res = search(value);
          if (res !== null) return res;
        }
      }
      return null;
    };

    return search(apiData);
  };

  return (
    <div className="mt-6 space-y-4">
      {/* CABECERA CON EL MENÚ DESPLEGABLE */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-gray-200 pb-3 gap-3">
        <h3 className="text-lg font-bold text-gray-800">Resultados Clínicos</h3>
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
            <option value="dental">Inclinación Dental</option>
            <option value="estetico">Estético (Ricketts)</option>
            <option value="jarabak_lineal">Lineales (Jarabak)</option>
            <option value="jarabak_angular">Angulares (Jarabak)</option>
          </select>
        </div>
      </div>

      {/* RENDERIZADO DINÁMICO DE LAS TABLAS */}
      {Object.entries(CEPHALOMETRIC_NORMS)
        // El filtro mágico: muestra si es 'todas' o si coincide con la categoría elegida
        .filter(([key]) => activeCategory === 'todas' || activeCategory === key)
        .map(([key, category]) => (
          <div key={key} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden transition-all duration-300">
            <div className="bg-blue-50/50 px-4 py-2.5 font-semibold text-sm text-blue-800 border-b border-gray-200">
              {category.title}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-gray-50 text-gray-500">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Medida</th>
                    <th className="px-4 py-2.5 font-medium">Norma</th>
                    <th className="px-4 py-2.5 font-medium">Paciente</th>
                    <th className="px-4 py-2.5 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {category.measurements.map((item) => {
                    // 1. Búsqueda Recursiva: Busca en toda la respuesta de Python
                    const rawVal = findDynamicValue(results, item.id);

                    // 2. Parseo de seguridad estricto
                    const patientVal = rawVal !== null && rawVal !== undefined && rawVal !== ''
                      ? parseFloat(rawVal)
                      : null;

                    const status = getInterpretation(patientVal, item);

                    return (
                      <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-2 font-medium text-gray-800">{item.id}</td>
                        <td className="px-4 py-2 text-gray-500">{item.normal}{item.unit} (±{item.sd})</td>
                        <td className="px-4 py-2 font-bold text-gray-900">
                          {patientVal !== null && !isNaN(patientVal) ? `${patientVal.toFixed(2)}${item.unit}` : '-'}
                        </td>
                        <td className={`px-4 py-2 text-xs font-semibold ${status.color}`}>
                          <span className="px-2 py-1 rounded-full">{status.text}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
    </div>
  );
}

export default SteinerTable;
