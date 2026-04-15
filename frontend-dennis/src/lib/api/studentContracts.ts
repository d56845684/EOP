import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export type ContractStatus = 'pending' | 'active' | 'expired' | 'terminated'
export type DetailType = 'lesson_price' | 'discount' | 'compensation'

export interface StudentContractDetail {
    id: string
    student_contract_id: string
    detail_type: DetailType
    course_id?: string
    course_name?: string
    description?: string
    amount: number
    notes?: string
    created_at?: string
    updated_at?: string
}

export interface StudentContractLeaveRecord {
    id: string
    student_contract_id: string
    leave_date: string
    reason?: string
    created_at?: string
}

export interface StudentContract {
    id: string
    contract_no: string
    student_id: string
    contract_status: ContractStatus
    start_date: string
    end_date: string
    total_lessons: number
    remaining_lessons: number
    total_amount?: number
    total_leave_allowed: number
    used_leave_count: number
    is_recurring: boolean
    notes?: string
    created_at?: string
    updated_at?: string
    contract_file_path?: string
    contract_file_name?: string
    contract_file_uploaded_at?: string
    student_name?: string
    details: StudentContractDetail[]
    leave_records: StudentContractLeaveRecord[]
    addendums?: any[]
}

export interface StudentContractListResponse {
    success: boolean
    data: StudentContract[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface StudentContractResponse {
    success: boolean
    message: string
    data?: StudentContract
}

export interface CreateStudentContractData {
    student_id: string
    contract_status: ContractStatus
    start_date: string
    end_date: string
    total_lessons: number
    remaining_lessons: number
    total_amount: number
    total_leave_allowed?: number
    is_recurring?: boolean
    notes?: string
}

export interface UpdateStudentContractData {
    student_id?: string
    contract_status?: ContractStatus
    start_date?: string
    end_date?: string
    total_lessons?: number
    remaining_lessons?: number
    total_amount?: number
    total_leave_allowed?: number
    is_recurring?: boolean
    notes?: string
}

export interface CreateDetailData {
    detail_type: DetailType
    course_id?: string
    description?: string
    amount: number
    notes?: string
}

export interface UpdateDetailData {
    description?: string
    amount?: number
    notes?: string
}

export interface CreateLeaveRecordData {
    leave_date: string
    reason?: string
}

export interface StudentOption {
    id: string
    student_no: string
    name: string
}

export interface CourseOption {
    id: string
    course_code: string
    course_name: string
}

export const studentContractsApi = {
    list: (params?: {
        page?: number
        per_page?: number
        search?: string
        contract_status?: ContractStatus
        student_id?: string
    }) =>
        apiGet<StudentContractListResponse>(`/api/v1/student-contracts${qs(params || {})}`, '取得學生合約列表失敗', { extractData: false }),

    get: (contractId: string) =>
        apiGet<StudentContract>(`/api/v1/student-contracts/${contractId}`, '取得學生合約失敗'),

    create: (data: CreateStudentContractData) =>
        apiPost<StudentContract>('/api/v1/student-contracts', data, '建立學生合約失敗'),

    update: (contractId: string, data: UpdateStudentContractData) =>
        apiPut<StudentContract>(`/api/v1/student-contracts/${contractId}`, data, '更新學生合約失敗'),

    delete: (contractId: string) =>
        apiDelete(`/api/v1/student-contracts/${contractId}`, '刪除學生合約失敗'),

    // Presigned URL upload flow — keep fetchWithAuth
    async uploadFile(contractId: string, file: File): Promise<{ data: StudentContract | null, error: any }> {
        try {
            const fileExt = file.name.split('.').pop()?.toLowerCase() || 'pdf'

            // 1. 從 backend 取得 S3 presigned upload URL（帶檔案格式）
            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/upload-url?file_ext=${fileExt}`, {
                method: 'POST',
            })
            if (!urlRes.ok) {
                const error = await urlRes.json()
                return { data: null, error: { message: error.detail || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path, content_type } = await urlRes.json()

            // 2. 直接 PUT 檔案到 S3
            const uploadRes = await fetch(upload_url, {
                method: 'PUT',
                headers: {
                    'Content-Type': content_type || file.type || 'application/octet-stream',
                },
                body: file,
            })
            if (!uploadRes.ok) {
                const errText = await uploadRes.text()
                return { data: null, error: { message: `檔案上傳失敗: ${errText}` } }
            }

            // 3. 通知 backend 確認上傳完成
            const confirmRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path, file_name: file.name }),
            })
            if (!confirmRes.ok) {
                const error = await confirmRes.json()
                return { data: null, error: { message: error.detail || '確認上傳失敗' } }
            }

            const result: StudentContractResponse = await confirmRes.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async generatePdf(contractId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/generate-docx`)
            if (!response.ok) {
                const err = await response.json()
                return { success: false, error: { message: err.detail || '產生合約文件失敗' } }
            }
            const blob = await response.blob()
            const contentDisposition = response.headers.get('Content-Disposition')
            let filename = 'contract.docx'
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^"]+)"?/)
                if (match) filename = match[1]
            }
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
            return { success: true, error: null }
        } catch {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async downloadFile(contractId: string): Promise<{ url: string | null, error: any }> {
        const { data, error } = await apiGet<{ download_url: string }>(`/api/v1/student-contracts/${contractId}/download-url`, '取得下載連結失敗', { extractData: false })
        if (error) return { url: null, error }
        return { url: data!.download_url, error: null }
    },

    getStudentOptions: () =>
        apiGet<StudentOption[]>('/api/v1/student-contracts/options/students', '取得學生選項失敗'),

    getCourseOptions: (studentId?: string) =>
        apiGet<CourseOption[]>(`/api/v1/student-contracts/options/courses${qs({ student_id: studentId })}`, '取得課程選項失敗'),

    // ========== Details API ==========

    listDetails: (contractId: string) =>
        apiGet<StudentContractDetail[]>(`/api/v1/student-contracts/${contractId}/details`, '取得合約明細失敗'),

    createDetail: (contractId: string, data: CreateDetailData) =>
        apiPost<StudentContractDetail>(`/api/v1/student-contracts/${contractId}/details`, data, '新增合約明細失敗'),

    updateDetail: (contractId: string, detailId: string, data: UpdateDetailData) =>
        apiPut<StudentContractDetail>(`/api/v1/student-contracts/${contractId}/details/${detailId}`, data, '更新合約明細失敗'),

    deleteDetail: (contractId: string, detailId: string) =>
        apiDelete(`/api/v1/student-contracts/${contractId}/details/${detailId}`, '刪除合約明細失敗'),

    // ========== Leave Records API ==========

    listLeaveRecords: (contractId: string) =>
        apiGet<StudentContractLeaveRecord[]>(`/api/v1/student-contracts/${contractId}/leave-records`, '取得請假紀錄失敗'),

    createLeaveRecord: (contractId: string, data: CreateLeaveRecordData) =>
        apiPost<StudentContractLeaveRecord>(`/api/v1/student-contracts/${contractId}/leave-records`, data, '新增請假紀錄失敗'),

    deleteLeaveRecord: (contractId: string, recordId: string) =>
        apiDelete(`/api/v1/student-contracts/${contractId}/leave-records/${recordId}`, '刪除請假紀錄失敗'),
}
