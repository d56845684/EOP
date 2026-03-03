const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export type BookingStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled'

export interface Booking {
    id: string
    booking_no: string
    student_id: string
    teacher_id: string
    course_id: string
    student_contract_id: string
    teacher_contract_id: string
    teacher_slot_id: string
    teacher_hourly_rate: number
    teacher_rate_percentage?: number
    booking_status: BookingStatus
    booking_date: string
    start_time: string
    end_time: string
    notes?: string
    created_at?: string
    updated_at?: string
    // 關聯資料
    student_name?: string
    teacher_name?: string
    course_name?: string
    student_contract_no?: string
    teacher_contract_no?: string
}

export interface BookingListResponse {
    success: boolean
    data: Booking[]
    total: number
    page: number
    per_page: number
    total_pages: number
}

export interface BookingResponse {
    success: boolean
    message: string
    data?: Booking
}

export interface CreateBookingData {
    student_id: string
    teacher_id: string
    course_id: string
    student_contract_id?: string  // 試上學生可不提供
    teacher_contract_id?: string
    teacher_slot_id?: string  // 可選，不提供則系統自動尋找符合時間的時段
    booking_date: string
    start_time: string
    end_time: string
    notes?: string
}

export interface UpdateBookingData {
    booking_status?: BookingStatus
    notes?: string
}

// 批次操作介面
export interface BatchUpdateByIdsData {
    booking_ids: string[]
    booking_status: BookingStatus
    notes?: string
}

export interface BatchDeleteByIdsData {
    booking_ids: string[]
}

export interface BatchUpdateData {
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    student_id?: string
    teacher_id?: string
    course_id?: string
    filter_status?: BookingStatus
    new_status: BookingStatus
    notes?: string
}

export interface BatchDeleteData {
    start_date: string
    end_date: string
    weekdays?: number[]  // 0=Monday, 6=Sunday
    student_id?: string
    teacher_id?: string
    course_id?: string
    filter_status?: BookingStatus
}

export interface BatchCreateData {
    student_id: string
    student_contract_id?: string  // 試上學生可不提供
    course_id?: string  // 試上學生無合約時必填
    teacher_id: string
    teacher_contract_id?: string
    start_date: string
    end_date: string
    weekdays: number[]  // 0=Monday, 6=Sunday
    start_time?: string
    end_time?: string
    notes?: string
}

// 下拉選單選項介面
export interface StudentOption {
    id: string
    student_no: string
    name: string
    student_type?: 'formal' | 'trial'
}

export interface TeacherOption {
    id: string
    teacher_no: string
    name: string
    teacher_level?: number
    is_primary?: boolean
}

export interface CourseOption {
    id: string
    course_code: string
    course_name: string
}

export interface StudentContractOption {
    id: string
    contract_no: string
    course_id: string
    course_ids?: string[]
    course_name?: string
    remaining_lessons: number
}

export interface TeacherContractOption {
    id: string
    contract_no: string
}

export interface TeacherSlotOption {
    id: string
    slot_date: string
    start_time: string
    end_time: string
    teacher_contract_id: string
    is_booked?: boolean
}

// 30 分鐘時間區塊
export interface TimeBlock {
    start_time: string
    end_time: string
    is_available: boolean
    booking_id?: string | null
}

export interface SlotAvailabilityResponse {
    slot_id: string
    slot_date: string
    slot_start_time: string
    slot_end_time: string
    blocks: TimeBlock[]
}

function parseErrorDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg || ''
        return msg.replace(/^Value error,\s*/, '')
    }
    return ''
}

export const bookingsApi = {
    async list(params?: {
        page?: number
        per_page?: number
        search?: string
        booking_status?: BookingStatus
        student_id?: string
        teacher_id?: string
        course_id?: string
        date_from?: string
        date_to?: string
    }): Promise<{ data: BookingListResponse | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.page) queryParams.set('page', params.page.toString())
            if (params?.per_page) queryParams.set('per_page', params.per_page.toString())
            if (params?.search) queryParams.set('search', params.search)
            if (params?.booking_status) queryParams.set('booking_status', params.booking_status)
            if (params?.student_id) queryParams.set('student_id', params.student_id)
            if (params?.teacher_id) queryParams.set('teacher_id', params.teacher_id)
            if (params?.course_id) queryParams.set('course_id', params.course_id)
            if (params?.date_from) queryParams.set('date_from', params.date_from)
            if (params?.date_to) queryParams.set('date_to', params.date_to)

            const url = `${API_BASE_URL}/api/v1/bookings${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得預約列表失敗' } }
            }

            const result: BookingListResponse = await response.json()
            return { data: result, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async get(bookingId: string): Promise<{ data: Booking | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/${bookingId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得預約失敗' } }
            }

            const result: BookingResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async create(data: CreateBookingData): Promise<{ data: Booking | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '建立預約失敗' } }
            }

            const result: BookingResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async update(bookingId: string, data: UpdateBookingData): Promise<{ data: Booking | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/${bookingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '更新預約失敗' } }
            }

            const result: BookingResponse = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async delete(bookingId: string): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/${bookingId}`, {
                method: 'DELETE',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '刪除預約失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 批次操作 API
    async createBatch(data: BatchCreateData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次建立預約失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateByIds(data: BatchUpdateByIdsData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/batch-by-ids/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次更新預約失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteByIds(data: BatchDeleteByIdsData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/batch-by-ids/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次刪除預約失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async updateBatch(data: BatchUpdateData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/batch`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次更新預約失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async deleteBatch(data: BatchDeleteData): Promise<{ success: boolean, message?: string, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/batch`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(data),
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '批次刪除預約失敗' } }
            }

            const result = await response.json()
            return { success: true, message: result.message, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得下拉選單選項
    async getStudentOptions(): Promise<{ data: StudentOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/options/students`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getTeacherOptions(params?: { student_id?: string, course_id?: string }): Promise<{ data: TeacherOption[] | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (params?.student_id) queryParams.set('student_id', params.student_id)
            if (params?.course_id) queryParams.set('course_id', params.course_id)

            const url = `${API_BASE_URL}/api/v1/bookings/options/teachers${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetch(url, {
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

    async updateTeacherLevel(teacherId: string, level: number): Promise<{ success: boolean, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/options/teachers/${teacherId}/level?level=${level}`, {
                method: 'PUT',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: parseErrorDetail(error.detail) || '更新教師等級失敗' } }
            }

            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getOverlappingCourseOptions(studentId: string, teacherId: string): Promise<{ data: CourseOption[] | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            queryParams.set('student_id', studentId)
            queryParams.set('teacher_id', teacherId)

            const url = `${API_BASE_URL}/api/v1/bookings/options/overlapping-courses?${queryParams.toString()}`

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得交集課程選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getCourseOptions(): Promise<{ data: CourseOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/options/courses`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得課程選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getStudentContractOptions(studentId: string): Promise<{ data: StudentContractOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/options/student-contracts/${studentId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生合約選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async getTeacherContractOptions(teacherId: string): Promise<{ data: TeacherContractOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/options/teacher-contracts/${teacherId}`, {
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

    async getTeacherSlotOptions(teacherId: string, dateFrom?: string, dateTo?: string): Promise<{ data: TeacherSlotOption[] | null, error: any }> {
        try {
            const queryParams = new URLSearchParams()
            if (dateFrom) queryParams.set('date_from', dateFrom)
            if (dateTo) queryParams.set('date_to', dateTo)

            const url = `${API_BASE_URL}/api/v1/bookings/options/teacher-slots/${teacherId}${queryParams.toString() ? '?' + queryParams.toString() : ''}`

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得教師時段選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得當前學生的資料（學生用）
    async getMyStudentInfo(): Promise<{ data: StudentOption | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/my-student-info`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生資料失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得時段的 30 分鐘區塊可用狀態
    async getSlotAvailability(slotId: string): Promise<{ data: SlotAvailabilityResponse | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/slot-availability/${slotId}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得時段可用狀態失敗' } }
            }

            const result = await response.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    // 取得當前學生的合約（學生用）
    async getMyContracts(): Promise<{ data: StudentContractOption[] | null, error: any }> {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/bookings/my-contracts`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const error = await response.json()
                return { data: null, error: { message: parseErrorDetail(error.detail) || '取得學生合約選項失敗' } }
            }

            const result = await response.json()
            return { data: result.data || [], error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
