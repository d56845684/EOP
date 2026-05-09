import { apiGet, apiPost, apiPut, apiAction, apiDelete, qs } from './client'

export type BookingStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled'

export interface Booking {
    id: string
    booking_no: string
    student_id: string
    teacher_id: string
    course_id: string
    student_contract_id: string
    teacher_contract_id: string
    teacher_slot_id: string
    substitute_detail_id?: string | null
    teacher_hourly_rate: number
    teacher_rate_percentage?: number
    booking_status: BookingStatus
    booking_type?: 'trial' | 'regular'
    is_trial_to_formal?: boolean
    is_overtime?: boolean | null
    regular_lessons?: number | null
    overtime_lessons?: number | null
    overtime_pay?: number | null
    booking_date: string
    start_time: string
    end_time: string
    notes?: string
    meeting_creation_error?: string | null
    created_at?: string
    updated_at?: string
    // 關聯資料
    student_name?: string
    student_no?: string
    student_eng_name?: string
    teacher_name?: string
    course_name?: string
    student_contract_no?: string
    teacher_contract_no?: string
    substitute_teacher_name?: string | null
    has_pending_leave?: boolean
    pending_leave_initiator_type?: 'student' | 'teacher' | null
}

export interface BookingListResponse {
    success: boolean
    data: Booking[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface BookingResponse {
    success: boolean
    message: string
    data?: Booking
}

export interface CreateBookingData {
    student_id: string
    teacher_id: string
    course_id: string
    student_contract_id?: string  // 試上學生可不提供
    teacher_contract_id?: string
    teacher_slot_id?: string  // 可選，不提供則系統自動尋找符合時間的時段
    booking_date: string
    start_time: string
    end_time: string
    notes?: string
}

export interface UpdateBookingData {
    booking_status?: BookingStatus
    notes?: string
}

// 批次操作介面
export interface BatchUpdateByIdsData {
    booking_ids: string[]
    booking_status: BookingStatus
    notes?: string
}

export interface BatchUpdateResult {
    updated_count: number
    updated_booking_ids: string[]
    meeting_failed_ids: string[]
    meeting_failed_reasons: Record<string, string>
    skipped_ids: string[]
}

export interface BatchDeleteByIdsData {
    booking_ids: string[]
}

export interface BatchUpdateData {
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    student_id?: string
    teacher_id?: string
    course_id?: string
    filter_status?: BookingStatus
    new_status: BookingStatus
    notes?: string
}

export interface BatchDeleteData {
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    student_id?: string
    teacher_id?: string
    course_id?: string
    filter_status?: BookingStatus
}

export interface BatchCreateData {
    student_id: string
    student_contract_id?: string  // 試上學生可不提供
    course_id?: string  // 試上學生無合約時必填
    teacher_id: string
    teacher_contract_id?: string
    start_date: string
    end_date: string
    weekdays: number[]  // 0=Monday, 6=Sunday
    start_time?: string
    end_time?: string
    notes?: string
}

// 下拉選單選項介面
export interface StudentOption {
    id: string
    student_no: string
    name: string
    student_type?: 'formal' | 'trial'
}

export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
    teacher_level?: number
    is_primary?: boolean
}

export interface CourseOption {
    id: string
    course_code: string
    course_name: string
}

export interface StudentContractOption {
    id: string
    contract_no: string
    course_id: string
    course_ids?: string[]
    course_name?: string
    remaining_lessons: number
}

export interface TeacherContractOption {
    id: string
    contract_no: string
}

export interface SubstituteTeacherOption {
    id: string
    teacher_no: string
    name: string
    teacher_level?: number
    is_preferred: boolean
}

export interface TeacherSlotOption {
    id: string
    slot_date: string
    start_time: string
    end_time: string
    teacher_contract_id: string
    is_booked?: boolean
}

// 30 分鐘時間區塊
export interface TimeBlock {
    start_time: string
    end_time: string
    is_available: boolean
    booking_id?: string | null
}

export interface SlotAvailabilityResponse {
    slot_id: string
    slot_date: string
    slot_start_time: string
    slot_end_time: string
    blocks: TimeBlock[]
}

export const bookingsApi = {
    list: (params?: {
        page?: number
        per_page?: number
        search?: string
        booking_status?: BookingStatus
        student_id?: string
        teacher_id?: string
        course_id?: string
        date_from?: string
        date_to?: string
    }) =>
        apiGet<BookingListResponse>(`/api/v1/bookings${qs(params || {})}`, '取得預約列表失敗', { extractData: false }),

    get: (bookingId: string) =>
        apiGet<Booking>(`/api/v1/bookings/${bookingId}`, '取得預約失敗'),

    create: (data: CreateBookingData) =>
        apiPost<Booking>('/api/v1/bookings', data, '建立預約失敗'),

    update: (bookingId: string, data: UpdateBookingData) =>
        apiPut<Booking>(`/api/v1/bookings/${bookingId}`, data, '更新預約失敗'),

    delete: (bookingId: string) =>
        apiDelete(`/api/v1/bookings/${bookingId}`, '刪除預約失敗'),

    // 批次操作 API
    createBatch: (data: BatchCreateData) =>
        apiAction('POST', '/api/v1/bookings/batch', data, '批次建立預約失敗'),

    updateByIds: (data: BatchUpdateByIdsData) =>
        apiPost<BatchUpdateResult>('/api/v1/bookings/batch-by-ids/update', data, '批次更新預約失敗'),

    deleteByIds: (data: BatchDeleteByIdsData) =>
        apiAction('POST', '/api/v1/bookings/batch-by-ids/delete', data, '批次刪除預約失敗'),

    updateBatch: (data: BatchUpdateData) =>
        apiAction('PUT', '/api/v1/bookings/batch', data, '批次更新預約失敗'),

    deleteBatch: (data: BatchDeleteData) =>
        apiAction('DELETE', '/api/v1/bookings/batch', data, '批次刪除預約失敗'),

    // 取得下拉選單選項
    getStudentOptions: () =>
        apiGet<StudentOption[]>('/api/v1/bookings/options/students', '取得學生選項失敗'),

    getTeacherOptions: (params?: { student_id?: string; course_id?: string }) =>
        apiGet<TeacherOption[]>(`/api/v1/bookings/options/teachers${qs(params || {})}`, '取得教師選項失敗'),

    getOverlappingCourseOptions: (studentId: string, teacherId: string) =>
        apiGet<CourseOption[]>(`/api/v1/bookings/options/overlapping-courses${qs({ student_id: studentId, teacher_id: teacherId })}`, '取得交集課程選項失敗'),

    getCourseOptions: () =>
        apiGet<CourseOption[]>('/api/v1/bookings/options/courses', '取得課程選項失敗'),

    getStudentContractOptions: (studentId: string) =>
        apiGet<StudentContractOption[]>(`/api/v1/bookings/options/student-contracts/${studentId}`, '取得學生合約選項失敗'),

    getTeacherContractOptions: (teacherId: string) =>
        apiGet<TeacherContractOption[]>(`/api/v1/bookings/options/teacher-contracts/${teacherId}`, '取得教師合約選項失敗'),

    getTeacherSlotOptions: (teacherId: string, dateFrom?: string, dateTo?: string) =>
        apiGet<TeacherSlotOption[]>(`/api/v1/bookings/options/teacher-slots/${teacherId}${qs({ date_from: dateFrom, date_to: dateTo })}`, '取得教師時段選項失敗'),

    // 取得當前學生的資料（學生用）
    getMyStudentInfo: () =>
        apiGet<StudentOption>('/api/v1/bookings/my-student-info', '取得學生資料失敗'),

    // 取得時段的 30 分鐘區塊可用狀態
    getSlotAvailability: (slotId: string) =>
        apiGet<SlotAvailabilityResponse>(`/api/v1/bookings/slot-availability/${slotId}`, '取得時段可用狀態失敗'),

    // 取得可用代課教師選項
    getSubstituteTeacherOptions: (bookingId: string) =>
        apiGet<SubstituteTeacherOption[]>(`/api/v1/bookings/options/substitute-teachers${qs({ booking_id: bookingId })}`, '取得代課教師選項失敗'),

    // 取得當前學生的合約（學生用）
    getMyContracts: () =>
        apiGet<StudentContractOption[]>('/api/v1/bookings/my-contracts', '取得學生合約選項失敗'),
}
