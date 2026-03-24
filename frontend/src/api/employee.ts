import request from '@/utils/request';

export interface Employee {
    id: string;
    employee_no?: string;
    employee_type?: string;
    name: string;
    email: string;
    phone?: string;
    address?: string;
    hire_date?: string;
    termination_date?: string;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface PageResponse_Employee_ {
    data: Employee[];
    success?: boolean;
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
}

export const getEmployeesApi = (params: any) => {
    return request.get<any, PageResponse_Employee_>('/v1/employees', { params });
}

export const createEmployeeApi = (data: any) => {
    return request.post<any, Omit<Employee, 'id' | 'created_at' | 'updated_at'>>('/v1/employees', data);
}

export const updateEmployeeApi = (id: string, data: any) => {
    return request.put<any, Omit<Employee, 'id' | 'created_at' | 'updated_at'>>(`/v1/employees/${id}`, data);
}

export const deleteEmployeeApi = (id: string) => {
    return request.delete<any, { success: boolean, message?: string }>(`/v1/employees/${id}`);
}