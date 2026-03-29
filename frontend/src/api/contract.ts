import request from '@/utils/request';

// ========================
// Type Definitions
// ========================

export interface ContractOption {
  label: string;
  value: string;
}

export interface TeacherOption extends ContractOption { }
export interface CourseOption extends ContractOption { }

export interface StudentContract {
  id: string;
  student_id: string;
  student_name: string;
  contract_no: string;
  contract_status: 'pending' | 'active' | 'expired' | 'terminated';
  contract_file_uploaded_at?: string | null;
  contract_file_name?: string | null;
  contract_file_path?: string | null;
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
  details: StudentContractDetail[];
  leave_records: StudentContractLeaveRecord[];
  emergency_leave_quota: number;
  used_emergency_leave_count: number;
  addendums: [];
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

export interface StudentContractAddendum {
  id: string;
  addendum_no: string;
  contract_type: string;
  parent_contract_id: string;
  original_end_date: string;
  new_end_date: string;
  addendum_status: string;
  file_path: string;
  file_name: string;
  file_uploaded_at: string;
  notes: string;
  created_at: string;
  updated_at: string;
  parent_contract_no: string;
  person_name: string;
}

export interface StudentContractAddendumUpdate {
  new_end_date: string;
  notes: string;
}

interface ResData<T> {
  data: T;
  message: string;
  success: boolean;
}

// export interface DownloadUrlResponse {
//   url: string;
// }

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

export function updateContractDetail(contractId: string, detailId: string, data: StudentContractDetailCreate) {
  return request.put<StudentContractDetail>(`/v1/student-contracts/${contractId}/details/${detailId}`, data);
}

export function deleteContractDetail(contractId: string, detailId: string) {
  return request.delete(`/v1/student-contracts/${contractId}/details/${detailId}`);
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
  return request.get<string>(`/v1/student-contracts/${contractId}/download-url`);
}

export function generateContract(contractId: string) {
  return request.post(`/v1/student-contracts/${contractId}/generate-pdf`);
}

export function uploadContract(contractId: string, data: FormData) {
  return request.post(`/v1/student-contracts/${contractId}/upload-url`, data);
}

export function getAddendum(contractId: string, addendumId: string) {
  return request.get<any, ResData<StudentContractAddendum>>(`/v1/student-contracts/${contractId}/addendums/${addendumId}`);
}

export function createAddendum(contractId: string, data: StudentContractAddendumUpdate) {
  return request.post<any, ResData<StudentContractAddendum>>(`/v1/student-contracts/${contractId}/addendums`, data);
}

export function updateAddendum(contractId: string, addendumId: string, data: StudentContractAddendumUpdate) {
  return request.put<any, ResData<StudentContractAddendum>>(`/v1/student-contracts/${contractId}/addendums/${addendumId}`, data);
}

export function deleteAddendum(contractId: string, addendumId: string) {
  return request.delete(`/v1/student-contracts/${contractId}/addendums/${addendumId}`);
}