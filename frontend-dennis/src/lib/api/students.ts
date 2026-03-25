import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface Student {
    id: string
    student_no: string
    name: string
    eng_name?: string
    email: string
    phone?: string
    address?: string
    birth_date?: string
    student_type?: 'formal' | 'trial'
    is_active: boolean
    email_verified_at?: string | null
    created_at?: string
    updated_at?: string
}

// ============================================
// Student Overview (總覽列表)
// ============================================
export interface StudentOverviewItem {
    id: string; student_no: string; name: string; eng_name?: string
    email: string; phone?: string; student_type?: string; is_active: boolean
    email_verified_at?: string; created_at?: string
    has_account: boolean; account_active?: boolean; role?: string
    line_bound: boolean; line_display_name?: string
    total_contracts: number; active_contracts: number; remaining_lessons: number
    total_bookings: number; completed_bookings: number; upcoming_bookings: number
}

// ============================================
// Student View (綜合檢視)
// ============================================
export interface StudentViewData {
    student: {
        id: string; student_no: string; name: string; eng_name?: string
        email: string; phone?: string; address?: string; birth_date?: string
        student_type?: string; is_active: boolean; email_verified_at?: string
        created_at?: string
    }
    account: { has_account: boolean; is_active?: boolean; role?: string }
    line_binding: { bound: boolean; line_display_name?: string; line_picture_url?: string; binding_status?: string }
    contracts: {
        id: string; contract_no: string; contract_status: string
        start_date?: string; end_date?: string
        total_lessons: number; remaining_lessons: number; total_amount?: number
        total_leave_allowed: number; used_leave_count: number; used_emergency_leave_count: number
        is_recurring: boolean; teachers: string[]; addendum_count: number
    }[]
    bookings_recent: {
        id: string; booking_date?: string; start_time?: string; end_time?: string
        booking_status: string; booking_type?: string
        teacher_name?: string; course_name?: string
    }[]
    courses: { id: string; course_id: string; course_name?: string; course_code?: string; enrolled_at?: string }[]
    teacher_preferences: { id: string; course_name?: string; min_teacher_level?: number; primary_teacher_name?: string }[]
    leave_records_recent: { id: string; leave_date?: string; leave_status: string; leave_type?: string; reason?: string; booking_date?: string }[]
    stats: {
        total_bookings: number; completed_bookings: number; cancelled_bookings: number
        pending_bookings: number; upcoming_bookings: number
        total_contracts: number; active_contracts: number
        total_remaining_lessons: number; total_leaves_used: number; total_courses_enrolled: number
    }
}

export interface StudentListResponse {
    success: boolean
    data: Student[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateStudentData {
    student_no: string
    name: string
    eng_name?: string
    email: string
    phone?: string
    address?: string
    birth_date?: string
    student_type?: string
    is_active?: boolean
}

export interface UpdateStudentData {
    name?: string
    eng_name?: string
    email?: string
    phone?: string
    address?: string
    birth_date?: string
    student_type?: string
    is_active?: boolean
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export interface ConvertToFormalData {
    contract_no: string
    total_lessons: number
    total_amount: number
    start_date: string
    end_date: string
    teacher_id?: string
    booking_id?: string
    notes?: string
}

export interface ConvertToFormalResponse {
    success: boolean
    message: string
    student: Student
    contract: {
        id: string
        contract_no: string
        student_id: string
        contract_status: string
        start_date: string
        end_date: string
        total_lessons: number
        remaining_lessons: number
        notes?: string
        created_at?: string
    }
    bonus_recorded: boolean
    bonus_amount?: number
}

export const studentsApi = {
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        is_active?: boolean
        student_type?: string
    }): Promise<{ data: StudentListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.search) queryParams.set('search', params.search)
            if (params?.is_active !== undefined) queryParams.set('is_active', params.is_active.toString())
            if (params?.student_type) queryParams.set('student_type', params.student_type)

            const url = `${API_BASE_URL}/api/v1/students${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetchWithAuth(url, { method: 'GET' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生列表失敗' } }
            }

            const result: StudentListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateStudentData): Promise<{ data: Student | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立學生失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(studentId: string, data: UpdateStudentData): Promise<{ data: Student | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students/${studentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新學生失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(studentId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students/${studentId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除學生失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async convertToFormal(studentId: string, data: ConvertToFormalData): Promise<{ data: ConvertToFormalResponse | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students/${studentId}/convert-to-formal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '試上轉正失敗' } }
            }

            const result: ConvertToFormalResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async listOverview(params?: {
        page?: number; per_page?: number; search?: string
        student_type?: string; is_active?: boolean
        has_account?: boolean; has_active_contract?: boolean
        role?: string
    }): Promise<{ data: { data: StudentOverviewItem[]; total: number; page: number; per_page: number; total_pages: number } | null, error: any }> {
        try {
            const sp = new URLSearchParams()
            if (params?.page) sp.set('page', String(params.page))
            if (params?.per_page) sp.set('per_page', String(params.per_page))
            if (params?.search) sp.set('search', params.search)
            if (params?.student_type) sp.set('student_type', params.student_type)
            if (params?.is_active !== undefined) sp.set('is_active', String(params.is_active))
            if (params?.has_account !== undefined) sp.set('has_account', String(params.has_account))
            if (params?.has_active_contract !== undefined) sp.set('has_active_contract', String(params.has_active_contract))
            if (params?.role) sp.set('role', params.role)
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students/overview/list?${sp}`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生總覽失敗' } }
            }
            return { data: await response.json(), error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getView(studentId: string): Promise<{ data: StudentViewData | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/students/${studentId}/view`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生資訊失敗' } }
            }
            const result = await response.json()
            return { data: result.data, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
