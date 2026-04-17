import request from '@/utils/request';
import type { BaseResponse, DataResponse, ListResponse } from './response';

export type EmployeeType = 'admin' | 'full_time' | 'part_time' | 'intern';

export interface EmployeeRole {
  id: string;
  key: string;
  name: string;
}

export interface Employee {
  id: string;
  employee_no: string;
  employee_type: EmployeeType;
  name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  hire_date?: string | null;
  termination_date?: string | null;
  is_active: boolean;
  has_account: boolean;
  role_id?: string | null;
  role_name?: string | null;
  email_verified_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface EmployeeListParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean;
  employee_type?: EmployeeType;
}

export interface EmployeeCreate {
  employee_no: string;
  employee_type: EmployeeType;
  name: string;
  email: string;
  phone?: string;
  address?: string;
  hire_date: string;
  termination_date?: string;
  is_active: boolean;
}

export interface EmployeeUpdate {
  employee_type?: EmployeeType;
  name?: string;
  email?: string;
  phone?: string;
  address?: string;
  hire_date?: string;
  termination_date?: string;
  role_id?: string;
  is_active?: boolean;
}

export type EmployeeListResponse = ListResponse<Employee>;

export const getEmployeesApi = (params?: EmployeeListParams) => {
  return request.get<any, EmployeeListResponse>('/v1/employees', { params });
};

export const getEmployeeApi = (id: string) => {
  return request.get<any, DataResponse<Employee>>(`/v1/employees/${id}`);
};

export const getEmployeeRolesApi = () => {
  return request.get<any, DataResponse<EmployeeRole[]>>('/v1/employees/roles');
};

export const createEmployeeApi = (data: EmployeeCreate) => {
  return request.post<any, DataResponse<Employee>>('/v1/employees', data);
};

export const updateEmployeeApi = (id: string, data: EmployeeUpdate) => {
  return request.put<any, DataResponse<Employee>>(`/v1/employees/${id}`, data);
};

export const deleteEmployeeApi = (id: string) => {
  return request.delete<any, BaseResponse>(`/v1/employees/${id}`);
};
