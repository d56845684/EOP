import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete, apiAction, qs } from './client'

// ============================================
// Types
// ============================================

export type AccountTier = 'basic' | 'pro' | 'business'

export interface ZoomAccount {
    id: string
    account_name: string
    zoom_account_id: string
    zoom_client_id: string
    zoom_user_email?: string
    account_tier: AccountTier
    is_active: boolean
    daily_meeting_count: number
    daily_count_reset_at?: string
    notes?: string
    created_at?: string
    created_by?: string
    updated_at?: string
}

export interface ZoomAccountListResponse {
    success: boolean
    data: ZoomAccount[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface CreateZoomAccountData {
    account_name: string
    zoom_account_id: string
    zoom_client_id: string
    zoom_client_secret: string
    zoom_user_email?: string
    account_tier?: AccountTier
    is_active?: boolean
    notes?: string
}

export interface UpdateZoomAccountData {
    account_name?: string
    zoom_account_id?: string
    zoom_client_id?: string
    zoom_client_secret?: string
    zoom_user_email?: string
    account_tier?: AccountTier
    is_active?: boolean
    notes?: string
}

export interface ZoomMeetingLog {
    id: string
    booking_id: string
    zoom_account_id?: string
    teacher_id?: string
    zoom_meeting_id: string
    zoom_meeting_uuid?: string
    join_url: string
    start_url?: string
    passcode?: string
    meeting_date?: string
    start_time?: string
    end_time?: string
    meeting_status: string
    recording_url?: string
    recording_download_url?: string
    recording_file_type?: string
    recording_file_size_bytes?: number
    recording_duration_seconds?: number
    recording_completed_at?: string
    created_at?: string
    updated_at?: string
    account_name?: string
    teacher_name?: string
}

export interface ZoomMeetingLogListResponse {
    success: boolean
    data: ZoomMeetingLog[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface ZoomTeacherLinkStatus {
    success: boolean
    is_linked: boolean
    zoom_email?: string
    zoom_user_id?: string
    linked_at?: string
}

// ============================================
// API
// ============================================

export const zoomApi = {
    // --- 帳號池 CRUD ---

    listAccounts: (params?: { page?: number; per_page?: number; is_active?: boolean }) =>
        apiGet<ZoomAccountListResponse>(`/api/v1/zoom/accounts${qs(params || {})}`, '取得 Zoom 帳號列表失敗', { extractData: false }),

    createAccount: (data: CreateZoomAccountData) =>
        apiPost<ZoomAccount>('/api/v1/zoom/accounts', data, '新增 Zoom 帳號失敗'),

    updateAccount: (accountId: string, data: UpdateZoomAccountData) =>
        apiPut<ZoomAccount>(`/api/v1/zoom/accounts/${accountId}`, data, '更新 Zoom 帳號失敗'),

    deleteAccount: (accountId: string) =>
        apiDelete(`/api/v1/zoom/accounts/${accountId}`, '刪除 Zoom 帳號失敗'),

    testAccount: (accountId: string) =>
        apiAction('POST', `/api/v1/zoom/accounts/${accountId}/test`, undefined, '測試連線失敗'),

    // --- 會議操作 ---

    listMeetings: (params?: { page?: number; per_page?: number; meeting_status?: string; date_from?: string; date_to?: string }) =>
        apiGet<ZoomMeetingLogListResponse>(`/api/v1/zoom/meetings${qs(params || {})}`, '取得會議紀錄失敗', { extractData: false }),

    /** 特殊：404 視為 data=null 而非錯誤 */
    async getMeetingByBooking(bookingId: string): Promise<{ data: ZoomMeetingLog | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/zoom/meetings/${bookingId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                if (response.status === 404) {
                    return { data: null, error: null }
                }
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得會議資訊失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    createMeeting: (bookingId: string) =>
        apiPost<ZoomMeetingLog>('/api/v1/zoom/meetings/create', { booking_id: bookingId }, '建立 Zoom 會議失敗'),

    fetchRecording: (bookingId: string) =>
        apiPost<ZoomMeetingLog>(`/api/v1/zoom/meetings/${bookingId}/fetch-recording`, undefined, '取得錄影失敗'),

    // --- 教師 OAuth ---

    getOAuthStatus: () =>
        apiGet<ZoomTeacherLinkStatus>('/api/v1/zoom/oauth/status', '取得 Zoom 綁定狀態失敗', { extractData: false }),

    getOAuthUrl: () =>
        apiGet<{ authorize_url: string }>('/api/v1/zoom/oauth/authorize', '取得授權連結失敗', { extractData: false }),

    unlinkZoom: () =>
        apiDelete('/api/v1/zoom/oauth/unlink', '解除 Zoom 綁定失敗'),
}
