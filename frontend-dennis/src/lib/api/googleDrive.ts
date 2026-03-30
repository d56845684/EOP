import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

function parseErrorDetail(detail: any): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(d => d.msg || d.message || JSON.stringify(d)).join(', ')
    return JSON.stringify(detail)
}

export interface GoogleDriveStatus {
    is_linked: boolean
    drive_mode: string | null
    google_email: string | null
    drive_folder_id: string | null
    linked_at: string | null
}

export const googleDriveApi = {
    async getStatus(): Promise<{ data: GoogleDriveStatus | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/google-drive/oauth/status`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得狀態失敗' } }
            }
            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤' } }
        }
    },

    async getAuthorizeUrl(): Promise<{ data: { authorize_url: string } | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/google-drive/oauth/authorize`)
            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得授權 URL 失敗' } }
            }
            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤' } }
        }
    },

    async unlink(): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/google-drive/oauth/unlink`, {
                method: 'DELETE',
            })
            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '解除綁定失敗' } }
            }
            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤' } }
        }
    },

    async updateFolder(folderId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(
                `${API_BASE_URL}/api/v1/google-drive/folder?folder_id=${encodeURIComponent(folderId)}`,
                { method: 'PUT' }
            )
            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '設定資料夾失敗' } }
            }
            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤' } }
        }
    },
}
