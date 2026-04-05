import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface NotificationPreferences {
    email_enabled: boolean
    booking_confirmed: boolean
    booking_cancelled: boolean
    contract_activated: boolean
    contract_converted: boolean
    contract_terminated: boolean
}

export const notificationsApi = {
    async getPreferences(): Promise<{ data: NotificationPreferences | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/notifications/preferences`)
            if (!response.ok) {
                return { data: null, error: { message: '取得通知設定失敗' } }
            }
            const result = await response.json()
            return { data: result.data, error: null }
        } catch {
            return { data: null, error: { message: '網路錯誤' } }
        }
    },

    async updatePreferences(data: NotificationPreferences): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/notifications/preferences`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            if (!response.ok) {
                const err = await response.json()
                return { success: false, error: { message: err.detail || '更新失敗' } }
            }
            return { success: true, error: null }
        } catch {
            return { success: false, error: { message: '網路錯誤' } }
        }
    },
}
