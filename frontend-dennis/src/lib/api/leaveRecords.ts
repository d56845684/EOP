import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const leaveRecordsApi = {
    async create(data: { booking_id: string; reason: string }): Promise<{ data: LeaveRecord | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/leave-records`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立請假申請失敗' } }
            }
            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async list(params?: { page?: number; per_page?: number; leave_status?: LeaveStatus }): Promise<{ data: LeaveRecordListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.leave_status) queryParams.set('leave_status', params.leave_status)
            const url = `${API_BASE_URL}/api/v1/leave-records${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetchWithAuth(url, { method: 'GET' })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得請假紀錄失敗' } }
            }
            const result: LeaveRecordListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async approve(leaveId: string): Promise<{ data: LeaveRecord | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/leave-records/${leaveId}/approve`, {
                method: 'POST',
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '核准請假失敗' } }
            }
            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async reject(leaveId: string, rejection_reason: string): Promise<{ data: LeaveRecord | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/leave-records/${leaveId}/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rejection_reason }),
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '駁回請假失敗' } }
            }
            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async cancel(leaveId: string): Promise<{ data: LeaveRecord | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/leave-records/${leaveId}/cancel`, {
                method: 'POST',
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '撤回請假失敗' } }
            }
            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
