const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const DETAIL_TYPE_LABELS: Record<TeacherDetailType, string> = {
    qualification: '學歷',
    certificate: '證照',
    video: '教學影片',
    experience: '經歷',
}

export const teacherDetailsApi = {
    async list(teacherId: string): Promise<{ data: TeacherDetailListResponse | null, error: any }> {
        try {
            const url = `${API_BASE_URL}/api/v1/teacher-details?teacher_id=${teacherId}`
            const response = await fetch(url, { method: 'GET', credentials: 'include' })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師明細失敗' } }
            }

            const result: TeacherDetailListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateTeacherDetailData): Promise<{ data: TeacherDetail | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '新增教師明細失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(detailId: string, data: UpdateTeacherDetailData): Promise<{ data: TeacherDetail | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details/${detailId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新教師明細失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(detailId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details/${detailId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除教師明細失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getUploadUrl(detailId: string): Promise<{ data: { upload_url: string, storage_path: string } | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/upload-url`, {
                method: 'POST',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得上傳連結失敗' } }
            }

            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async confirmUpload(detailId: string, storagePath: string, fileName: string): Promise<{ data: TeacherDetail | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ storage_path: storagePath, file_name: fileName }),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '確認上傳失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getDownloadUrl(detailId: string): Promise<{ data: { download_url: string, file_name: string } | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-details/${detailId}/download-url`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得下載連結失敗' } }
            }

            const result = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
