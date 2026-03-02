const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface TeacherSlot {
    id: string
    teacher_id: string
    teacher_contract_id?: string
    slot_date: string
    start_time: string
    end_time: string
    is_available: boolean
    is_booked: boolean
    notes?: string
    created_at?: string
    updated_at?: string
    // 關聯資料
    teacher_name?: string
    teacher_no?: string
    teacher_contract_no?: string
}

export interface TeacherSlotListResponse {
    success: boolean
    data: TeacherSlot[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface TeacherSlotResponse {
    success: boolean
    message: string
    data?: TeacherSlot
}

export interface CreateTeacherSlotData {
    teacher_id: string
    teacher_contract_id?: string
    slot_date: string
    start_time: string
    end_time: string
    is_available?: boolean
    notes?: string
}

export interface BatchCreateTeacherSlotData {
    teacher_id: string
    teacher_contract_id?: string
    start_date: string
    end_date: string
    weekdays: number[]  // 0=Monday, 6=Sunday
    start_time: string
    end_time: string
    notes?: string
}

export interface BatchDeleteTeacherSlotData {
    teacher_id: string
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    start_time?: string
    end_time?: string
}

export interface BatchUpdateTeacherSlotData {
    // 篩選條件
    teacher_id: string
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    filter_start_time?: string
    filter_end_time?: string
    // 更新內容
    new_start_time?: string
    new_end_time?: string
    is_available?: boolean
    notes?: string
}

export interface BatchDeleteByIdsData {
    slot_ids: string[]
}

export interface BatchUpdateByIdsData {
    slot_ids: string[]
    new_start_time?: string
    new_end_time?: string
    is_available?: boolean
    notes?: string
}

export interface UpdateTeacherSlotData {
    teacher_contract_id?: string
    slot_date?: string
    start_time?: string
    end_time?: string
    is_available?: boolean
    notes?: string
}

// 下拉選單選項介面
export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
}

export interface TeacherContractOption {
    id: string
    contract_no: string
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        // Pydantic validation errors: "Value error, 實際訊息"
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const teacherSlotsApi = {
    async list(params?: {
        page?: number
        per_page?: number
        teacher_id?: string
        date_from?: string
        date_to?: string
        is_available?: boolean
        is_booked?: boolean
    }): Promise<{ data: TeacherSlotListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.teacher_id) queryParams.set('teacher_id', params.teacher_id)
            if (params?.date_from) queryParams.set('date_from', params.date_from)
            if (params?.date_to) queryParams.set('date_to', params.date_to)
            if (params?.is_available !== undefined) queryParams.set('is_available', params.is_available.toString())
            if (params?.is_booked !== undefined) queryParams.set('is_booked', params.is_booked.toString())

            const url = `${API_BASE_URL}/api/v1/teacher-slots${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師時段列表失敗' } }
            }

            const result: TeacherSlotListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async get(slotId: string): Promise<{ data: TeacherSlot | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/${slotId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師時段失敗' } }
            }

            const result: TeacherSlotResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateTeacherSlotData): Promise<{ data: TeacherSlot | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立教師時段失敗' } }
            }

            const result: TeacherSlotResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async createBatch(data: BatchCreateTeacherSlotData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次建立教師時段失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteBatch(data: BatchDeleteTeacherSlotData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/batch`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次刪除教師時段失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateBatch(data: BatchUpdateTeacherSlotData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/batch`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次更新教師時段失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteByIds(data: BatchDeleteByIdsData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/batch-by-ids/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次刪除教師時段失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateByIds(data: BatchUpdateByIdsData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/batch-by-ids/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次更新教師時段失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(slotId: string, data: UpdateTeacherSlotData): Promise<{ data: TeacherSlot | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/${slotId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新教師時段失敗' } }
            }

            const result: TeacherSlotResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(slotId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/${slotId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除教師時段失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得下拉選單選項（僅限員工）
    async getTeacherOptions(): Promise<{ data: TeacherOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/options/teachers`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得當前教師的合約
    async getMyContracts(): Promise<{ data: TeacherContractOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/teacher-slots/my-contracts`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師合約選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
