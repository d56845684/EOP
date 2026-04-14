import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export type BonusType = 'trial_completed' | 'trial_to_formal' | 'performance' | 'substitute' | 'referral' | 'other'

export const BONUS_TYPE_LABELS: Record<BonusType, string> = {
    trial_completed: '試上完成',
    trial_to_formal: '試上轉正',
    performance: '績效獎金',
    substitute: '代課獎金',
    referral: '推薦獎金',
    other: '其他',
}

export interface TeacherBonus {
    id: string
    teacher_id: string
    bonus_type: BonusType
    amount: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
    created_at?: string
    created_by?: string
    updated_at?: string
    teacher_name?: string
    student_name?: string
}

export interface TeacherBonusListResponse {
    success: boolean
    data: TeacherBonus[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateTeacherBonusData {
    teacher_id: string
    bonus_type: BonusType
    amount: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
}

export interface UpdateTeacherBonusData {
    bonus_type?: BonusType
    amount?: number
    bonus_date?: string
    description?: string
    related_student_id?: string
    related_booking_id?: string
    notes?: string
}

export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
}

export const teacherBonusApi = {
    list: (params?: {
        page?: number
        per_page?: number
        teacher_id?: string
        bonus_type?: BonusType
        date_from?: string
        date_to?: string
    }) =>
        apiGet<TeacherBonusListResponse>(`/api/v1/teacher-bonus${qs(params || {})}`, '取得教師獎金列表失敗', { extractData: false }),

    create: (data: CreateTeacherBonusData) =>
        apiPost<TeacherBonus>('/api/v1/teacher-bonus', data, '新增教師獎金失敗'),

    update: (bonusId: string, data: UpdateTeacherBonusData) =>
        apiPut<TeacherBonus>(`/api/v1/teacher-bonus/${bonusId}`, data, '更新教師獎金失敗'),

    delete: (bonusId: string) =>
        apiDelete(`/api/v1/teacher-bonus/${bonusId}`, '刪除教師獎金失敗'),

    getTeacherOptions: () =>
        apiGet<TeacherOption[]>('/api/v1/teacher-bonus/options/teachers', '取得教師選項失敗'),
}
