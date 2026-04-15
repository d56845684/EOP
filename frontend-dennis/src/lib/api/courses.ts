import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export interface Course {
    id: string
    course_code: string
    course_name: string
    description?: string
    duration_minutes: number
    is_active: boolean
    created_at?: string
    updated_at?: string
}

export interface CourseListResponse {
    success: boolean
    data: Course[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateCourseData {
    course_code: string
    course_name: string
    description?: string
    duration_minutes?: number
    is_active?: boolean
}

export interface UpdateCourseData {
    course_code?: string
    course_name?: string
    description?: string
    duration_minutes?: number
    is_active?: boolean
}

export const coursesApi = {
    list: (params?: { page?: number; per_page?: number; search?: string; is_active?: boolean }) =>
        apiGet<CourseListResponse>(`/api/v1/courses${qs(params || {})}`, '取得課程列表失敗', { extractData: false }),

    get: (courseId: string) =>
        apiGet<Course>(`/api/v1/courses/${courseId}`, '取得課程失敗'),

    create: (data: CreateCourseData) =>
        apiPost<Course>('/api/v1/courses', data, '建立課程失敗'),

    update: (courseId: string, data: UpdateCourseData) =>
        apiPut<Course>(`/api/v1/courses/${courseId}`, data, '更新課程失敗'),

    delete: (courseId: string) =>
        apiDelete(`/api/v1/courses/${courseId}`, '刪除課程失敗'),
}
