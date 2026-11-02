import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

import type { ApiError } from './types'

export const TOKEN_KEY = 'demo_token'
export const USER_KEY = 'demo_user'

const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

instance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status: number = error.response?.status ?? 0
    const body = error.response?.data as
      | { code?: string; message?: string; detail?: unknown }
      | undefined

    const apiError: ApiError = {
      code: body?.code ?? 'NETWORK_ERROR',
      message:
        body?.message ??
        (status > 0 ? `请求失败（${status}）` : '网络异常，请确认后端服务已启动'),
      detail: body?.detail ?? null,
      status,
    }

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      const current = window.location.pathname + window.location.search
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = `/login?redirect=${encodeURIComponent(current)}`
      }
    }

    if (apiError.code === 'OUT_OF_STOCK') {
      const stock = (apiError.detail as { stock?: number } | null)?.stock
      if (stock !== undefined) {
        apiError.message = `${apiError.message}（剩余库存 ${stock}）`
      }
    }

    ElMessage.error(apiError.message)
    return Promise.reject(apiError)
  },
)

// 响应拦截器已把 AxiosResponse 解包成 data，这里补回类型。
export function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.get(url, config) as unknown as Promise<T>
}

export function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return instance.post(url, data, config) as unknown as Promise<T>
}

export function patch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return instance.patch(url, data, config) as unknown as Promise<T>
}

export function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete(url, config) as unknown as Promise<T>
}
