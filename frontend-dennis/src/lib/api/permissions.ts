import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface PageInfo {
  id: string
  key: string
  name: string
  description?: string
  parent_key?: string
  sort_order: number
  is_active: boolean
}

export interface MyPermissionsResponse {
  success: boolean
  role: string
  page_keys: string[]
  pages: PageInfo[]
}

export const permissionsApi = {
  async getMyPermissions(): Promise<{ data: MyPermissionsResponse | null; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/permissions/me`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得權限失敗' } }
      }
      const data = await response.json()
      return { data, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得權限失敗' } }
    }
  },
}
