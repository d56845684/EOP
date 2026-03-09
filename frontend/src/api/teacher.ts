import request from '@/utils/request';

export interface TeacherListParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean | string; // Handle 'all' to undefined transformation
}

export interface TeacherCreate {
  teacher_no: string; // Required
  name: string;       // Required
  email: string;      // Required
  phone?: string | null;
  address?: string | null;
  bio?: string | null;
  teacher_level?: number;
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
