// src/services/api.ts
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'

// ── Config from Vite env (injected at build time, never hardcoded) ──
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''

// ── Retry config ───────────────────────────────────────────────
const MAX_RETRIES = 3
const RETRY_DELAY_MS = 800

function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms))
}

// ── Axios instance ──────────────────────────────────────────────
const api: AxiosInstance = axios.create({
    baseURL: BASE_URL,
    timeout: 120_000,   // 2 min — HF Inference can be slow on cold start
    headers: {
        'Content-Type': 'application/json',
    },
})

// ── Request interceptor: attach API key ─────────────────────────
api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        if (API_KEY) {
            config.headers['X-API-Key'] = API_KEY
        }
        return config
    },
    (error) => Promise.reject(error)
)

// ── Response interceptor: error normalization + retries ──────────
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const config = error.config as InternalAxiosRequestConfig & { _retryCount?: number }

        if (!config) return Promise.reject(error)

        // Initialize retry counter
        config._retryCount = config._retryCount ?? 0

        const status = error.response?.status

        // ── Auth errors: don't retry ──────────────────────────────
        if (status === 401) {
            toast.error('Invalid API key. Check your settings.')
            return Promise.reject(error)
        }

        // ── Rate limit: wait and retry ────────────────────────────
        if (status === 429) {
            const retryAfter = parseInt(error.response?.headers['retry-after'] ?? '5', 10)
            toast.error(`Rate limit hit. Retrying in ${retryAfter}s…`)
            await sleep(retryAfter * 1000)
        }

        // ── Retry on 5xx and network errors ───────────────────────
        const shouldRetry = !status || status >= 500 || status === 429
        if (shouldRetry && config._retryCount < MAX_RETRIES) {
            config._retryCount += 1
            const delay = RETRY_DELAY_MS * Math.pow(2, config._retryCount - 1)  // exponential backoff
            await sleep(delay)
            return api(config)
        }

        // ── Final error ────────────────────────────────────────────
        const detail = (error.response?.data as { detail?: string })?.detail
        const message = detail || error.message || 'An unexpected error occurred.'

        if (status === 500) {
            toast.error('Server error. Please try again.')
        } else if (!error.response) {
            toast.error('Cannot reach Nexxi backend. Is it running?')
        }

        return Promise.reject(new Error(message))
    }
)

export default api
export { BASE_URL }
