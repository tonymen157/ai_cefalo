import axios from 'axios'
import { API_BASE_URL } from '../config'

const api = axios.create({
  baseURL: API_BASE_URL,
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
    console.log('[useApi] Data type:', data instanceof FormData ? 'FormData' : typeof data)
    if (data instanceof FormData) {
      for (let pair of data.entries()) {
        console.log('[useApi] FormData:', pair[0], pair[1] instanceof File ? `File: ${pair[1].name} (${pair[1].size} bytes)` : pair[1])
      }
    }
    try {
      const response = await api.post(url, data)
      return response.data
    } catch (err) {
      console.error('[useApi] FULL ERROR:', {
        message: err.message,
        code: err.code,
        response: err.response ? {
          status: err.response.status,
          statusText: err.response.statusText,
          data: err.response.data,
          headers: err.response.headers
        } : null,
        request: err.request ? 'Request was made but no response' : null
      })
      throw err
    }
  }

  const get = async (url) => {
    const response = await api.get(url)
    return response.data
  }

  return { post, get, api }
}
