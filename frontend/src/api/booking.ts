import request from '@/utils/request';

// API Request Parameters
export interface BookingListParams {
    page?: number;
    per_page?: number;
    search?: string;
    booking_status?: 'pending' | 'confirmed' | 'completed' | 'cancelled' | '';
    student_id?: string;
    teacher_id?: string;
    course_id?: string;
    date_from?: string; // YYYY-MM-DD
    date_to?: string;   // YYYY-MM-DD
}

// API Response Item structure
export interface BookingItem {
    id: string;
    booking_no: string;
    student_id: string;
    teacher_id: string;
    course_id: string;
    student_contract_id?: string | null;
    teacher_contract_id?: string | null;
    teacher_slot_id: string;
    teacher_hourly_rate: number;
    teacher_rate_percentage?: number | null;
    booking_status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
    booking_date: string;
    start_time: string;
    end_time: string;
    booking_type: string;
    is_trial_to_formal: boolean;
    lessons_used: number;
    notes?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
    student_name?: string | null;
    teacher_name?: string | null;
    course_name?: string | null;
    student_contract_no?: string | null;
    teacher_contract_no?: string | null;
}

// API Response Wrap
export interface BookingListResponse {
    success: boolean;
    message: string;
    data: BookingItem[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
}

export function getBookingList(params: BookingListParams) {
    // Assuming the baseURL in request.ts covers '/api', we call '/v1/bookings'
    return request.get<any, BookingListResponse>('/v1/bookings', { params });
}

export interface BookingTeacherOption {
    id: string;
    name: string;
    teacher_no?: string;
    // other fields that might be returned
    [key: string]: any;
}

export interface BookingCourseOption {
    id: string;
    course_name: string;
    course_code?: string;
    // other fields that might be returned
    [key: string]: any;
}

export function getBookingTeacherOptions(params?: { student_id?: string }) {
    return request.get<any, { data: BookingTeacherOption[] }>('/v1/bookings/options/teachers', { params });
}

export function getBookingCourseOptions() {
    return request.get<any, { data: BookingCourseOption[] }>('/v1/bookings/options/courses');
}
