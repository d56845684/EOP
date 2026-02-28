const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export type ContractStatus = 'pending' | 'active' | 'expired' | 'terminated'
export type EmploymentType = 'hourly' | 'full_time'
export type DetailType = 'course_rate' | 'base_salary' | 'allowance'

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

export interface TeacherContract {
    id: string
    contract_no: string
    teacher_id: string
    contract_status: ContractStatus
    start_date: string
    end_date: string
    employment_type: EmploymentType
    trial_to_formal_bonus?: number
    notes?: string
    created_at?: string
    updated_at?: string
    contract_file_path?: string
    contract_file_name?: string
    contract_file_uploaded_at?: string
    teacher_name?: string
    details: TeacherContractDetail[]
    total_amount?: number
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
    trial_to_formal_bonus?: number
    notes?: string
}

export interface UpdateTeacherContractData {
    teacher_id?: string
    contract_status?: ContractStatus
    start_date?: string
    end_date?: string
    employment_type?: EmploymentType
    trial_to_formal_bonus?: number
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
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        contract_status?: ContractStatus
        employment_type?: EmploymentType
        teacher_id?: string
    }): Promise<{ data: TeacherContractListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.search) queryParams.set('search', params.search)
            if (params?.contract_status) queryParams.set('contract_status', params.contract_status)
            if (params?.employment_type) queryParams.set('employment_type', params.employment_type)
            if (params?.teacher_id) queryParams.set('teacher_id', params.teacher_id)

            const url = `${API_BASE_URL}/api/v1/teacher-contracts${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得教師合約列表失敗' } }
            }

            const result: TeacherContractListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async get(contractId: string): Promise<{ data: TeacherContract | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '取得教師合約失敗' } }
            }

            const result: TeacherContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateTeacherContractData): Promise<{ data: TeacherContract | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '建立教師合約失敗' } }
            }

            const result: TeacherContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(contractId: string, data: UpdateTeacherContractData): Promise<{ data: TeacherContract | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: error.detail || '更新教師合約失敗' } }
            }

            const result: TeacherContractResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(contractId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '刪除教師合約失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async uploadFile(contractId: string, file: File): Promise<{ data: TeacherContract | null, error: any }> {
        try {
            // 1. 從 backend 取得 S3 presigned upload URL
            const urlRes = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/upload-url`, {
                method: 'POST',
                credentials: 'include',
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
            const confirmRes = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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

    async downloadFile(contractId: string): Promise<{ url: string | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/download-url`, {
                method: 'GET',
                credentials: 'include',
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

    async getTeacherOptions(): Promise<{ data: TeacherOption[], error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/options/teachers`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: [], error: { message: error.detail || '取得教師選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: [], error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getCourseOptions(): Promise<{ data: CourseOption[], error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/options/courses`, {
                method: 'GET',
                credentials: 'include',
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

    async listDetails(contractId: string): Promise<{ data: TeacherContractDetail[], error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/details`, {
                method: 'GET',
                credentials: 'include',
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

    async createDetail(contractId: string, data: CreateDetailData): Promise<{ data: TeacherContractDetail | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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

    async updateDetail(contractId: string, detailId: string, data: UpdateDetailData): Promise<{ data: TeacherContractDetail | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/details/${detailId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
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
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-contracts/${contractId}/details/${detailId}`, {
                method: 'DELETE',
                credentials: 'include',
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
}
