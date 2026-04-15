import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete, qs } from './client'

export type ContractStatus = 'pending' | 'active' | 'expired' | 'terminated' | 'suspended'
export type EmploymentType = 'hourly' | 'full_time'
export type DetailType = 'course_rate' | 'base_salary' | 'allowance' | 'overtime_rate'

export interface TeacherContractDetail {
    id: string
    teacher_contract_id: string
    detail_type: DetailType
    course_id?: string
    course_name?: string
    description?: string
    amount: number
    notes?: string
    created_at?: string
    updated_at?: string
}

export interface CourseOption {
    id: string
    course_code: string
    course_name: string
}

export interface TeacherWorkSchedule {
    id: string
    teacher_contract_id: string
    weekday: number  // 0=週一, 6=週日
    start_time: string
    end_time: string
    notes?: string
    created_at?: string
    updated_at?: string
}

export interface TeacherWorkScheduleInput {
    weekday: number
    start_time: string
    end_time: string
    notes?: string
}

export interface TeacherContract {
    id: string
    contract_no: string
    teacher_id: string
    contract_status: ContractStatus
    start_date: string
    end_date: string
    employment_type: EmploymentType
    trial_completed_bonus?: number
    trial_to_formal_bonus?: number
    work_start_time?: string | null
    work_end_time?: string | null
    notes?: string
    created_at?: string
    updated_at?: string
    contract_file_path?: string
    contract_file_name?: string
    contract_file_uploaded_at?: string
    teacher_name?: string
    details: TeacherContractDetail[]
    total_amount?: number
    work_schedules: TeacherWorkSchedule[]
    addendums?: any[]
}

export interface TeacherContractListResponse {
    success: boolean
    data: TeacherContract[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface TeacherContractResponse {
    success: boolean
    message: string
    data?: TeacherContract
}

export interface CreateTeacherContractData {
    teacher_id: string
    contract_status: ContractStatus
    start_date: string
    end_date: string
    employment_type: EmploymentType
    trial_completed_bonus?: number
    trial_to_formal_bonus?: number
    work_start_time?: string | null
    work_end_time?: string | null
    notes?: string
}

export interface UpdateTeacherContractData {
    teacher_id?: string
    contract_status?: ContractStatus
    start_date?: string
    end_date?: string
    employment_type?: EmploymentType
    trial_completed_bonus?: number
    trial_to_formal_bonus?: number
    work_start_time?: string | null
    work_end_time?: string | null
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

export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
}

export const teacherContractsApi = {
    list: (params?: {
        page?: number
        per_page?: number
        search?: string
        contract_status?: ContractStatus
        employment_type?: EmploymentType
        teacher_id?: string
    }) =>
        apiGet<TeacherContractListResponse>(`/api/v1/teacher-contracts${qs(params || {})}`, '取得教師合約列表失敗', { extractData: false }),

    get: (contractId: string) =>
        apiGet<TeacherContract>(`/api/v1/teacher-contracts/${contractId}`, '取得教師合約失敗'),

    create: (data: CreateTeacherContractData) =>
        apiPost<TeacherContract>('/api/v1/teacher-contracts', data, '建立教師合約失敗'),

    update: (contractId: string, data: UpdateTeacherContractData) =>
        apiPut<TeacherContract>(`/api/v1/teacher-contracts/${contractId}`, data, '更新教師合約失敗'),

    delete: (contractId: string) =>
        apiDelete(`/api/v1/teacher-contracts/${contractId}`, '刪除教師合約失敗'),

    // Presigned URL upload flow — keep fetchWithAuth
    async uploadFile(contractId: string, file: File): Promise<{ data: TeacherContract | null, error: any }> {
        try {
            const fileExt = file.name.split('.').pop()?.toLowerCase() || 'pdf'

            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/upload-url?file_ext=${fileExt}`, {
                method: 'POST',
            })
            if (!urlRes.ok) {
                const error = await urlRes.json()
                return { data: null, error: { message: error.detail || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path, content_type } = await urlRes.json()

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
            const confirmRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path, file_name: file.name }),
            })
            if (!confirmRes.ok) {
                const error = await confirmRes.json()
                return { data: null, error: { message: error.detail || '確認上傳失敗' } }
            }

            const result: TeacherContractResponse = await confirmRes.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async generatePdf(contractId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/generate-pdf`)
            if (!response.ok) {
                const err = await response.json()
                return { success: false, error: { message: err.detail || '產生合約 PDF 失敗' } }
            }
            const blob = await response.blob()
            const contentDisposition = response.headers.get('Content-Disposition')
            let filename = 'contract.pdf'
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
        const { data, error } = await apiGet<{ download_url: string }>(`/api/v1/teacher-contracts/${contractId}/download-url`, '取得下載連結失敗', { extractData: false })
        if (error) return { url: null, error }
        return { url: data!.download_url, error: null }
    },

    getTeacherOptions: () =>
        apiGet<TeacherOption[]>('/api/v1/teacher-contracts/options/teachers', '取得教師選項失敗'),

    getCourseOptions: () =>
        apiGet<CourseOption[]>('/api/v1/teacher-contracts/options/courses', '取得課程選項失敗'),

    // ========== Details API ==========

    listDetails: (contractId: string) =>
        apiGet<TeacherContractDetail[]>(`/api/v1/teacher-contracts/${contractId}/details`, '取得合約明細失敗'),

    createDetail: (contractId: string, data: CreateDetailData) =>
        apiPost<TeacherContractDetail>(`/api/v1/teacher-contracts/${contractId}/details`, data, '新增合約明細失敗'),

    updateDetail: (contractId: string, detailId: string, data: UpdateDetailData) =>
        apiPut<TeacherContractDetail>(`/api/v1/teacher-contracts/${contractId}/details/${detailId}`, data, '更新合約明細失敗'),

    deleteDetail: (contractId: string, detailId: string) =>
        apiDelete(`/api/v1/teacher-contracts/${contractId}/details/${detailId}`, '刪除合約明細失敗'),

    // ========== Work Schedules API ==========

    listWorkSchedules: (contractId: string) =>
        apiGet<TeacherWorkSchedule[]>(`/api/v1/teacher-contracts/${contractId}/work-schedules`, '取得工作時段失敗'),

    setWorkSchedules: (contractId: string, schedules: TeacherWorkScheduleInput[]) =>
        apiPut<TeacherWorkSchedule[]>(`/api/v1/teacher-contracts/${contractId}/work-schedules`, { schedules }, '更新工作時段失敗'),

    clearWorkSchedules: (contractId: string) =>
        apiDelete(`/api/v1/teacher-contracts/${contractId}/work-schedules`, '清除工作時段失敗'),
}
