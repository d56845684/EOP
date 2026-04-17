import request from '@/utils/request';
import type { BaseResponse, DataResponse } from './response';

// Interfaces based on Swagger
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface UserInfo {
  id: string;
  email: string;
  role: string; // 'student' | 'teacher' | 'employee'
  role_id?: string | null;
  created_at?: string | null;
  employee_type?: string | null;
  permission_level?: number;
  must_change_password?: boolean;
  teacher_id?: string | null;
  student_id?: string | null;
  employee_id?: string | null;
  name?: string | null;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  error_code?: string | null;
  user: UserInfo;
  tokens: TokenPair;
}

export interface InviteLinkRequest {
  entity_type: string; //'student' | 'teacher' | 'employee'
  entity_id: string;
  role_id?: string;
}

export interface InviteLinkResponse {
  success?: boolean;
  message?: string;
  error_code?: string;
  detail?: string;
  invite_url?: string;
  expires_at?: string;
}

export function loginApi(data: LoginRequest) {
  return request.post<any, LoginResponse>('/v1/auth/login', data);
}

export interface LogoutRequest {
  logout_all_devices?: boolean;
}

export function logout(data: LogoutRequest = { logout_all_devices: false }) {
  return request.post<any, BaseResponse>('/v1/auth/logout', data);
}

export function refreshToken() {
  // The Swagger doesn't specify a body, assuming token is sent via HTTP-only cookie or Authorization header
  return request.post<any, { success: boolean; message?: string; error_code?: string | null; data?: TokenPair; tokens?: TokenPair }>('/v1/auth/refresh');
}

export function getMeApi() {
  return request.get<any, DataResponse<UserInfo>>('/v1/auth/me');
}

export function generateInviteLinkApi(data: InviteLinkRequest) {
  return request.post<any, InviteLinkResponse>('/v1/invites/generate', data, { showError: false } as any);
}

export function acceptInviteApi(token: string, password: string) {
  return request.post<any, BaseResponse>('/v1/invites/accept', { token, password });
}
