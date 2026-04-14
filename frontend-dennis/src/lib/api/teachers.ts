import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export interface Teacher {
    id: string
    teacher_no: string
    name: string
    email: string
    phone?: string
    address?: string
    bio?: string
    avatar_url?: string
    teacher_level: number
    is_active: boolean
    email_verified_at?: string | null
    created_at?: string
    updated_at?: string
}

// ============================================
// Teacher Overview (總覽列表)
// ============================================
export interface TeacherOverviewItem {
    id: string; teacher_no: string; name: string
    email: string; phone?: string; teacher_level: number; is_active: boolean
    email_verified_at?: string; created_at?: string
    has_account: boolean; account_active?: boolean; role?: string
    line_bound: boolean; line_display_name?: string
    total_contracts: number; active_contracts: number
    total_bookings: number; completed_bookings: number; upcoming_bookings: number
    total_bonus: number; bonus_count: number
}

// ============================================
// Teacher View (綜合檢視)
// ============================================
export interface TeacherViewData {
    teacher: {
        id: string; teacher_no: string; name: string
        email: string; phone?: string; address?: string; bio?: string
        avatar_url?: string
        teacher_level: number; is_active: boolean; email_verified_at?: string
        created_at?: string
    }
    account: { has_account: boolean; is_active?: boolean; role?: string }
    line_binding: { bound: boolean; line_display_name?: string; line_picture_url?: string; binding_status?: string }
    contracts: {
        id: string; contract_no: string; contract_status: string
        start_date?: string; end_date?: string
        employment_type?: string; notes?: string; addendum_count: number
    }[]
    bookings_recent: {
        id: string; booking_date?: string; start_time?: string; end_time?: string
        booking_status: string; booking_type?: string
        student_name?: string; course_name?: string
    }[]
    bonus_records_recent: {
        id: string; bonus_type: string; amount: number
        bonus_date?: string; description?: string; student_name?: string
    }[]
    stats: {
        total_bookings: number; completed_bookings: number; cancelled_bookings: number
        pending_bookings: number; upcoming_bookings: number
        total_contracts: number; active_contracts: number
        total_bonus_amount: number; total_bonus_count: number; total_students_taught: number
    }
}

export interface TeacherListResponse {
    success: boolean
    data: Teacher[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateTeacherData {
    teacher_no?: string
    name: string
    email: string
    phone?: string
    address?: string
    bio?: string
    teacher_level?: number
    is_active?: boolean
}

export interface UpdateTeacherData {
    name?: string
    email?: string
    phone?: string
    address?: string
    bio?: string
    teacher_level?: number
    is_active?: boolean
}

export interface TeacherSelfUpdateData {
    bio?: string
    phone?: string
    address?: string
}

export const teachersApi = {
    list: (params?: { page?: number; per_page?: number; search?: string; is_active?: boolean }) =>
        apiGet<TeacherListResponse>(`/api/v1/teachers${qs(params || {})}`, '取得教師列表失敗', { extractData: false }),

    create: (data: CreateTeacherData) =>
        apiPost<Teacher>('/api/v1/teachers', data, '建立教師失敗'),

    update: (teacherId: string, data: UpdateTeacherData) =>
        apiPut<Teacher>(`/api/v1/teachers/${teacherId}`, data, '更新教師失敗'),

    updateSelf: (data: TeacherSelfUpdateData) =>
        apiPut<Teacher>('/api/v1/teachers/me', data, '更新個人資料失敗'),

    delete: (teacherId: string) =>
        apiDelete(`/api/v1/teachers/${teacherId}`, '刪除教師失敗'),

    listOverview: (params?: { page?: number; per_page?: number; search?: string; is_active?: boolean; has_account?: boolean; has_active_contract?: boolean; role?: string }) =>
        apiGet<{ data: TeacherOverviewItem[]; total: number; page: number; per_page: number; total_pages: number }>(
            `/api/v1/teachers/overview/list${qs(params || {})}`, '取得教師總覽失敗', { extractData: false }),

    getView: (teacherId: string) =>
        apiGet<TeacherViewData>(`/api/v1/teachers/${teacherId}/view`, '取得教師資訊失敗'),

    /** 頭像上傳（presigned URL 流程，無法用 apiPost 簡化） */
    async uploadAvatar(teacherId: string, file: File): Promise<{ data: Teacher | null, error: any }> {
        try {
            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}/avatar/upload-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_name: file.name }),
            })
            if (!urlRes.ok) {
                const err = await urlRes.json()
                return { data: null, error: { message: err.detail || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path, content_type } = await urlRes.json()

            const uploadRes = await fetch(upload_url, {
                method: 'PUT',
                headers: { 'Content-Type': content_type || file.type || 'application/octet-stream' },
                body: file,
            })
            if (!uploadRes.ok) return { data: null, error: { message: '頭像上傳失敗' } }

            const confirmRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}/avatar/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path, file_name: file.name }),
            })
            if (!confirmRes.ok) {
                const err = await confirmRes.json()
                return { data: null, error: { message: err.detail || '確認上傳失敗' } }
            }
            const result = await confirmRes.json()
            return { data: result.data || null, error: null }
        } catch {
            return { data: null, error: { message: '網路錯誤' } }
        }
    },
}
