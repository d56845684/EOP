import request from '@/utils/request';

export interface StudentListParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean | string; // allowing 'all' before transformation
  student_type?: string; // 'formal' | 'trial' | 'all'
}

export interface StudentCreate {
  student_no: string;
  name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  birth_date?: string | null;
  student_type?: string; // default: formal
  is_active?: boolean;
}

export interface StudentUpdate {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  birth_date?: string | null;
  student_type?: string | null;
  is_active?: boolean | null;
}

export interface ConvertToFormalRequest {
  contract_no: string;
  total_lessons: number;
  total_amount: number;
  start_date: string;
  end_date: string;
  teacher_id?: string | null;
  booking_id?: string | null;
  notes?: string | null;
}

export interface StudentResponse {
  id: string;
  student_no: string;
  name: string;
  email: string;
  phone: string | null;
  address: string | null;
  birth_date: string | null;
  student_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentListResponse {
  items: StudentResponse[];
  total: number;
  page: number;
  per_page: number;
}

export function getStudentList(params: StudentListParams) {
  return request.get<StudentListResponse>('/v1/students', { params });
}

export function createStudent(data: StudentCreate) {
  return request.post<StudentResponse>('/v1/students', data);
}

export function updateStudent(id: string, data: StudentUpdate) {
  return request.put<StudentResponse>(`/v1/students/${id}`, data);
}

export function deleteStudent(id: string) {
  return request.delete(`/v1/students/${id}`);
}

export function convertToFormal(id: string, data: ConvertToFormalRequest) {
  return request.post<StudentResponse>(`/v1/students/${id}/convert-to-formal`, data);
}
