import { apiGet, apiAction } from './client'

export interface NotificationPreferences {
    email_enabled: boolean
    booking_confirmed: boolean
    booking_cancelled: boolean
    contract_activated: boolean
    contract_converted: boolean
    contract_terminated: boolean
}

export const notificationsApi = {
    getPreferences: () =>
        apiGet<NotificationPreferences>('/api/v1/notifications/preferences', '取得通知設定失敗'),

    updatePreferences: (data: NotificationPreferences) =>
        apiAction('PUT', '/api/v1/notifications/preferences', data, '更新失敗'),
}
