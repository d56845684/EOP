const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export type BonusType = 'trial_to_formal' | 'performance' | 'substitute' | 'referral' | 'other'

export const BONUS_TYPE_LABELS: Record<BonusType, string> = {
    trial_to_formal: '試上轉正',
    performance: '績效獎金',
    substitute: '代課獎金',
    referral: '推薦獎金',
    other: '其他',
}

export interface TeacherBonus {
    id: string
    teacher_id: string
    bonus_type: BonusType
    amount: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
    created_at?: string
    created_by?: string
    updated_at?: string
    teacher_name?: string
    student_name?: string
}

export interface TeacherBonusListResponse {
    success: boolean
    data: TeacherBonus[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateTeacherBonusData {
    teacher_id: string
    bonus_type: BonusType
    amount: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
}

export interface UpdateTeacherBonusData {
    bonus_type?: BonusType
    amount?: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
}

export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const teacherBonusApi = {
    async list(params?: {
        page?: number
        per_page?: number
        teacher_id?: string
        bonus_type?: BonusType
        date_from?: string
        date_to?: string
    }): Promise<{ data: TeacherBonusListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.teacher_id) queryParams.set('teacher_id', params.teacher_id)
            if (params?.bonus_type) queryParams.set('bonus_type', params.bonus_type)
            if (params?.date_from) queryParams.set('date_from', params.date_from)
            if (params?.date_to) queryParams.set('date_to', params.date_to)

            const url = `${API_BASE_URL}/api/v1/teacher-bonus${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師獎金列表失敗' } }
            }

            const result: TeacherBonusListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateTeacherBonusData): Promise<{ data: TeacherBonus | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-bonus`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '新增教師獎金失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(bonusId: string, data: UpdateTeacherBonusData): Promise<{ data: TeacherBonus | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-bonus/${bonusId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新教師獎金失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(bonusId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-bonus/${bonusId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除教師獎金失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getTeacherOptions(): Promise<{ data: TeacherOption[], error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-bonus/options/teachers`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: parseErrorDetail(error.detail) || '取得教師選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
