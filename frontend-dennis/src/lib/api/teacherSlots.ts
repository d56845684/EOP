import { apiGet, apiPost, apiPut, apiAction, apiDelete, qs } from './client'

export interface TeacherSlot {
    id: string
    teacher_id: string
    teacher_contract_id?: string
    slot_date: string
    start_time: string
    end_time: string
    is_available: boolean
    is_booked: boolean
    booking_count?: number
    notes?: string
    created_at?: string
    updated_at?: string
    // 關聯資料
    teacher_name?: string
    teacher_no?: string
    teacher_contract_no?: string
}

export interface TeacherSlotListResponse {
    success: boolean
    data: TeacherSlot[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface TeacherSlotResponse {
    success: boolean
    message: string
    data?: TeacherSlot
}

export interface CreateTeacherSlotData {
    teacher_id: string
    teacher_contract_id?: string
    slot_date: string
    start_time: string
    end_time: string
    is_available?: boolean
    notes?: string
}

export interface BatchCreateTeacherSlotData {
    teacher_id: string
    teacher_contract_id?: string
    start_date: string
    end_date: string
    weekdays: number[]  // 0=Monday, 6=Sunday
    start_time: string
    end_time: string
    notes?: string
}

export interface BatchDeleteTeacherSlotData {
    teacher_id: string
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    start_time?: string
    end_time?: string
}

export interface BatchUpdateTeacherSlotData {
    // 篩選條件
    teacher_id: string
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    filter_start_time?: string
    filter_end_time?: string
    // 更新內容
    new_start_time?: string
    new_end_time?: string
    is_available?: boolean
    notes?: string
}

export interface BatchDeleteByIdsData {
    slot_ids: string[]
}

export interface BatchUpdateByIdsData {
    slot_ids: string[]
    new_start_time?: string
    new_end_time?: string
    is_available?: boolean
    notes?: string
}

export interface UpdateTeacherSlotData {
    teacher_contract_id?: string
    slot_date?: string
    start_time?: string
    end_time?: string
    is_available?: boolean
    notes?: string
}

// 下拉選單選項介面
export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
    teacher_level?: number
}

export interface TeacherContractOption {
    id: string
    contract_no: string
}

export const teacherSlotsApi = {
    list: (params?: {
        page?: number
        per_page?: number
        teacher_id?: string
        date_from?: string
        date_to?: string
        is_available?: boolean
        is_booked?: boolean
    }) =>
        apiGet<TeacherSlotListResponse>(`/api/v1/teacher-slots${qs(params || {})}`, '取得教師時段列表失敗', { extractData: false }),

    get: (slotId: string) =>
        apiGet<TeacherSlot>(`/api/v1/teacher-slots/${slotId}`, '取得教師時段失敗'),

    create: (data: CreateTeacherSlotData) =>
        apiPost<TeacherSlot>('/api/v1/teacher-slots', data, '建立教師時段失敗'),

    createBatch: (data: BatchCreateTeacherSlotData) =>
        apiAction('POST', '/api/v1/teacher-slots/batch', data, '批次建立教師時段失敗'),

    deleteBatch: (data: BatchDeleteTeacherSlotData) =>
        apiAction('DELETE', '/api/v1/teacher-slots/batch', data, '批次刪除教師時段失敗'),

    updateBatch: (data: BatchUpdateTeacherSlotData) =>
        apiAction('PUT', '/api/v1/teacher-slots/batch', data, '批次更新教師時段失敗'),

    deleteByIds: (data: BatchDeleteByIdsData) =>
        apiAction('POST', '/api/v1/teacher-slots/batch-by-ids/delete', data, '批次刪除教師時段失敗'),

    updateByIds: (data: BatchUpdateByIdsData) =>
        apiAction('POST', '/api/v1/teacher-slots/batch-by-ids/update', data, '批次更新教師時段失敗'),

    update: (slotId: string, data: UpdateTeacherSlotData) =>
        apiPut<TeacherSlot>(`/api/v1/teacher-slots/${slotId}`, data, '更新教師時段失敗'),

    delete: (slotId: string) =>
        apiDelete(`/api/v1/teacher-slots/${slotId}`, '刪除教師時段失敗'),

    // 取得下拉選單選項（僅限員工）
    getTeacherOptions: () =>
        apiGet<TeacherOption[]>('/api/v1/teacher-slots/options/teachers', '取得教師選項失敗'),

    // 取得當前教師的合約
    getMyContracts: () =>
        apiGet<TeacherContractOption[]>('/api/v1/teacher-slots/my-contracts', '取得教師合約選項失敗'),
}
