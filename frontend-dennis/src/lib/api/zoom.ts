const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// ============================================
// Types
// ============================================

export interface ZoomAccount {
    id: string
    account_name: string
    zoom_account_id: string
    zoom_client_id: string
    zoom_user_email?: string
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
    is_active?: boolean
    notes?: string
}

export interface UpdateZoomAccountData {
    account_name?: string
    zoom_account_id?: string
    zoom_client_id?: string
    zoom_client_secret?: string
    zoom_user_email?: string
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
// Helper
// ============================================

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

// ============================================
// API
// ============================================

export const zoomApi = {
    // --- 帳號池 CRUD ---

    async listAccounts(params?: {
        page?: number
        per_page?: number
        is_active?: boolean
    }): Promise<{ data: ZoomAccountListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.is_active !== undefined) queryParams.set('is_active', params.is_active.toString())

            const url = `${API_BASE_URL}/api/v1/zoom/accounts${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得 Zoom 帳號列表失敗' } }
            }

            const result: ZoomAccountListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async createAccount(data: CreateZoomAccountData): Promise<{ data: ZoomAccount | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/accounts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '新增 Zoom 帳號失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateAccount(accountId: string, data: UpdateZoomAccountData): Promise<{ data: ZoomAccount | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/accounts/${accountId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新 Zoom 帳號失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteAccount(accountId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/accounts/${accountId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除 Zoom 帳號失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async testAccount(accountId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/accounts/${accountId}/test`, {
                method: 'POST',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '測試連線失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // --- 會議操作 ---

    async listMeetings(params?: {
        page?: number
        per_page?: number
        meeting_status?: string
        date_from?: string
        date_to?: string
    }): Promise<{ data: ZoomMeetingLogListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.meeting_status) queryParams.set('meeting_status', params.meeting_status)
            if (params?.date_from) queryParams.set('date_from', params.date_from)
            if (params?.date_to) queryParams.set('date_to', params.date_to)

            const url = `${API_BASE_URL}/api/v1/zoom/meetings${queryParams.toString() ? '?' + queryParams.toString() : ''}`
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得會議紀錄失敗' } }
            }

            const result: ZoomMeetingLogListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getMeetingByBooking(bookingId: string): Promise<{ data: ZoomMeetingLog | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/meetings/${bookingId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                if (response.status === 404) {
                    return { data: null, error: null }
                }
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得會議資訊失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async createMeeting(bookingId: string): Promise<{ data: ZoomMeetingLog | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/meetings/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ booking_id: bookingId }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立 Zoom 會議失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // --- 教師 OAuth ---

    async getOAuthStatus(): Promise<{ data: ZoomTeacherLinkStatus | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/oauth/status`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得 Zoom 綁定狀態失敗' } }
            }

            const result: ZoomTeacherLinkStatus = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getOAuthUrl(): Promise<{ data: { authorize_url: string } | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/oauth/authorize`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得授權連結失敗' } }
            }

            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async unlinkZoom(): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/zoom/oauth/unlink`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '解除 Zoom 綁定失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
