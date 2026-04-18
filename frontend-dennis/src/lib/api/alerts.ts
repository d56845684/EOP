import { apiGet, apiPut, qs } from './client'

export type AlertSeverity = 'info' | 'warning' | 'error'

export interface SystemAlert {
    id: string
    alert_type: string
    severity: AlertSeverity
    title: string
    message?: string
    metadata?: Record<string, unknown>
    is_read: boolean
    read_by?: string
    read_at?: string
    created_at: string
}

export interface AlertListResponse {
    success: boolean
    data: SystemAlert[]
    total: number
    page: number
    per_page: number
    total_pages: number
    unread_count: number
}

export const alertsApi = {
    list: (params?: { page?: number; per_page?: number; is_read?: boolean; severity?: string }) =>
        apiGet<AlertListResponse>(`/api/v1/alerts${qs(params || {})}`, '取得告警列表失敗', { extractData: false }),

    markRead: (alertId: string) =>
        apiPut(`/api/v1/alerts/${alertId}/read`, undefined, '標記已讀失敗', { extractData: false }),

    markAllRead: () =>
        apiPut('/api/v1/alerts/read-all', undefined, '標記全部已讀失敗', { extractData: false }),

    getUnreadCount: () =>
        apiGet<{ success: boolean; count: number }>('/api/v1/alerts/unread-count', '取得未讀數量失敗', { extractData: false }),
}
