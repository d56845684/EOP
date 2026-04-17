import request from '@/utils/request';
import type { BaseResponse, DataResponse } from './response';

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

export interface UploadDetailUrlResponse {
    success?: boolean;
    message?: string;
    error_code?: string | null;
    upload_url: string;
    storage_path: string;
    content_type: string;
    max_size_bytes: number;
}

export function getTeacherDetails(teacherId: string) {
    return request.get<any, DataResponse<TeacherDetail[]>>(`/v1/teacher-details`, { params: { teacher_id: teacherId } });
}

export function createTeacherDetail(data: TeacherDetailCreateParams) {
    return request.post<any, DataResponse<TeacherDetail>>(`/v1/teacher-details`, data);
}

export function updateTeacherDetail(detailId: string, data: TeacherDetailUpdateParams) {
    return request.put<any, DataResponse<TeacherDetail>>(`/v1/teacher-details/${detailId}`, data);
}

export function deleteTeacherDetail(detailId: string) {
    return request.delete<any, BaseResponse>(`/v1/teacher-details/${detailId}`);
}

export function getUploadDetailUrl(detailId: string, data: { file_name: string }) {
    return request.post<any, UploadDetailUrlResponse>(`/v1/teacher-details/${detailId}/upload-url`, data);
}

export function confirmUploadDetail(detailId: string, data: { storage_path: string, file_name: string }) {
    return request.post<any, DataResponse<TeacherDetail>>(`/v1/teacher-details/${detailId}/confirm-upload`, data);
}
