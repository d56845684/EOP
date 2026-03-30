import request from '@/utils/request';

export interface TeacherDetail {
    id: string;
    teacher_id: string;
    detail_type: string;
    content: string | null;
    issue_date: string | null;
    expiry_date: string | null;
    file_path: string | null;
    file_name: string | null;
    created_at: string | null;
    updated_at: string | null;
}

export interface TeacherDetailCreateParams {
    teacher_id: string;
    detail_type: string;
    content: string | null;
    issue_date: string | null;
    expiry_date: string | null;
}

export interface TeacherDetailUpdateParams {
    content: string | null;
    issue_date: string | null;
    expiry_date: string | null;
}

interface ResData<T> {
    data: T;
    message: string;
    success: boolean;
}

export function getTeacherDetails(teacherId: string) {
    return request.get<any, Omit<ResData<TeacherDetail[]>, 'message'>>(`/v1/teacher-details`, { params: { teacher_id: teacherId } });
}

export function createTeacherDetail(data: TeacherDetailCreateParams) {
    return request.post<any, ResData<TeacherDetail>>(`/v1/teacher-details`, data);
}

export function updateTeacherDetail(detailId: string, data: TeacherDetailUpdateParams) {
    return request.put<any, ResData<TeacherDetail>>(`/v1/teacher-details/${detailId}`, data);
}

export function deleteTeacherDetail(detailId: string) {
    return request.delete<any, Omit<ResData<null>, 'data'>>(`/v1/teacher-details/${detailId}`);
}

export function getUploadDetailUrl(detailId: string) {
    return request.get<any, { upload_url: string; storage_path: string }>(`/v1/teacher-details/${detailId}/upload-url`);
}

export function confirmUploadDetail(detailId: string, data: { storage_path: string, file_name: string }) {
    return request.post<any, ResData<TeacherDetail>>(`/v1/teacher-details/${detailId}/confirm-upload`, data);
}
