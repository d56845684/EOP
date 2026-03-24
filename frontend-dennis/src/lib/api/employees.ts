import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export type EmployeeType = 'admin' | 'full_time' | 'part_time' | 'intern'

export interface Employee {
    id: string
    employee_no: string
    employee_type: EmployeeType
    name: string
    email: string
    phone?: string
    address?: string
    hire_date?: string
    termination_date?: string
    is_active: boolean
    email_verified_at?: string
    created_at?: string
    updated_at?: string
}

export interface CreateEmployeeData {
    employee_no: string
    employee_type: string
    name: string
    email: string
    phone?: string
    address?: string
    hire_date: string
    termination_date?: string
    is_active: boolean
}

export interface UpdateEmployeeData {
    employee_type?: string
    name?: string
    email?: string
    phone?: string
    address?: string
    hire_date?: string
    termination_date?: string
    is_active?: boolean
}

export interface EmployeeListResponse {
    data: Employee[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export const employeesApi = {
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        is_active?: boolean
        employee_type?: string
    }): Promise<{ data: EmployeeListResponse | null, error: any }> {
        try {
            const searchParams = new URLSearchParams()
            if (params?.page) searchParams.set('page', String(params.page))
            if (params?.per_page) searchParams.set('per_page', String(params.per_page))
            if (params?.search) searchParams.set('search', params.search)
            if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
            if (params?.employee_type) searchParams.set('employee_type', params.employee_type)

            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/employees?${searchParams}`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得員工列表失敗' } }
            }
            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateEmployeeData): Promise<{ data: Employee | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/employees`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '建立員工失敗' } }
            }
            const result = await response.json()
            return { data: result.data, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(id: string, data: UpdateEmployeeData): Promise<{ data: Employee | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/employees/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '更新員工失敗' } }
            }
            const result = await response.json()
            return { data: result.data, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(id: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/employees/${id}`, {
                method: 'DELETE',
            })
            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '刪除員工失敗' } }
            }
            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
