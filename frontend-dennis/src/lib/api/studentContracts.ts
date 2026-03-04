import { fetchWithAuth } from './fetchWithAuth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

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
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        contract_status?: ContractStatus
        student_id?: string
    }): Promise<{ data: StudentContractListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.search) queryParams.set('search', params.search)
            if (params?.contract_status) queryParams.set('contract_status', params.contract_status)
            if (params?.student_id) queryParams.set('student_id', params.student_id)

            const url = `${API_BASE_URL}/api/v1/student-contracts${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetchWithAuth(url, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得學生合約列表失敗' } }
            }

            const result: StudentContractListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async get(contractId: string): Promise<{ data: StudentContract | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得學生合約失敗' } }
            }

            const result: StudentContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateStudentContractData): Promise<{ data: StudentContract | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '建立學生合約失敗' } }
            }

            const result: StudentContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(contractId: string, data: UpdateStudentContractData): Promise<{ data: StudentContract | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '更新學生合約失敗' } }
            }

            const result: StudentContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(contractId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '刪除學生合約失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async uploadFile(contractId: string, file: File): Promise<{ data: StudentContract | null, error: any }> {
        try {
            // 1. 從 backend 取得 S3 presigned upload URL
            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/upload-url`, {
                method: 'POST',
            })
            if (!urlRes.ok) {
                const error = await urlRes.json()
                return { data: null, error: { message: error.detail || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path } = await urlRes.json()

            // 2. 直接 PUT 檔案到 S3
            const uploadRes = await fetch(upload_url, {
                method: 'PUT',
                headers: {
                    'Content-Type': file.type || 'application/pdf',
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

    async downloadFile(contractId: string): Promise<{ url: string | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/download-url`, {
                method: 'GET',
            })
            if (!response.ok) {
                const error = await response.json()
                return { url: null, error: { message: error.detail || '取得下載連結失敗' } }
            }
            const { download_url } = await response.json()
            return { url: download_url, error: null }
        } catch (err) {
            return { url: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getStudentOptions(): Promise<{ data: StudentOption[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/options/students`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得學生選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getCourseOptions(studentId?: string): Promise<{ data: CourseOption[], error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (studentId) queryParams.set('student_id', studentId)

            const url = `${API_BASE_URL}/api/v1/student-contracts/options/courses${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetchWithAuth(url, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得課程選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // ========== Details API ==========

    async listDetails(contractId: string): Promise<{ data: StudentContractDetail[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/details`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得合約明細失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async createDetail(contractId: string, data: CreateDetailData): Promise<{ data: StudentContractDetail | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '新增合約明細失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateDetail(contractId: string, detailId: string, data: UpdateDetailData): Promise<{ data: StudentContractDetail | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/details/${detailId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '更新合約明細失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteDetail(contractId: string, detailId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/details/${detailId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '刪除合約明細失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // ========== Leave Records API ==========

    async listLeaveRecords(contractId: string): Promise<{ data: StudentContractLeaveRecord[], error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/leave-records`, {
                method: 'GET',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得請假紀錄失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async createLeaveRecord(contractId: string, data: CreateLeaveRecordData): Promise<{ data: StudentContractLeaveRecord | null, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/leave-records`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '新增請假紀錄失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteLeaveRecord(contractId: string, recordId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/student-contracts/${contractId}/leave-records/${recordId}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '刪除請假紀錄失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
