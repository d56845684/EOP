const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface Teacher {
    id: string
    teacher_no: string
    name: string
    email: string
    phone?: string
    address?: string
    bio?: string
    teacher_level: number
    is_active: boolean
    created_at?: string
    updated_at?: string
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
    teacher_no: string
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
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

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
            const response = await fetch(`${API_BASE_URL}/api/v1/teachers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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
            const response = await fetch(`${API_BASE_URL}/api/v1/teachers/${teacherId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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

    async delete(teacherId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teachers/${teacherId}`, {
                method: 'DELETE',
                credentials: 'include',
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
}
