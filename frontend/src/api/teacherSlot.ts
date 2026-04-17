import request from '@/utils/request';
import type { BaseResponse, DataResponse, ListResponse } from './response';

export interface TeacherSlotParams {
    page?: number;
    per_page?: number;
    teacher_id?: string;
    date_from?: string; // YYYY-MM-DD
    date_to?: string;   // YYYY-MM-DD
    is_available?: boolean;
}

export interface TeacherSlotCreate {
    teacher_id: string;
    slot_date: string; // YYYY-MM-DD
    start_time: string; // HH:mm:ss
    end_time: string; // HH:mm:ss
    is_available?: boolean;
    notes?: string;
}

export interface TeacherSlotBatchCreate {
    teacher_id: string;
    start_date: string; // YYYY-MM-DD
    end_date: string;   // YYYY-MM-DD
    weekdays: number[]; // 0=Mon, 6=Sun
    start_time: string; // HH:mm:ss
    end_time: string; // HH:mm:ss
}

export interface TeacherSlotResponse {
    id: string;
    teacher_id: string;
    teacher_contract_id?: string | null;
    slot_date: string;
    start_time: string;
    end_time: string;
    is_available: boolean;
    is_booked: boolean;
    notes?: string | null;
    teacher_name?: string | null;
    teacher_no?: string | null;
    teacher_contract_no?: string | null;
}

export function getTeacherSlots(params: TeacherSlotParams) {
    return request.get<any, ListResponse<TeacherSlotResponse>>('/v1/teacher-slots', { params });
}

export function createTeacherSlot(data: TeacherSlotCreate) {
    return request.post<any, DataResponse<TeacherSlotResponse>>('/v1/teacher-slots', data);
}

export function batchCreateTeacherSlots(data: TeacherSlotBatchCreate) {
    return request.post<any, BaseResponse>('/v1/teacher-slots/batch', data);
}

export function deleteTeacherSlot(slotId: string) {
    return request.delete<any, BaseResponse>(`/v1/teacher-slots/${slotId}`);
}
