import request from '@/utils/request';

// Role Definitions
export interface RoleInfo {
  id: string;
  key: string;
  name: string;
  description?: string;
  is_system?: boolean;
  page_count?: number;
}

export interface RoleCreate {
  key: string;
  name: string;
  description?: string;
}

export interface RoleUpdate {
  name: string;
  description?: string;
}

export interface RoleListResponse {
  pages: PageResponse[];
  role_id: string;
  success: boolean;
}


export interface DataResponse<T> {
  data: T;
  message?: string;
  success?: boolean;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PaginatedResponse<T> extends DataResponse<PaginatedData<T>> { }

// Role CRUD APIs
export function getRolesApi() {
  return request.get<any, DataResponse<RoleInfo[]>>('/v1/roles');
}

export function createRoleApi(data: RoleCreate) {
  return request.post<any, DataResponse<RoleInfo>>('/v1/roles', data);
}

export function updateRoleApi(roleId: string, data: RoleUpdate) {
  return request.put<any, DataResponse<RoleInfo>>(`/v1/roles/${roleId}`, data);
}

export function deleteRoleApi(roleId: string) {
  return request.delete<any, DataResponse<null>>(`/v1/roles/${roleId}`);
}

// Pages Definitions
export interface PageResponse {
  id: string;
  key: string;
  name: string;
  parent_key?: string | null;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

export interface RolePagesBatchSet {
  role_id: string;
  page_ids: string[];
}

export interface RolePagesResponse {
  role: string | null;
  page_keys: string[];
  pages: PageResponse[];
}

// Pages and Permissions APIs
export function getPagesApi(params?: { per_page: number }) {
  // Use default per_page=200 as requested
  return request.get<any, DataResponse<PageResponse[]>>('/v1/pages', {
    params: { per_page: 200, ...params },
  });
}

export function getRolePagesApi(roleId: string) {
  return request.get<any, RoleListResponse>('/v1/role-pages', {
    params: { role_id: roleId },
  });
}

export function updateRolePagesApi(data: RolePagesBatchSet) {
  return request.put<any, DataResponse<null>>('/v1/role-pages', data);
}
