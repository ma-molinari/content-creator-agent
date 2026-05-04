import axios, { type InternalAxiosRequestConfig } from 'axios'

import { useAuthStore } from '@/stores/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

export const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

/** No interceptors — only for initial session bootstrap (POST /auth/refresh). Avoids 401 → full-page redirect on public routes. */
export const apiSession = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 → refresh → retry once → clear + redirect
let isRefreshing = false
let pendingQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

function drainQueue(error: unknown, token?: string) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  pendingQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const config = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status !== 401 || config._retry) {
      return Promise.reject(error)
    }

    // Refresh itself failed — bail out
    if ((config.url ?? '').includes('/auth/refresh')) {
      useAuthStore.getState().clear()
      window.location.replace('/login')
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({
          resolve: (token) => {
            config.headers.Authorization = `Bearer ${token}`
            resolve(api(config))
          },
          reject,
        })
      })
    }

    config._retry = true
    isRefreshing = true

    try {
      const { data } = await apiSession.post<{ accessToken: string }>('/auth/refresh')
      const token = data.accessToken
      useAuthStore.getState().setAccessToken(token)
      drainQueue(null, token)
      config.headers.Authorization = `Bearer ${token}`
      return api(config)
    } catch (refreshErr) {
      drainQueue(refreshErr)
      useAuthStore.getState().clear()
      window.location.replace('/login')
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  },
)
