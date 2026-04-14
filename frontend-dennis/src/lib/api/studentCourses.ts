import { apiGet, apiPost, apiDelete, qs } from './client'

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
    list: (params?: { page?: number; per_page?: number; student_id?: string; search?: string }) =>
        apiGet<StudentCourseListResponse>(`/api/v1/student-courses${qs(params || {})}`, '取得學生選課列表失敗', { extractData: false }),

    getByStudent: (studentId: string) =>
        apiGet<StudentCourse[]>(`/api/v1/student-courses/by-student/${studentId}`, '取得學生選課失敗'),

    create: (data: CreateStudentCourseData) =>
        apiPost<StudentCourse>('/api/v1/student-courses', data, '新增學生選課失敗'),

    delete: (enrollmentId: string) =>
        apiDelete(`/api/v1/student-courses/${enrollmentId}`, '移除學生選課失敗'),

    getStudentOptions: () =>
        apiGet<StudentOption[]>('/api/v1/student-courses/options/students', '取得學生選項失敗'),

    getCourseOptions: () =>
        apiGet<CourseOption[]>('/api/v1/student-courses/options/courses', '取得課程選項失敗'),
}
