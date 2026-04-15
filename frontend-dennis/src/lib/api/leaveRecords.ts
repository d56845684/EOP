import { apiGet, apiPost, qs } from './client'

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface LeaveRecord {
    id: string
    leave_no: string
    initiator_type: 'student' | 'teacher'
    initiator_student_id?: string
    initiator_teacher_id?: string
    booking_id?: string
    leave_date: string
    start_time?: string
    end_time?: string
    reason: string
    leave_status: LeaveStatus
    approver_id?: string
    approved_at?: string
    rejection_reason?: string
    created_at?: string
    updated_at?: string
    // 請假類型 + 扣堂
    leave_type?: 'normal' | 'emergency'
    deduct_lesson?: boolean
    emergency_quota?: number
    used_emergency_count?: number
    // 關聯資料
    initiator_name?: string
    booking_no?: string
    approver_name?: string
}

export interface LeaveRecordListResponse {
    success: boolean
    data: LeaveRecord[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export const leaveRecordsApi = {
    create: (data: { booking_id: string; reason: string }) =>
        apiPost<LeaveRecord>('/api/v1/leave-records', data, '建立請假申請失敗'),

    list: (params?: { page?: number; per_page?: number; leave_status?: LeaveStatus }) =>
        apiGet<LeaveRecordListResponse>(`/api/v1/leave-records${qs(params || {})}`, '取得請假紀錄失敗', { extractData: false }),

    approve: (leaveId: string) =>
        apiPost<LeaveRecord>(`/api/v1/leave-records/${leaveId}/approve`, undefined, '核准請假失敗'),

    reject: (leaveId: string, rejection_reason: string) =>
        apiPost<LeaveRecord>(`/api/v1/leave-records/${leaveId}/reject`, { rejection_reason }, '駁回請假失敗'),

    cancel: (leaveId: string) =>
        apiPost<LeaveRecord>(`/api/v1/leave-records/${leaveId}/cancel`, undefined, '撤回請假失敗'),
}
