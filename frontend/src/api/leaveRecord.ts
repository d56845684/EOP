import request from '@/utils/request';
import type { DataResponse } from './response';

export interface LeaveRecordCreate {
  booking_id: string;
  reason: string;
}

export interface LeaveRecordResponse {
  id: string;
  leave_no: string;
  initiator_type: 'student' | 'teacher';
  initiator_student_id?: string | null;
  initiator_teacher_id?: string | null;
  booking_id?: string | null;
  leave_date: string;
  start_time?: string | null;
  end_time?: string | null;
  reason: string;
  leave_status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  leave_type?: 'normal' | 'emergency' | string | null;
  deduct_lesson?: boolean;
  emergency_quota?: number | null;
  used_emergency_count?: number | null;
  booking_no?: string | null;
  created_at?: string | null;
}

export function createLeaveRecord(data: LeaveRecordCreate) {
  return request.post<any, DataResponse<LeaveRecordResponse>>('/v1/leave-records', data);
}
