import request from '@/utils/request';

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
  email_verified_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherListResponse {
  success: boolean;
  data: TeacherResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface TeacherDetailResponse {
  success: boolean;
  message: string;
  data: TeacherResponse;
}

export function getTeacherList(params: TeacherListParams) {
  return request.get<any, TeacherListResponse>('/v1/teachers', { params });
}
export function createTeacher(data: TeacherCreate) {
  return request.post('/v1/teachers', data);
}
export function updateTeacher(teacherId: string, data: TeacherUpdate) {
  return request.put(`/v1/teachers/${teacherId}`, data);
}
export function deleteTeacher(teacherId: string) {
  return request.delete(`/v1/teachers/${teacherId}`);
}
export function getTeacherById(teacherId: string) {
  return request.get<any, TeacherDetailResponse>(`/v1/teachers/${teacherId}`);
}
export function getTeacherAvatarUploadUrl(teacherId: string) {
  return request.get<any, string>(`/v1/teachers/${teacherId}/avatar/upload-url`);
}
export function confirmTeacherAvatar(teacherId: string) {
  return request.post<any, { storage_path: string, file_name: string }>(`/v1/teachers/${teacherId}/avatar/confirm-upload`);
}