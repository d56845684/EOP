import request from '@/utils/request';
import type { BaseResponse, DataResponse } from './response';

export type BookingStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled';

// API Request Parameters
export interface BookingListParams {
    page?: number;
    per_page?: number;
    search?: string;
    booking_status?: BookingStatus | '';
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
    booking_status: BookingStatus;
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

export interface BookingCreate {
    student_id: string;
    teacher_id: string;
    course_id: string;
    student_contract_id?: string | null;
    teacher_contract_id?: string | null;
    teacher_slot_id?: string | null;
    booking_date: string;
    start_time: string;
    end_time: string;
    notes?: string | null;
}

export interface BookingUpdate {
    booking_status?: BookingStatus | null;
    end_time?: string | null;
    notes?: string | null;
}

export interface BookingBatchCreate {
    student_id: string;
    student_contract_id?: string | null;
    course_id?: string | null;
    teacher_id: string;
    teacher_contract_id?: string | null;
    start_date: string;
    end_date: string;
    weekdays: number[] | null;
    start_time?: string | null;
    end_time?: string | null;
    notes?: string | null;
}

export interface BookingBatchUpdate {
    start_date: string;
    end_date: string;
    weekdays?: number[] | null;
    student_id?: string | null;
    teacher_id?: string | null;
    course_id?: string | null;
    filter_status?: BookingStatus | null;
    new_status: BookingStatus;
    notes?: string | null;
}

export interface BookingBatchDelete {
    start_date: string;
    end_date: string;
    weekdays?: number[] | null;
    student_id?: string | null;
    teacher_id?: string | null;
    course_id?: string | null;
    filter_status?: BookingStatus | null;
}

export interface BookingBatchUpdateByIds {
    booking_ids: string[];
    booking_status: BookingStatus;
    notes?: string | null;
}

export interface BookingBatchDeleteByIds {
    booking_ids: string[];
}

// API Response Wrap
export interface BookingListResponse {
    success: boolean;
    message?: string;
    error_code?: string | null;
    data: BookingItem[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
}

// List API
export function getBookingList(params: BookingListParams) {
    return request.get<any, BookingListResponse>('/v1/bookings', { params });
}

export function createBooking(data: BookingCreate) {
    return request.post<any, DataResponse<BookingItem>>('/v1/bookings', data);
}

export function updateBooking(id: string, data: BookingUpdate) {
    return request.put<any, DataResponse<BookingItem>>(`/v1/bookings/${id}`, data);
}

// Batch APIs
export function batchCreateBookings(data: BookingBatchCreate) {
    return request.post<any, BaseResponse & { data?: BookingItem[] }>(
      '/v1/bookings/batch',
      data
    );
}

export function batchUpdateBookings(data: BookingBatchUpdate) {
    return request.put<any, BaseResponse>('/v1/bookings/batch', data);
}

export function batchDeleteBookings(data: BookingBatchDelete) {
    return request.delete<any, BaseResponse>('/v1/bookings/batch', { data });
}

export function batchUpdateBookingsByIds(data: BookingBatchUpdateByIds) {
    return request.post<any, BaseResponse>('/v1/bookings/batch-by-ids/update', data);
}

export function batchDeleteBookingsByIds(data: BookingBatchDeleteByIds) {
    return request.post<any, BaseResponse>('/v1/bookings/batch-by-ids/delete', data);
}

// Options API
export interface BookingStudentOption {
    id: string;
    name: string;
    email: string;
}

export interface BookingTeacherOption {
    id: string;
    name: string;
    teacher_no?: string;
}

export interface BookingCourseOption {
    id: string;
    course_name: string;
    course_code?: string;
    duration?: number;
}

export interface BookingStudentContractOption {
    id: string;
    contract_no: string;
    course_id: string;
    remaining_lessons: number;
    contract_status: string;
    course_name: string;
}

export interface BookingTeacherSlotOption {
    id: string;
    start_time: string;
    end_time: string;
    is_booked: boolean;
    slot_date: string;
    teacher_contract_id: string;
}

export function getBookingOptionStudents() {
    return request.get<any, DataResponse<BookingStudentOption[]>>('/v1/bookings/options/students');
}

export function getBookingOptionTeachers(params?: { student_id?: string }) {
    return request.get<any, DataResponse<BookingTeacherOption[]>>('/v1/bookings/options/teachers', { params });
}

export function getBookingOptionOverlappingCourses(params: { student_id: string; teacher_id: string }) {
    return request.get<any, DataResponse<BookingCourseOption[]>>('/v1/bookings/options/overlapping-courses', { params });
}

export function getBookingCourseOptions() {
    return request.get<any, DataResponse<BookingCourseOption[]>>('/v1/bookings/options/courses');
}

export function getBookingOptionStudentContracts(studentId: string) {
    return request.get<any, DataResponse<BookingStudentContractOption[]>>(`/v1/bookings/options/student-contracts/${studentId}`);
}

export function getBookingOptionTeacherSlots(teacherId: string) {
    return request.get<any, DataResponse<BookingTeacherSlotOption[]>>(`/v1/bookings/options/teacher-slots/${teacherId}`);
}
