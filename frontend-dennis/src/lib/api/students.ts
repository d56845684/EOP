import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export interface Student {
    id: string
    student_no: string
    name: string
    eng_name?: string
    email: string
    phone?: string
    address?: string
    birth_date?: string
    id_number?: string
    student_type?: 'formal' | 'trial'
    student_status?: 'trial' | 'pending' | 'active' | 'suspended' | 'terminated' | 'extended' | 'completed'
    is_active: boolean
    google_drive_folder_id?: string
    email_verified_at?: string | null
    created_at?: string
    updated_at?: string
}

// ============================================
// Student Overview (總覽列表)
// ============================================
export interface StudentOverviewItem {
    id: string; student_no: string; name: string; eng_name?: string
    email: string; phone?: string; student_type?: string; student_status?: string; is_active: boolean
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
    student_no?: string
    name: string
    eng_name?: string
    email: string
    phone?: string
    address?: string
    birth_date?: string
    id_number?: string
    student_type?: string
    is_active?: boolean
    google_drive_folder_id?: string
}

export interface UpdateStudentData {
    name?: string
    eng_name?: string
    email?: string
    phone?: string
    address?: string
    birth_date?: string
    id_number?: string
    student_type?: string
    is_active?: boolean
    google_drive_folder_id?: string
}

export interface ConvertToFormalData {
    student_contract_id: string
    teacher_id?: string
    booking_id?: string
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
    bonus_error?: string
}

export const studentsApi = {
    list: (params?: { page?: number; per_page?: number; search?: string; is_active?: boolean; student_type?: string }) =>
        apiGet<StudentListResponse>(`/api/v1/students${qs(params || {})}`, '取得學生列表失敗', { extractData: false }),

    create: (data: CreateStudentData) =>
        apiPost<Student>('/api/v1/students', data, '建立學生失敗'),

    update: (studentId: string, data: UpdateStudentData) =>
        apiPut<Student>(`/api/v1/students/${studentId}`, data, '更新學生失敗'),

    delete: (studentId: string) =>
        apiDelete(`/api/v1/students/${studentId}`, '刪除學生失敗'),

    convertToFormal: (studentId: string, data: ConvertToFormalData) =>
        apiPost<ConvertToFormalResponse>(`/api/v1/students/${studentId}/convert-to-formal`, data, '試上轉正失敗', { extractData: false }),

    listOverview: (params?: { page?: number; per_page?: number; search?: string; student_type?: string; is_active?: boolean; has_account?: boolean; has_active_contract?: boolean; role?: string }) =>
        apiGet<{ data: StudentOverviewItem[]; total: number; page: number; per_page: number; total_pages: number }>(
            `/api/v1/students/overview/list${qs(params || {})}`, '取得學生總覽失敗', { extractData: false }),

    getView: (studentId: string) =>
        apiGet<StudentViewData>(`/api/v1/students/${studentId}/view`, '取得學生資訊失敗'),
}
