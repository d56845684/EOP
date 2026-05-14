import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import type { ApiError, ApiResult, ApiActionResult, ApiBlobResult } from './types'

// ============================================================
// Error parsing
// ============================================================

function parseErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const msg = detail[0]?.msg || ''
    return msg.replace(/^Value error,\s*/, '')
  }
  return ''
}

function toApiError(status: number, body: Record<string, unknown>, fallback: string): ApiError {
  const rawCode = body.error_code
  const code = typeof rawCode === 'number' ? rawCode : 0  // 0 = unknown
  return {
    message: parseErrorDetail(body.detail) || (body.message as string) || fallback,
    code,
    status,
  }
}

const NETWORK_ERROR: ApiError = { message: '網路錯誤，請稍後再試', code: 0, status: 0 }

// ============================================================
// Core helpers
// ============================================================

/**
 * GET 請求，回傳 { data, error }
 * data 預設取 response body 的 .data 欄位；若 extractData=false 則回傳整個 body
 */
export async function apiGet<T>(
  path: string,
  fallback = '操作失敗',
  { extractData = true }: { extractData?: boolean } = {},
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`)
    const body = await res.json()
    if (!res.ok) return { data: null, error: toApiError(res.status, body, fallback) }
    return { data: (extractData ? body.data : body) as T, error: null }
  } catch {
    return { data: null, error: NETWORK_ERROR }
  }
}

/** POST 請求，回傳 { data, error } */
export async function apiPost<T>(
  path: string,
  payload?: unknown,
  fallback = '操作失敗',
  { extractData = true }: { extractData?: boolean } = {},
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload !== undefined ? JSON.stringify(payload) : undefined,
    })
    const body = await res.json()
    if (!res.ok) return { data: null, error: toApiError(res.status, body, fallback) }
    return { data: (extractData ? body.data : body) as T, error: null }
  } catch {
    return { data: null, error: NETWORK_ERROR }
  }
}

/** PUT 請求，回傳 { data, error } */
export async function apiPut<T>(
  path: string,
  payload?: unknown,
  fallback = '操作失敗',
  { extractData = true }: { extractData?: boolean } = {},
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: payload !== undefined ? JSON.stringify(payload) : undefined,
    })
    const body = await res.json()
    if (!res.ok) return { data: null, error: toApiError(res.status, body, fallback) }
    return { data: (extractData ? body.data : body) as T, error: null }
  } catch {
    return { data: null, error: NETWORK_ERROR }
  }
}

/** DELETE 請求，回傳 { success, error } */
export async function apiDelete(
  path: string,
  fallback = '刪除失敗',
  payload?: unknown,
): Promise<ApiActionResult> {
  try {
    const options: RequestInit = { method: 'DELETE' }
    if (payload !== undefined) {
      options.headers = { 'Content-Type': 'application/json' }
      options.body = JSON.stringify(payload)
    }
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`, options)
    const body = await res.json()
    if (!res.ok) return { success: false, message: '', error: toApiError(res.status, body, fallback) }
    return { success: true, message: (body.message as string) || '操作成功', error: null }
  } catch {
    return { success: false, message: '', error: NETWORK_ERROR }
  }
}

/** POST/PUT 只關心成功與否，不需要 data（例如 confirm upload） */
export async function apiAction(
  method: 'POST' | 'PUT' | 'DELETE',
  path: string,
  payload?: unknown,
  fallback = '操作失敗',
): Promise<ApiActionResult> {
  try {
    const options: RequestInit = { method }
    if (payload !== undefined) {
      options.headers = { 'Content-Type': 'application/json' }
      options.body = JSON.stringify(payload)
    }
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`, options)
    const body = await res.json()
    if (!res.ok) return { success: false, message: '', error: toApiError(res.status, body, fallback) }
    return { success: true, message: (body.message as string) || '操作成功', error: null }
  } catch {
    return { success: false, message: '', error: NETWORK_ERROR }
  }
}

/** Blob 下載（PDF / DOCX 等） */
export async function apiBlob(
  method: 'GET' | 'POST',
  path: string,
  payload?: unknown,
  fallback = '下載失敗',
): Promise<ApiBlobResult> {
  try {
    const options: RequestInit = { method }
    if (payload !== undefined) {
      options.headers = { 'Content-Type': 'application/json' }
      options.body = JSON.stringify(payload)
    }
    const res = await fetchWithAuth(`${API_BASE_URL}${path}`, options)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      return { blob: null, error: toApiError(res.status, body, fallback) }
    }
    const blob = await res.blob()
    return { blob, error: null }
  } catch {
    return { blob: null, error: NETWORK_ERROR }
  }
}

/** 建立 query string，自動忽略 undefined/null 值 */
export function qs(params: Record<string, unknown>): string {
  const entries = Object.entries(params).filter(([, v]) => v != null && v !== '')
  if (!entries.length) return ''
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}
