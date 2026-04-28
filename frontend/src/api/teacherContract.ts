import request from '@/utils/request';
import type { BaseResponse, DataResponse, DownloadResponse } from './response';

// Base Interfaces
export type EmploymentType = 'hourly' | 'full_time';
export type ContractStatus = 'pending' | 'active' | 'expired' | 'terminated';
export type DetailType = 'course_rate'; // Based on app__schemas__teacher_contract__DetailType

// Contracts
export interface TeacherContractCreate {
  teacher_id: string; // Required
  contract_status?: ContractStatus;
  start_date?: string | null; // date format
  end_date?: string | null; // date format
  employment_type?: EmploymentType | null;
  trial_completed_bonus?: number | null;
  trial_to_formal_bonus?: number | null;
  work_start_time?: string | null;
  work_end_time?: string | null;
  notes?: string | null;
}

export interface TeacherContractUpdate {
  contract_status?: ContractStatus | null;
  start_date?: string | null;
  end_date?: string | null;
  employment_type?: EmploymentType | null;
  trial_completed_bonus?: number | null;
  trial_to_formal_bonus?: number | null;
  work_start_time?: string | null;
  work_end_time?: string | null;
  notes?: string | null;
}

export interface TeacherContractResponse {
  addendums: TeacherContractAddendumResponse[];
  contract_file_name: string | null;
  contract_file_path: string | null;
  contract_file_uploaded_at: string | null;
  details: TeacherContractDetailResponse[];
  id: string;
  teacher_id: string;
  teacher_name: string;
  contract_status: ContractStatus;
  contract_no: string;
  start_date?: string | null;
  end_date?: string | null;
  employment_type?: EmploymentType | null;
  trial_completed_bonus: number;
  trial_to_formal_bonus: number;
  work_start_time?: string | null;
  work_end_time?: string | null;
  work_schedules: TeacherWorkScheduleResponse[];
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherContractListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherContractResponse[];
  total: number;
}

// Work Schedules
export interface TeacherWorkScheduleCreate {
  weekday: number; // 0-6
  start_time: string; // HH:mm
  end_time: string; // HH:mm
  notes?: string | null;
}

export interface TeacherWorkScheduleResponse extends TeacherWorkScheduleCreate {
  id: string;
  teacher_contract_id: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherWorkScheduleBatchSet {
  schedules: TeacherWorkScheduleCreate[];
}

export interface TeacherWorkScheduleListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherWorkScheduleResponse[];
  total: number;
}

// Contract Details (Course Rates)
export interface TeacherContractDetailCreate {
  detail_type: 'base_salary' | 'allowance' | 'course_rate';
  course_id?: string | null;
  description?: string | null;
  amount: number; // Required
  notes?: string | null;
}

export interface TeacherContractDetailResponse {
  id: string;
  teacher_contract_id: string;
  detail_type: 'base_salary' | 'allowance' | 'course_rate';
  course_id?: string | null;
  course_name?: string | null;
  description?: string | null;
  amount: number;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherContractDetailListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherContractDetailResponse[];
  total: number;
}

// Option Responses
export interface CourseOption {
  id: string;
  name: string;
  course_code?: string;
  course_name?: string;
}
export interface OptionsResponse {
  success?: boolean;
  message?: string;
  error_code?: string | null;
  data: CourseOption[];
}

export interface ConfirmUploadResponse {
  success?: boolean;
  message?: string;
  error_code?: string | null;
  upload_url: string;
  storage_path: string;
  content_type: string;
  max_size_bytes: number;
}

export interface ResData<T> {
  data: T;
  message: string;
  success: boolean;
  error_code?: string | null;
}

// API Methods

// ─── Addendums ────────────────────────────────────────────────────────────────
export interface TeacherContractAddendumCreate {
  new_end_date?: string | null;
  notes?: string | null;
}

export interface TeacherContractAddendumUpdate {
  new_end_date?: string | null;
  notes?: string | null;
}

export interface TeacherContractAddendumResponse {
  id: string;
  addendum_no: string;
  parent_contract_id: string;
  original_end_date?: string | null;
  new_end_date?: string | null;
  addendum_status: string;
  file_path?: string | null;
  file_name?: string | null;
  file_uploaded_at?: string | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  parent_contract_no?: string | null;
  person_name?: string | null;
}

export interface TeacherContractAddendumListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: TeacherContractAddendumResponse[];
}

// API Methods
export function getTeacherContracts(teacherId: string) {
  return request.get<any, TeacherContractListResponse>('/v1/teacher-contracts', { params: { teacher_id: teacherId } });
}

export function createTeacherContract(data: TeacherContractCreate) {
  return request.post<any, DataResponse<TeacherContractResponse>>('/v1/teacher-contracts', data);
}

export function updateTeacherContract(contractId: string, data: TeacherContractUpdate) {
  return request.put<any, DataResponse<TeacherContractResponse>>(`/v1/teacher-contracts/${contractId}`, data);
}

// Work Schedules
export function getTeacherWorkSchedules(contractId: string) {
  return request.get<any, TeacherWorkScheduleListResponse>(`/v1/teacher-contracts/${contractId}/work-schedules`);
}

export function batchSetTeacherWorkSchedules(contractId: string, data: TeacherWorkScheduleBatchSet) {
  return request.put<any, BaseResponse>(`/v1/teacher-contracts/${contractId}/work-schedules`, data);
}

// Contract Details
export function getTeacherContractDetails(contractId: string) {
  return request.get<any, TeacherContractDetailListResponse>(`/v1/teacher-contracts/${contractId}/details`);
}

export function createTeacherContractDetail(contractId: string, data: TeacherContractDetailCreate) {
  return request.post<any, DataResponse<TeacherContractDetailResponse>>(`/v1/teacher-contracts/${contractId}/details`, data);
}

export function deleteTeacherContractDetail(contractId: string, detailId: string) {
  return request.delete<any, BaseResponse>(`/v1/teacher-contracts/${contractId}/details/${detailId}`);
}

// Generate PDF (returns binary blob)
export function generateTeacherContractPdf(contractId: string) {
  return request.get(`/v1/teacher-contracts/${contractId}/generate-pdf`, { responseType: 'blob' });
}

// Addendums
export function getTeacherContractAddendums(contractId: string) {
  return request.get<any, TeacherContractAddendumListResponse>(`/v1/teacher-contracts/${contractId}/addendums`);
}

export function createTeacherContractAddendum(contractId: string, data: TeacherContractAddendumCreate) {
  return request.post<any, ResData<TeacherContractAddendumResponse>>(`/v1/teacher-contracts/${contractId}/addendums`, data);
}

export function updateTeacherContractAddendum(contractId: string, addendumId: string, data: TeacherContractAddendumUpdate) {
  return request.put<any, ResData<TeacherContractAddendumResponse>>(`/v1/teacher-contracts/${contractId}/addendums/${addendumId}`, data);
}

export function deleteTeacherContractAddendum(contractId: string, addendumId: string) {
  return request.delete<any, BaseResponse>(`/v1/teacher-contracts/${contractId}/addendums/${addendumId}`);
}

export function uploadTeacherContract(contractId: string) {
  return request.post<any, ConfirmUploadResponse>(`/v1/teacher-contracts/${contractId}/upload-url`);
}

export function confirmUploadTeacherContract(contractId: string, data: { storage_path: string, file_name: string }) {
  return request.post<any, ResData<TeacherContractResponse>>(`/v1/teacher-contracts/${contractId}/confirm-upload`, data);
}

export function getTeacherContractDownloadUrl(contractId: string) {
  return request.get<any, DownloadResponse>(`/v1/teacher-contracts/${contractId}/download-url`);
}

export function uploadTeacherContractAddendum(contractId: string, addendumId: string) {
  return request.post<any, ConfirmUploadResponse>(`/v1/teacher-contracts/${contractId}/addendums/${addendumId}/upload-url`);
}

export function confirmUploadTeacherContractAddendum(contractId: string, addendumId: string, data: { storage_path: string, file_name: string }) {
  return request.post<any, ResData<TeacherContractResponse>>(`/v1/teacher-contracts/${contractId}/addendums/${addendumId}/confirm-upload`, data);
}

// Options
export function getCourseOptions() {
  return request.get<any, OptionsResponse>('/v1/teacher-contracts/options/courses');
}
