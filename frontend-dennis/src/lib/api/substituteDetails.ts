import { apiGet, apiPost, apiDelete, qs } from './client'

export interface SubstituteDetail {
    id: string
    booking_id: string
    substitute_teacher_id: string
    substitute_contract_id: string
    substitute_hourly_rate?: number
    reason?: string
    approved_by?: string
    approved_at?: string
    created_at?: string
    updated_at?: string
    // 關聯資料
    substitute_teacher_name?: string
    booking_no?: string
    original_teacher_name?: string
}

export interface SubstituteDetailListResponse {
    success: boolean
    data: SubstituteDetail[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export const substituteDetailsApi = {
    create: (data: {
        booking_id: string
        substitute_teacher_id: string
        substitute_contract_id: string
        reason?: string
    }) =>
        apiPost<SubstituteDetail>('/api/v1/substitute-details', data, '指派代課失敗'),

    list: (params?: { page?: number; per_page?: number }) =>
        apiGet<SubstituteDetailListResponse>(`/api/v1/substitute-details${qs(params || {})}`, '取得代課紀錄失敗', { extractData: false }),

    delete: (subId: string) =>
        apiDelete(`/api/v1/substitute-details/${subId}`, '取消代課失敗'),
}
