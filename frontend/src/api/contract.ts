import request from '@/utils/request';

// ========================
// Type Definitions
// ========================

export interface ContractOption {
  label: string;
  value: string;
}

export interface TeacherOption extends ContractOption {}
export interface CourseOption extends ContractOption {}

export interface StudentContract {
  id: string;
  student_id: string;
  contract_no: string;
  contract_status: 'pending' | 'active' | 'expired' | 'terminated';
  is_recurring: boolean;
  start_date: string;
  end_date: string;
  total_lessons: number;
  remaining_lessons: number;
  total_amount: number;
  total_leave_allowed: number;
  used_leave_count: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  contract_url?: string | null;
}

export interface StudentContractUpdate {
  contract_status: 'pending' | 'active' | 'expired' | 'terminated';
  is_recurring?: boolean;
  start_date: string;
  end_date: string;
  total_lessons: number;
  total_amount: number;
  total_leave_allowed?: number;
  notes?: string | null;
}

export interface StudentContractDetail {
  id: string;
  contract_id: string;
  detail_type: 'lesson_price' | 'discount' | 'compensation';
  course_id?: string | null;
  course_name?: string | null;
  description: string;
  amount?: number | null;
  notes?: string | null;
  created_at: string;
}

export interface StudentContractDetailCreate {
  detail_type: 'lesson_price' | 'discount' | 'compensation';
  course_id?: string | null;
  description: string;
  amount?: number | null;
  notes?: string | null;
}

export interface StudentContractLeaveRecord {
  id: string;
  contract_id: string;
  leave_date: string;
  reason?: string | null;
  created_at: string;
}

export interface StudentContractLeaveRecordCreate {
  leave_date: string;
  reason?: string | null;
}

export interface DownloadUrlResponse {
  url: string;
}

export interface GetStudentContractsParams {
  student_id: string;
}

// ========================
// API Functions
// ========================

export function getContractTeacherOptions() {
  return request.get<TeacherOption[]>('/v1/student-contracts/options/teachers');
}

export function getContractCourseOptions(studentId: string) {
  return request.get<CourseOption[]>('/v1/student-contracts/options/courses', { params: { student_id: studentId } });
}

export function getStudentContracts(params: GetStudentContractsParams) {
  return request.get<StudentContract[]>('/v1/student-contracts', { params });
}

export function updateStudentContract(contractId: string, data: StudentContractUpdate) {
  return request.put<StudentContract>(`/v1/student-contracts/${contractId}`, data);
}

export function getContractDetails(contractId: string) {
  return request.get<StudentContractDetail[]>(`/v1/student-contracts/${contractId}/details`);
}

export function createContractDetail(contractId: string, data: StudentContractDetailCreate) {
  return request.post<StudentContractDetail>(`/v1/student-contracts/${contractId}/details`, data);
}

export function getContractLeaveRecords(contractId: string) {
  return request.get<StudentContractLeaveRecord[]>(`/v1/student-contracts/${contractId}/leave-records`);
}

export function createContractLeaveRecord(contractId: string, data: StudentContractLeaveRecordCreate) {
  return request.post<StudentContractLeaveRecord>(`/v1/student-contracts/${contractId}/leave-records`, data);
}

export function deleteContractLeaveRecord(contractId: string, recordId: string) {
  return request.delete(`/v1/student-contracts/${contractId}/leave-records/${recordId}`);
}

export function getContractDownloadUrl(contractId: string) {
  return request.get<DownloadUrlResponse>(`/v1/student-contracts/${contractId}/download-url`);
}
