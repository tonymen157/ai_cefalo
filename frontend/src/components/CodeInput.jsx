import { useState } from 'react'

function CodeInput({ value, onChange, error }) {
  const [localValue, setLocalValue] = useState(value || '')

  const handleChange = (e) => {
    const val = e.target.value.toUpperCase()
    setLocalValue(val)
    if (onChange) onChange(val)
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Código de Crédito
      </label>
      <input
        type="text"
        value={localValue}
        onChange={handleChange}
        placeholder="Ingresa tu código"
        className="w-full border border-gray-300 p-3 rounded-lg focus:border-blue-500 focus:outline-none"
      />
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  )
}

export default CodeInput
