import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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
  async list(params: {
    page?: number
    per_page?: number
    role?: string
    search?: string
  }): Promise<{ data: AccountListResponse | null; error: any }> {
    try {
      const query = new URLSearchParams()
      if (params.page) query.set('page', String(params.page))
      if (params.per_page) query.set('per_page', String(params.per_page))
      if (params.role) query.set('role', params.role)
      if (params.search) query.set('search', params.search)
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/users/?${query.toString()}`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得帳號列表失敗' } }
      }
      const data = await response.json()
      return { data, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得帳號列表失敗' } }
    }
  },

  async update(userId: string, data: AccountUpdateData): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '更新帳號失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '更新帳號失敗' } }
    }
  },

  async deactivate(userId: string): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/users/${userId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '停用帳號失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '停用帳號失敗' } }
    }
  },

  // ========== Roles ==========

  async getRoles(): Promise<{ data: RoleInfo[] | null; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/roles`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得角色列表失敗' } }
      }
      const result = await response.json()
      return { data: result.data || [], error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得角色列表失敗' } }
    }
  },

  async createRole(data: { key: string; name: string; description?: string }): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '建立角色失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '建立角色失敗' } }
    }
  },

  async updateRole(roleId: string, data: { name?: string; description?: string }): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/roles/${roleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '更新角色失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '更新角色失敗' } }
    }
  },

  async deleteRole(roleId: string): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/roles/${roleId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '刪除角色失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '刪除角色失敗' } }
    }
  },

  // ========== Permission wrappers ==========

  async getAllPages(): Promise<{ data: PageInfo[] | null; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/pages?per_page=200`)
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '取得頁面列表失敗' } }
      }
      const result = await response.json()
      return { data: result.data || [], error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '取得頁面列表失敗' } }
    }
  },

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

  async setRolePages(roleId: string, pageIds: string[]): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/role-pages`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_id: roleId, page_ids: pageIds }),
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '設定角色頁面失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '設定角色頁面失敗' } }
    }
  },

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

  async setUserOverrides(
    userId: string,
    overrides: { page_id: string; access_type: 'grant' | 'revoke' }[]
  ): Promise<{ data: any; error: any }> {
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/user-pages/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overrides }),
      })
      if (!response.ok) {
        const err = await response.json()
        return { data: null, error: { message: err.detail || '設定用戶覆寫失敗' } }
      }
      const result = await response.json()
      return { data: result, error: null }
    } catch (e: any) {
      return { data: null, error: { message: e.message || '設定用戶覆寫失敗' } }
    }
  },
}
