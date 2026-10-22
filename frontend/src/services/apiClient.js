import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor — normalise errors
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Unknown error'
    return Promise.reject(new Error(message))
  },
)

export default apiClient
