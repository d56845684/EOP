import request from '@/utils/request';
import type { DataResponse, ListResponse } from './response';

export type LeaveInitiatorType = 'student' | 'teacher';
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface LeaveRecordCreate {
  booking_id: string;
  reason: string;
}

export interface LeaveRecordListParams {
  page?: number;
  per_page?: number;
  leave_status?: LeaveStatus | '';
}

export interface LeaveRecordReject {
  rejection_reason: string;
}

export interface LeaveRecordResponse {
  id: string;
  leave_no: string;
  initiator_type: LeaveInitiatorType;
  initiator_student_id?: string | null;
  initiator_teacher_id?: string | null;
  booking_id?: string | null;
  leave_date: string;
  start_time?: string | null;
  end_time?: string | null;
  reason: string;
  leave_status: LeaveStatus;
  approver_id?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  updated_at?: string | null;
  leave_type?: 'normal' | 'emergency' | string | null;
  deduct_lesson?: boolean;
  emergency_quota?: number | null;
  used_emergency_count?: number | null;
  initiator_name?: string | null;
  booking_no?: string | null;
  approver_name?: string | null;
  created_at?: string | null;
}

export function createLeaveRecord(data: LeaveRecordCreate) {
  return request.post<any, DataResponse<LeaveRecordResponse>>('/v1/leave-records', data);
}

export function getLeaveRecordList(params: LeaveRecordListParams) {
  return request.get<any, ListResponse<LeaveRecordResponse>>('/v1/leave-records', { params });
}

export function approveLeaveRecord(leaveId: string) {
  return request.post<any, DataResponse<LeaveRecordResponse>>(`/v1/leave-records/${leaveId}/approve`);
}

export function rejectLeaveRecord(leaveId: string, data: LeaveRecordReject) {
  return request.post<any, DataResponse<LeaveRecordResponse>>(`/v1/leave-records/${leaveId}/reject`, data);
}

export function cancelLeaveRecord(leaveId: string) {
  return request.post<any, DataResponse<LeaveRecordResponse>>(`/v1/leave-records/${leaveId}/cancel`);
}
