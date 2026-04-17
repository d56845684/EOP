import request from '@/utils/request';
import type { BaseResponse, DataResponse, ListResponse } from './response';

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
  success: boolean;
  error_code?: string | null;
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
  role_id: string | null;
  employee_subtype: string | null;
  is_active: boolean;
  is_protected: boolean;
  created_at: string | null;
}

export interface AccountUpdate {
  role_id?: string;
  employee_subtype?: string | null;
  is_active?: boolean;
}

export interface UserPageOverride {
  id: string;
  page_id: string;
  page_key?: string | null;
  page_name?: string | null;
  access_type: 'grant' | 'revoke';
  created_at?: string | null;
}

export interface UserPageOverridesResponse {
  success: boolean;
  user_id: string;
  overrides: UserPageOverride[];
  message?: string;
  error_code?: string | null;
}

export interface UserPageOverrideEntry {
  page_id: string;
  access_type: 'grant' | 'revoke';
}

export function getUsersApi(params?: { page?: number; per_page?: number; role?: string; search?: string; is_active?: boolean }) {
  return request.get<any, ListResponse<AccountInfo>>('/v1/users', { params });
}

export function getRolesApi() {
  return request.get<any, DataResponse<RoleInfo[]>>('/v1/roles');
}

export function updateUserApi(userId: string, data: AccountUpdate) {
  return request.put<any, DataResponse<AccountInfo>>(`/v1/users/${userId}`, data);
}

export function deleteUserApi(userId: string) {
  return request.delete<any, BaseResponse>(`/v1/users/${userId}`);
}

export function getUserPageOverridesApi(userId: string) {
  return request.get<any, UserPageOverridesResponse>(`/v1/user-pages/${userId}`);
}

export function updateUserPageOverridesApi(userId: string, overrides: UserPageOverrideEntry[]) {
  return request.put<any, UserPageOverridesResponse>(`/v1/user-pages/${userId}`, { overrides });
}
