import request from '@/utils/request';

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface DataResponse_UserProfile_ {
  data: UserProfile;
  message?: string;
  success?: boolean;
}

export function getUserProfileApi() {
  return request.get<any, DataResponse_UserProfile_>('/v1/users/profile');
}

export interface RoleInfo {
  id: string;
  name: string;
  key: string;
  description?: string;
  is_system?: boolean;
  page_count?: number;
}

export interface AccountInfo {
  id: string;
  email: string;
  name: string | null;
  role: string;
  role_id: string;
  employee_subtype: string | null;
  is_active: boolean;
  is_protected: boolean;
  created_at: string;
}

export interface AccountUpdate {
  role_id?: string;
  employee_subtype?: string | null;
  is_active: boolean;
}

export function getUsersApi(params?: { page?: number; per_page?: number; role?: string; search?: string }) {
  return request.get<any, any>('/v1/users/', { params });
}

export function getRolesApi() {
  return request.get<any, any>('/v1/roles');
}

export function updateUserApi(userId: string, data: AccountUpdate) {
  return request.put<any, any>(`/v1/users/${userId}`, data);
}

export function deleteUserApi(userId: string) {
  return request.delete<any, any>(`/v1/users/${userId}`);
}
