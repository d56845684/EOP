import request from '@/utils/request';

// Base Interfaces
export type EmploymentType = 'hourly' | 'full_time';
export type ContractStatus = 'pending' | 'active' | 'expired' | 'terminated';
export type DetailType = 'course_rate'; // Based on app__schemas__teacher_contract__DetailType

// Contracts
export interface TeacherContractCreate {
  teacher_id: string; // Required
  status?: ContractStatus;
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
  status?: ContractStatus | null;
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
  id: string;
  teacher_id: string;
  status: ContractStatus;
  start_date?: string | null;
  end_date?: string | null;
  employment_type?: EmploymentType | null;
  trial_completed_bonus: number;
  trial_to_formal_bonus: number;
  work_start_time?: string | null;
  work_end_time?: string | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherContractListResponse {
  success: boolean;
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
  data: TeacherWorkScheduleResponse[];
  total: number;
}

// Contract Details (Course Rates)
export interface TeacherContractDetailCreate {
  detail_type: DetailType; // Required
  course_id?: string | null;
  description?: string | null;
  amount: number; // Required
  notes?: string | null;
}

export interface TeacherContractDetailResponse {
  id: string;
  teacher_contract_id: string;
  detail_type: DetailType;
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
  data: TeacherContractDetailResponse[];
  total: number;
}

// Option Responses
export interface CourseOption {
  id: string;
  name: string;
}
export interface OptionsResponse {
  success: boolean;
  data: CourseOption[];
}

// API Methods
export function getTeacherContracts(teacherId: string) {
  return request.get<any, TeacherContractListResponse>('/v1/teacher-contracts', { params: { teacher_id: teacherId } });
}

export function createTeacherContract(data: TeacherContractCreate) {
  return request.post<any, any>('/v1/teacher-contracts', data); // wrapped in base response usually
}

export function updateTeacherContract(contractId: string, data: TeacherContractUpdate) {
  return request.put<any, any>(`/v1/teacher-contracts/${contractId}`, data);
}

// Work Schedules
export function getTeacherWorkSchedules(contractId: string) {
  return request.get<any, TeacherWorkScheduleListResponse>(`/v1/teacher-contracts/${contractId}/work-schedules`);
}

export function batchSetTeacherWorkSchedules(contractId: string, data: TeacherWorkScheduleBatchSet) {
  return request.put<any, any>(`/v1/teacher-contracts/${contractId}/work-schedules`, data);
}

// Contract Details
export function getTeacherContractDetails(contractId: string) {
  return request.get<any, TeacherContractDetailListResponse>(`/v1/teacher-contracts/${contractId}/details`);
}

export function createTeacherContractDetail(contractId: string, data: TeacherContractDetailCreate) {
  return request.post<any, any>(`/v1/teacher-contracts/${contractId}/details`, data);
}

export function deleteTeacherContractDetail(contractId: string, detailId: string) {
  return request.delete<any, any>(`/v1/teacher-contracts/${contractId}/details/${detailId}`);
}

// Options
export function getCourseOptions() {
  return request.get<any, OptionsResponse>('/v1/teacher-contracts/options/courses');
}
