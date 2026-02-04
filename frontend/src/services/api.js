/**
 * API Client - Comunicação com backend
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Produtos
export const productApi = {
  scrape: (url, bypassCache = false) =>
    apiClient.post('/products/scrape', { url }, { params: { bypass_cache: bypassCache } }),

  scrapeBatch: (urls, bypassCache = false) =>
    apiClient.post('/products/batch', { urls }, { params: { bypass_cache: bypassCache } }),

  clearCache: (marketplace = 'all') =>
    apiClient.delete(`/cache/${marketplace}`),
}

// YouTube
export const youtubeApi = {
  analyze: (youtubeUrl, forceReanalysis = false) =>
    apiClient.post('/youtube/analyze', {
      youtube_url: youtubeUrl,
      force_reanalysis: forceReanalysis,
    }),

  getAnalysis: (videoId) =>
    apiClient.get(`/youtube/analysis/${videoId}`),
}

// Anúncios
export const adsApi = {
  create: (productUrl, youtubeUrl = null, style = 'charismatic_fomo') =>
    apiClient.post('/ads/create', {
      product_url: productUrl,
      youtube_url: youtubeUrl,
      style,
    }),

  getStatus: (jobId) =>
    apiClient.get(`/ads/status/${jobId}`),
}

// Health check
export const healthApi = {
  check: () => apiClient.get('/health'),
}

export default apiClient
