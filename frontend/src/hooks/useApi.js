import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
  timeout: 120000,
})

// Log requests
api.interceptors.request.use(
  (config) => {
    console.log('[API →]', config.method?.toUpperCase(), config.url, {
      baseURL: config.baseURL,
      data: config.data instanceof FormData ? 'FormData' : config.data
    })
    return config
  },
  (error) => {
    console.error('[API REQUEST ERROR]', error)
    return Promise.reject(error)
  }
)

// Log responses
api.interceptors.response.use(
  (response) => {
    console.log('[API ←]', response.status, response.statusText, response.config.url, response.data)
    return response
  },
  (error) => {
    console.error('[API ERROR]', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      url: error.config?.url
    })
    return Promise.reject(error)
  }
)

export function useApi() {
  const post = async (url, data) => {
    console.log('[useApi] BASE:', api.defaults.baseURL)
    console.log('[useApi] ENDPOINT:', url)
    console.log('[useApi] FULL URL:', api.defaults.baseURL + url)
    const response = await api.post(url, data)
    return response.data
  }

  const get = async (url) => {
    const response = await api.get(url)
    return response.data
  }

  return { post, get, api }
}
