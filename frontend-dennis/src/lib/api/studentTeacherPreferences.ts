import { apiGet, apiPost, apiPut, apiDelete } from './client'

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

export const studentTeacherPreferencesApi = {
    list: (studentId: string) =>
        apiGet<StudentTeacherPreference[]>(`/api/v1/student-teacher-preferences?student_id=${studentId}`, '取得偏好設定失敗'),

    create: (data: CreatePreferenceData) =>
        apiPost<StudentTeacherPreference>('/api/v1/student-teacher-preferences', data, '建立偏好設定失敗'),

    update: (preferenceId: string, data: UpdatePreferenceData) =>
        apiPut<StudentTeacherPreference>(`/api/v1/student-teacher-preferences/${preferenceId}`, data, '更新偏好設定失敗'),

    getAllowedTeachers: (studentId: string) =>
        apiGet<AllowedTeacher[]>(`/api/v1/student-teacher-preferences/allowed-teachers?student_id=${studentId}`, '取得可預約教師失敗'),

    getTeacherOptions: () =>
        apiGet<AllowedTeacher[]>('/api/v1/student-teacher-preferences/options/teachers', '取得教師選項失敗'),

    getCourseOptions: (studentId: string) =>
        apiGet<{ id: string; course_name: string }[]>(`/api/v1/student-teacher-preferences/options/courses?student_id=${studentId}`, '取得課程選項失敗'),

    delete: (preferenceId: string) =>
        apiDelete(`/api/v1/student-teacher-preferences/${preferenceId}`, '刪除偏好設定失敗'),
}
