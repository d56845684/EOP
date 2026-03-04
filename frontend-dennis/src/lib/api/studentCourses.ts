import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface StudentCourse {
    id: string
    student_id: string
    course_id: string
    course_code?: string
    course_name?: string
    student_name?: string
    enrolled_at?: string
    created_at?: string
}

export interface StudentCourseListResponse {
    success: boolean
    data: StudentCourse[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateStudentCourseData {
    student_id: string
    course_id: string
}

export interface StudentOption {
    id: string
    student_no: string
    name: string
}

export interface CourseOption {
    id: string
    course_code: string
    course_name: string
}

export const studentCoursesApi = {
    async list(params?: {
        page?: number
        per_page?: number
        student_id?: string
        search?: string
    }): Promise<{ data: StudentCourseListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.student_id) queryParams.set('student_id', params.student_id)
            if (params?.search) queryParams.set('search', params.search)

            const url = `${API_BASE_URL}/api/v1/student-courses${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetchWithAuth(url, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得學生選課列表失敗' } }
            }

            const result: StudentCourseListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getByStudent(studentId: string): Promise<{ data: StudentCourse[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-courses/by-student/${studentId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得學生選課失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateStudentCourseData): Promise<{ data: StudentCourse | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-courses`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '新增學生選課失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(enrollmentId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-courses/${enrollmentId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '移除學生選課失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getStudentOptions(): Promise<{ data: StudentOption[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-courses/options/students`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得學生選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getCourseOptions(): Promise<{ data: CourseOption[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-courses/options/courses`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得課程選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
