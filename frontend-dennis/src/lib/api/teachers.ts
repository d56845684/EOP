import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const teachersApi = {
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        is_active?: boolean
    }): Promise<{ data: TeacherListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.search) queryParams.set('search', params.search)
            if (params?.is_active !== undefined) queryParams.set('is_active', params.is_active.toString())

            const url = `${API_BASE_URL}/api/v1/teachers${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetchWithAuth(url, { method: 'GET' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師列表失敗' } }
            }

            const result: TeacherListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateTeacherData): Promise<{ data: Teacher | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立教師失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(teacherId: string, data: UpdateTeacherData): Promise<{ data: Teacher | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新教師失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateSelf(data: TeacherSelfUpdateData): Promise<{ data: Teacher | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/me`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新個人資料失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(teacherId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除教師失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async uploadAvatar(teacherId: string, file: File): Promise<{ data: Teacher | null, error: any }> {
        try {
            const fileExt = file.name.split('.').pop()?.toLowerCase() || 'jpg'

            // 1. 取得 presigned URL
            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}/avatar/upload-url?file_ext=${fileExt}`, {
                method: 'POST',
            })
            if (!urlRes.ok) {
                const error = await urlRes.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path } = await urlRes.json()

            // 2. PUT 到 S3
            const uploadRes = await fetch(upload_url, {
                method: 'PUT',
                headers: { 'Content-Type': file.type || 'application/octet-stream' },
                body: file,
            })
            if (!uploadRes.ok) {
                return { data: null, error: { message: '頭像上傳失敗' } }
            }

            // 3. 確認上傳
            const confirmRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}/avatar/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path, file_name: file.name }),
            })
            if (!confirmRes.ok) {
                const error = await confirmRes.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '確認上傳失敗' } }
            }
            const result = await confirmRes.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤' } }
        }
    },

    async listOverview(params?: {
        page?: number; per_page?: number; search?: string
        is_active?: boolean; has_account?: boolean
        has_active_contract?: boolean; role?: string
    }): Promise<{ data: { data: TeacherOverviewItem[]; total: number; page: number; per_page: number; total_pages: number } | null, error: any }> {
        try {
            const sp = new URLSearchParams()
            if (params?.page) sp.set('page', String(params.page))
            if (params?.per_page) sp.set('per_page', String(params.per_page))
            if (params?.search) sp.set('search', params.search)
            if (params?.is_active !== undefined) sp.set('is_active', String(params.is_active))
            if (params?.has_account !== undefined) sp.set('has_account', String(params.has_account))
            if (params?.has_active_contract !== undefined) sp.set('has_active_contract', String(params.has_active_contract))
            if (params?.role) sp.set('role', params.role)
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/overview/list?${sp}`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師總覽失敗' } }
            }
            return { data: await response.json(), error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getView(teacherId: string): Promise<{ data: TeacherViewData | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teachers/${teacherId}/view`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師資訊失敗' } }
            }
            const result = await response.json()
            return { data: result.data, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
