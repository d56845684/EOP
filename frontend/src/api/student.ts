import request from '@/utils/request';

export interface StudentListParams {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean | string; // allowing 'all' before transformation
  student_type?: string; // 'formal' | 'trial' | 'all'
}

export interface StudentOverviewListParams extends StudentListParams {
  has_account?: boolean | string;
  has_active_contract?: boolean | string;
  role?: string; //student/teacher/admin/employee
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
  email_verified_at: string | null;
  updated_at: string;
}

export interface StudentListResponse<T> {
  success: boolean;
  message: string;
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface StudentOverviewListResponse {
  id: string;
  student_no: string;
  name: string;
  eng_name: string;
  email: string;
  phone: string | null;
  student_type: string;
  is_active: boolean;
  email_verified_at: string | null;
  created_at: string;
  has_account: boolean;
  account_active: string | null;
  role: string | null;
  line_bound: boolean;
  line_display_name: string | null;
  total_contracts: number;
  active_contracts: number;
  remaining_lessons: number;
  total_bookings: number;
  completed_bookings: number;
  upcoming_bookings: number;
}

export interface StudentOverviewResponse {
  success: boolean;
  message: string;
  data: StudentOverviewDetail;
}

export interface StudentOverviewDetail {
  student: StudentResponse;
  account: AccountSummary;
  line_binding: LineBindingSummary;
  contracts: ContractSummary[];
  bookings_recent: BookingRecentSummary[];
  courses: CourseSummary[];
  teacher_preferences: TeacherPreferenceSummary[];
  leave_records_recent: LeaveRecordSummary[];
  stats: StudentStatsSummary;
}

export interface AccountSummary {
  has_account: boolean;
  is_active: boolean;
  role: string | null;
}

export interface LineBindingSummary {
  bound: boolean;
  line_display_name: string | null;
  line_picture_url: string | null;
  binding_status: string | null;
}

export interface ContractSummary {
  id: string;
  contract_no: string;
  contract_status: string;
  teachers: string[];
  total_lessons: number;
  remaining_lessons: number;
  total_amount: number;
  total_leave_allowed: number;
  used_leave_count: number;
  used_emergency_leave_count: number;
  is_recurring: boolean;
  start_date: string | null;
  end_date: string | null;
  addendum_count: number;
}

export interface BookingRecentSummary {
  id: string;
  booking_date: string | null;
  teacher_name: string | null;
  course_name: string | null;
  start_time: string | null;
  end_time: string | null;
  booking_status: string;
  booking_type: string | null;
}

export interface CourseSummary {
  id: string;
  course_id: string;
  course_name: string | null;
  course_code: string | null;
  enrolled_at: string | null;
}

export interface TeacherPreferenceSummary {
  id: string;
  course_name: string | null;
  teacher_name: string | null;
  min_teacher_level: number | null;
  primary_teacher_name: string | null;
}

export interface LeaveRecordSummary {
  id: string;
  leave_date: string | null;
  leave_status: string | null;
  leave_type: string | null;
  reason: string | null;
  booking_date: string | null;
}

export interface StudentStatsSummary {
  total_bookings: number;
  completed_bookings: number;
  cancelled_bookings: number;
  pending_bookings: number;
  upcoming_bookings: number;
  total_contracts: number;
  active_contracts: number;
  total_remaining_lessons: number;
  total_leaves_used: number;
  total_courses_enrolled: number;
}


export function getStudentList(params: StudentListParams) {
  return request.get<StudentListResponse<StudentResponse>>('/v1/students', { params });
}

export function getStudentOverviewList(params: StudentOverviewListParams) {
  return request.get<StudentListResponse<StudentOverviewListResponse>>('/v1/students/overview/list', { params });
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

export function getStudentView(id: string) {
  return request.get<StudentOverviewResponse>(`/v1/students/${id}/view`);
}
