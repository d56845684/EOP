import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const substituteDetailsApi = {
    async create(data: {
        booking_id: string
        substitute_teacher_id: string
        substitute_contract_id: string
        reason?: string
    }): Promise<{ data: SubstituteDetail | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/substitute-details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '指派代課失敗' } }
            }
            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async list(params?: { page?: number; per_page?: number }): Promise<{ data: SubstituteDetailListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            const url = `${API_BASE_URL}/api/v1/substitute-details${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetchWithAuth(url, { method: 'GET' })
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得代課紀錄失敗' } }
            }
            const result: SubstituteDetailListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(subId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/substitute-details/${subId}`, {
                method: 'DELETE',
            })
            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '取消代課失敗' } }
            }
            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
