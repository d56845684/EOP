import { apiGet } from './client'

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
  getMyPermissions: () =>
    apiGet<MyPermissionsResponse>('/api/v1/permissions/me', '取得權限失敗', { extractData: false }),
}
