import request from '@/utils/request';
import type { BaseResponse, DataResponse, DownloadResponse, ListResponse } from './response';

// ========================
// Type Definitions
// ========================

export interface ContractOption {
  label: string;
  value: string;
}

export interface TeacherOption extends ContractOption { }
export interface CourseOption {
  id: string;
  course_code?: string | null;
  course_name: string;
}

export interface StudentContract {
  id: string;
  student_id: string;
  student_name: string;
  contract_no: string;
  contract_status: StudentContractStatus;
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
  remaining_emergency_leave_count?: number | null;
  addendums: StudentContractAddendum[];
}

export interface StudentContractUpdate {
  contract_status: StudentContractStatus;
  is_recurring?: boolean;
  start_date: string;
  end_date: string;
  total_lessons: number;
  total_amount: number;
  total_leave_allowed?: number;
  notes?: string | null;
}

export interface StudentContractCreate {
  student_id: string;
  contract_status: StudentContractStatus;
  is_recurring?: boolean;
  start_date: string;
  end_date: string;
  total_lessons: number;
  remaining_lessons: number;
  total_amount: number;
  total_leave_allowed?: number | null;
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
  file_path?: string | null;
  file_name?: string | null;
  file_uploaded_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  parent_contract_no?: string | null;
  person_name?: string | null;
}

export interface StudentContractAddendumUpdate {
  new_end_date: string;
  notes: string;
}

interface ResData<T> {
  data: T;
  message: string;
  success: boolean;
  error_code?: string | null;
}

export interface ConfirmUploadResponse {
  success?: boolean;
  message?: string;
  error_code?: string | null;
  storage_path: string;
  upload_url: string;
  content_type: string;
  max_size_bytes: number;
}

export interface GetStudentContractsParams {
  student_id?: string;
  page?: number;
  per_page?: number;
  search?: string;
  contract_status?: StudentContractStatus | '';
}

export type StudentContractStatus = 'pending' | 'active' | 'suspended' | 'expired' | 'terminated';

// ========================
// API Functions
// ========================

export function getContractTeacherOptions() {
  return request.get<any, DataResponse<TeacherOption[]>>('/v1/student-contracts/options/teachers');
}

export function getContractCourseOptions(studentId: string) {
  return request.get<any, DataResponse<CourseOption[]>>('/v1/student-contracts/options/courses', { params: { student_id: studentId } });
}

export function getStudentContracts(params: GetStudentContractsParams) {
  return request.get<any, ListResponse<StudentContract>>('/v1/student-contracts', { params });
}

export function createStudentContract(data: StudentContractCreate) {
  return request.post<any, ResData<StudentContract>>('/v1/student-contracts', data);
}

export function updateStudentContract(contractId: string, data: StudentContractUpdate) {
  return request.put<any, ResData<StudentContract>>(`/v1/student-contracts/${contractId}`, data);
}

export function getContractDetails(contractId: string) {
  return request.get<any, DataResponse<StudentContractDetail[]>>(`/v1/student-contracts/${contractId}/details`);
}

export function createContractDetail(contractId: string, data: StudentContractDetailCreate) {
  return request.post<any, ResData<StudentContractDetail>>(`/v1/student-contracts/${contractId}/details`, data);
}

export function updateContractDetail(contractId: string, detailId: string, data: StudentContractDetailCreate) {
  return request.put<any, ResData<StudentContractDetail>>(`/v1/student-contracts/${contractId}/details/${detailId}`, data);
}

export function deleteContractDetail(contractId: string, detailId: string) {
  return request.delete<any, BaseResponse>(`/v1/student-contracts/${contractId}/details/${detailId}`);
}

export function getContractLeaveRecords(contractId: string) {
  return request.get<any, DataResponse<StudentContractLeaveRecord[]>>(`/v1/student-contracts/${contractId}/leave-records`);
}

export function createContractLeaveRecord(contractId: string, data: StudentContractLeaveRecordCreate) {
  return request.post<any, ResData<StudentContractLeaveRecord>>(`/v1/student-contracts/${contractId}/leave-records`, data);
}

export function deleteContractLeaveRecord(contractId: string, recordId: string) {
  return request.delete<any, BaseResponse>(`/v1/student-contracts/${contractId}/leave-records/${recordId}`);
}

export function getContractDownloadUrl(contractId: string) {
  return request.get<any, DownloadResponse>(`/v1/student-contracts/${contractId}/download-url`);
}

export function generateContract(contractId: string) {
  return request.get(`/v1/student-contracts/${contractId}/generate-docx`, { responseType: 'blob' });
}

export function uploadStudentContract(contractId: string) {
  return request.post<any, ConfirmUploadResponse>(`/v1/student-contracts/${contractId}/upload-url`);
}

export function confirmUploadContract(contractId: string, data: { storage_path: string, file_name: string }) {
  return request.post<any, ResData<StudentContract>>(`/v1/student-contracts/${contractId}/confirm-upload`, data);
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
  return request.delete<any, BaseResponse>(`/v1/student-contracts/${contractId}/addendums/${addendumId}`);
}

export function uploadStudentContractAddendum(contractId: string, addendumId: string) {
  return request.post<any, ConfirmUploadResponse>(`/v1/student-contracts/${contractId}/addendums/${addendumId}/upload-url`);
}

export function confirmuploadStudentContractAddendum(contractId: string, addendumId: string, data: { storage_path: string, file_name: string }) {
  return request.post<any, ResData<StudentContract>>(`/v1/student-contracts/${contractId}/addendums/${addendumId}/confirm-upload`, data);
}
