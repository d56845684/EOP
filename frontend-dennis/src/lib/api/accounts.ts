import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export interface AccountInfo {
  id: string
  email: string
  name: string | null
  role: string
  role_id: string | null
  employee_subtype: string | null
  is_active: boolean
  is_protected: boolean
  created_at: string | null
}

export interface AccountListResponse {
  success: boolean
  data: AccountInfo[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface AccountUpdateData {
  role_id?: string
  employee_subtype?: string
  is_active?: boolean
}

export interface RoleInfo {
  id: string
  key: string
  name: string
  description: string | null
  is_system: boolean
  page_count: number
}

export interface PageInfo {
  id: string
  key: string
  name: string
  description?: string
  parent_key?: string
  sort_order: number
  is_active: boolean
}

export interface UserPageOverride {
  id: string
  page_id: string
  page_key?: string
  page_name?: string
  access_type: 'grant' | 'revoke'
}

export const accountsApi = {
  list: (params: { page?: number; per_page?: number; role?: string; search?: string }) =>
    apiGet<AccountListResponse>(`/api/v1/users${qs(params)}`, '取得帳號列表失敗', { extractData: false }),

  update: (userId: string, data: AccountUpdateData) =>
    apiPut(`/api/v1/users/${userId}`, data, '更新帳號失敗', { extractData: false }),

  deactivate: (userId: string) =>
    apiDelete(`/api/v1/users/${userId}`, '停用帳號失敗'),

  // ========== Roles ==========

  getRoles: () =>
    apiGet<RoleInfo[]>('/api/v1/roles', '取得角色列表失敗'),

  createRole: (data: { key: string; name: string; description?: string }) =>
    apiPost('/api/v1/roles', data, '建立角色失敗', { extractData: false }),

  updateRole: (roleId: string, data: { name?: string; description?: string }) =>
    apiPut(`/api/v1/roles/${roleId}`, data, '更新角色失敗', { extractData: false }),

  deleteRole: (roleId: string) =>
    apiDelete(`/api/v1/roles/${roleId}`, '刪除角色失敗'),

  // ========== Permission wrappers ==========

  getAllPages: () =>
    apiGet<PageInfo[]>('/api/v1/pages?per_page=200', '取得頁面列表失敗'),

  async getRolePages(roleId: string): Promise<{ data: PageInfo[] | null; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/role-pages?role_id=${roleId}`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得角色頁面失敗' } }
      }
      const result = await response.json()
      return { data: result.pages || [], error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得角色頁面失敗' } }
    }
  },

  setRolePages: (roleId: string, pageIds: string[]) =>
    apiPut('/api/v1/role-pages', { role_id: roleId, page_ids: pageIds }, '設定角色頁面失敗', { extractData: false }),

  async getUserOverrides(userId: string): Promise<{ data: UserPageOverride[] | null; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/user-pages/${userId}`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得用戶覆寫失敗' } }
      }
      const result = await response.json()
      return { data: result.overrides || [], error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得用戶覆寫失敗' } }
    }
  },

  setUserOverrides: (
    userId: string,
    overrides: { page_id: string; access_type: 'grant' | 'revoke' }[]
  ) =>
    apiPut(`/api/v1/user-pages/${userId}`, { overrides }, '設定用戶覆寫失敗', { extractData: false }),
}
