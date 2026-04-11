import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface StudentTeacherPreference {
    id: string
    student_id: string
    course_id: string | null
    min_teacher_level: number | null
    primary_teacher_id: string | null
    created_at?: string
    updated_at?: string
    student_name?: string
    course_name?: string
    primary_teacher_name?: string
}

export interface CreatePreferenceData {
    student_id: string
    course_id?: string | null
    min_teacher_level?: number | null
    primary_teacher_ids?: string[]
}

export interface UpdatePreferenceData {
    min_teacher_level?: number | null
    primary_teacher_id?: string | null
}

export interface AllowedTeacher {
    id: string
    teacher_no: string
    name: string
    teacher_level?: number
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const studentTeacherPreferencesApi = {
    async list(studentId: string): Promise<{ data: StudentTeacherPreference[] | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences?student_id=${studentId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得偏好設定失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreatePreferenceData): Promise<{ data: StudentTeacherPreference | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立偏好設定失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(preferenceId: string, data: UpdatePreferenceData): Promise<{ data: StudentTeacherPreference | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences/${preferenceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新偏好設定失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getAllowedTeachers(studentId: string): Promise<{ data: AllowedTeacher[] | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences/allowed-teachers?student_id=${studentId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得可預約教師失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getTeacherOptions(): Promise<{ data: AllowedTeacher[] | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences/options/teachers`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getCourseOptions(studentId: string): Promise<{ data: { id: string, course_name: string }[] | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences/options/courses?student_id=${studentId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得課程選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(preferenceId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-teacher-preferences/${preferenceId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除偏好設定失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
