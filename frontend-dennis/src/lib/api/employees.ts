import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

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
    has_account: boolean
    role_id?: string
    role_name?: string
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
    role_id?: string
    is_active?: boolean
}

export interface Role {
    id: string
    key: string
    name: string
}

export interface EmployeeListResponse {
    data: Employee[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export const employeesApi = {
    list: (params?: { page?: number; per_page?: number; search?: string; is_active?: boolean; employee_type?: string }) =>
        apiGet<EmployeeListResponse>(`/api/v1/employees${qs(params || {})}`, '取得員工列表失敗', { extractData: false }),

    create: (data: CreateEmployeeData) =>
        apiPost<Employee>('/api/v1/employees', data, '建立員工失敗'),

    update: (id: string, data: UpdateEmployeeData) =>
        apiPut<Employee>(`/api/v1/employees/${id}`, data, '更新員工失敗'),

    delete: (id: string) =>
        apiDelete(`/api/v1/employees/${id}`, '刪除員工失敗'),

    listRoles: () =>
        apiGet<Role[]>('/api/v1/employees/roles', '取得角色列表失敗'),
}
