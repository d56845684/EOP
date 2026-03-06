import request from '@/utils/request';

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

export function getTeacherSlots(params: TeacherSlotParams) {
    return request.get('/v1/teacher-slots', { params });
}

export function createTeacherSlot(data: TeacherSlotCreate) {
    return request.post('/v1/teacher-slots', data);
}

export function batchCreateTeacherSlots(data: TeacherSlotBatchCreate) {
    return request.post('/v1/teacher-slots/batch', data);
}

export function deleteTeacherSlot(slotId: string) {
    return request.delete(`/v1/teacher-slots/${slotId}`);
}
