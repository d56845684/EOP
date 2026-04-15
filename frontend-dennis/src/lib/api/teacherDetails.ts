import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete } from './client'

export type TeacherDetailType = 'qualification' | 'certificate' | 'video' | 'experience'

export interface TeacherDetail {
    id: string
    teacher_id: string
    detail_type: TeacherDetailType
    content?: string
    issue_date?: string
    expiry_date?: string
    file_path?: string
    file_name?: string
    created_at?: string
    updated_at?: string
}

export interface TeacherDetailListResponse {
    success: boolean
    data: TeacherDetail[]
}

export interface CreateTeacherDetailData {
    teacher_id: string
    detail_type: TeacherDetailType
    content?: string
    issue_date?: string
    expiry_date?: string
}

export interface UpdateTeacherDetailData {
    content?: string
    issue_date?: string
    expiry_date?: string
}

export const DETAIL_TYPE_LABELS: Record<TeacherDetailType, string> = {
    qualification: '學歷',
    certificate: '證照',
    video: '教學影片',
    experience: '經歷',
}

export const teacherDetailsApi = {
    list: (teacherId: string) =>
        apiGet<TeacherDetailListResponse>(`/api/v1/teacher-details?teacher_id=${teacherId}`, '取得教師明細失敗', { extractData: false }),

    create: (data: CreateTeacherDetailData) =>
        apiPost<TeacherDetail>('/api/v1/teacher-details', data, '新增教師明細失敗'),

    update: (detailId: string, data: UpdateTeacherDetailData) =>
        apiPut<TeacherDetail>(`/api/v1/teacher-details/${detailId}`, data, '更新教師明細失敗'),

    delete: (detailId: string) =>
        apiDelete(`/api/v1/teacher-details/${detailId}`, '刪除教師明細失敗'),

    async getUploadUrl(detailId: string, fileName: string): Promise<{ data: { upload_url: string, storage_path: string } | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/upload-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_name: fileName }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得上傳連結失敗' } }
            }

            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async confirmUpload(detailId: string, storagePath: string, fileName: string): Promise<{ data: TeacherDetail | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path: storagePath, file_name: fileName }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '確認上傳失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getDownloadUrl(detailId: string): Promise<{ data: { download_url: string, file_name: string } | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/download-url`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得下載連結失敗' } }
            }

            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
