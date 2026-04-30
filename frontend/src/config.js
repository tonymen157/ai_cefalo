// Centralized API configuration
// No hardcode URLs - use environment variable with sensible development default

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

export const BASE_URL = API_BASE_URL.replace(/\/api$/, '')
