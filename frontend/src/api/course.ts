import request from '@/utils/request';
import type { BaseResponse } from './response';

export interface CourseListParams {
    page?: number;
    per_page?: number;
    search?: string;
    is_active?: boolean | null;
}

export interface CourseCreate {
    course_code: string;
    course_name: string;
    description?: string | null;
    duration_minutes?: number; // default: 60
    is_active?: boolean;       // default: true
}

export interface CourseUpdate {
    course_code?: string | null;
    course_name?: string | null;
    description?: string | null;
    duration_minutes?: number | null;
    is_active?: boolean | null;
}

export interface CourseResponseData {
    id: string;
    course_code: string;
    course_name: string;
    description?: string | null;
    duration_minutes: number;
    is_active: boolean;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface CourseResponse<T> {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: T;
}

export interface CourseListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: CourseResponseData[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
}

export function getCourseList(params: CourseListParams) {
    return request.get<any, CourseListResponse>('/v1/courses', { params });
}

export function createCourse(data: CourseCreate) {
  return request.post<any, CourseResponse<CourseResponseData>>('/v1/courses', data);
}

export function updateCourse(courseId: string, data: CourseUpdate) {
    return request.put<any, CourseResponse<CourseResponseData>>(`/v1/courses/${courseId}`, data);
}

export function deleteCourse(courseId: string) {
  return request.delete<any, BaseResponse>(`/v1/courses/${courseId}`);
}
