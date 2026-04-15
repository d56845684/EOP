import request from '@/utils/request';
import type { BaseResponse, DataResponse, ListResponse } from './response';

export interface TeacherListParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean | string; // Handle 'all' to undefined transformation
}

export interface TeacherCreate {
  teacher_no?: string | null; // Optional auto-gen
  name: string;       // Required
  email: string;      // Required
  phone?: string | null;
  address?: string | null;
  bio?: string | null;
  teacher_level?: number | null;
  is_active?: boolean;
}

export interface TeacherUpdate {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  bio?: string | null;
  teacher_level?: number | null;
  is_active?: boolean | null;
}

export interface TeacherResponse {
  id: string;
  teacher_no: string;
  name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  bio?: string | null;
  teacher_level: number;
  is_active: boolean;
  avatar_url?: string | null;
  email_verified_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Overview list
export interface TeacherOverviewParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean | null;
  has_account?: boolean | null;
  has_active_contract?: boolean | null;
  role?: string | null;
}

export interface TeacherOverviewItem {
  account_active: boolean | null;
  active_contracts: number;
  avatar_url?: string | null;
  bonus_count: number;
  completed_bookings: number;
  created_at: string;
  email: string;
  email_verified_at: string | null;
  has_account: boolean;
  id: string;
  is_active: boolean;
  line_bound: boolean;
  line_display_name: string | null;
  name: string;
  phone: string | null;
  role: string | null;
  teacher_level: number;
  teacher_no: string;
  total_bonus: number;
  total_bookings: number;
  total_contracts: number;
  upcoming_bookings: number;
}

export interface TeacherOverviewListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherOverviewItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface TeacherDetailResponse<T> {
  success: boolean;
  message: string;
  error_code?: string | null;
  data: T;
}

export interface UploadTeacherAvatarUrlResponse {
  success?: boolean;
  message?: string;
  error_code?: string | null;
  upload_url: string;
  storage_path: string;
  content_type: string;
  max_size_bytes: number;
}

export function getTeacherList(params: TeacherListParams) {
  return request.get<any, TeacherListResponse>('/v1/teachers', { params });
}
export function getTeacherOverviewList(params: TeacherOverviewParams) {
  return request.get<any, TeacherOverviewListResponse>('/v1/teachers/overview/list', { params });
}
export function createTeacher(data: TeacherCreate) {
  return request.post<any, TeacherDetailResponse<TeacherResponse>>('/v1/teachers', data);
}
export function updateTeacher(teacherId: string, data: TeacherUpdate) {
  return request.put<any, TeacherDetailResponse<TeacherResponse>>(`/v1/teachers/${teacherId}`, data);
}
export function deleteTeacher(teacherId: string) {
  return request.delete<any, BaseResponse>(`/v1/teachers/${teacherId}`);
}
export function getTeacherById(teacherId: string) {
  return request.get<any, TeacherDetailResponse<TeacherResponse>>(`/v1/teachers/${teacherId}`);
}
export function getTeacherAvatarUploadUrl(teacherId: string, data: { file_name: string }) {
  return request.post<any, UploadTeacherAvatarUrlResponse>(`/v1/teachers/${teacherId}/avatar/upload-url`, data);
}
export function confirmTeacherAvatar(teacherId: string, data: { storage_path: string, file_name: string }) {
  return request.post<any, TeacherDetailResponse<TeacherResponse>>(`/v1/teachers/${teacherId}/avatar/confirm-upload`, data);
}
