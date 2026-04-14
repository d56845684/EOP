import { apiGet, apiDelete, apiAction } from './client'

export interface GoogleDriveStatus {
    is_linked: boolean
    drive_mode: string | null
    google_email: string | null
    drive_folder_id: string | null
    linked_at: string | null
}

export const googleDriveApi = {
    getStatus: () =>
        apiGet<GoogleDriveStatus>('/api/v1/google-drive/oauth/status', '取得狀態失敗', { extractData: false }),

    getAuthorizeUrl: () =>
        apiGet<{ authorize_url: string }>('/api/v1/google-drive/oauth/authorize', '取得授權 URL 失敗', { extractData: false }),

    unlink: () =>
        apiDelete('/api/v1/google-drive/oauth/unlink', '解除綁定失敗'),

    updateFolder: (folderId: string) =>
        apiAction('PUT', `/api/v1/google-drive/folder?folder_id=${encodeURIComponent(folderId)}`, undefined, '設定資料夾失敗'),
}
