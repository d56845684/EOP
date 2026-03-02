const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface Student {
    id: string
    student_no: string
    name: string
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
    email: string
    phone?: string
    address?: string
    birth_date?: string
    student_type?: string
    is_active?: boolean
}

export interface UpdateStudentData {
    name?: string
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
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

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
            const response = await fetch(`${API_BASE_URL}/api/v1/students`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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
            const response = await fetch(`${API_BASE_URL}/api/v1/students/${studentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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
            const response = await fetch(`${API_BASE_URL}/api/v1/students/${studentId}`, {
                method: 'DELETE',
                credentials: 'include',
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
}
