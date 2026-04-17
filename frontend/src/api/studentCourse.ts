import request from '@/utils/request';
import type { BaseResponse, DataResponse } from './response';

// ─── Types ─────────────────────────────────────────────────────────────────

export interface StudentCourseCreate {
  student_id: string;
  course_id: string;
}

export interface StudentCourseResponse {
  id: string;
  student_id: string;
  course_id: string;
  course_code: string | null;
  course_name: string | null;
  student_name: string | null;
  enrolled_at: string | null;
  created_at: string | null;
}

export interface StudentCourseListResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data: StudentCourseResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface CourseOption {
  id: string;
  course_name: string;
  course_code?: string | null;
}

// ─── API Functions ──────────────────────────────────────────────────────────

/** 取得學生已選課程列表 */
export const getStudentCourses = (student_id: string) => {
  return request.get<any, StudentCourseListResponse>('/v1/student-courses', {
    params: { student_id, per_page: 100 },
  });
};

/** 取得某學生的已選課程（供合約明細 course 下拉用） */
export const getStudentCoursesByStudentId = (student_id: string) => {
  return request.get<any, StudentCourseListResponse>(`/v1/student-courses/by-student/${student_id}`);
};

/** 刪除已選課程 */
export const deleteStudentCourse = (enrollment_id: string) => {
  return request.delete<any, BaseResponse>(`/v1/student-courses/${enrollment_id}`);
};

/** 取得可選課程清單 (下拉選單用) */
export const getCourseOptions = () => {
  return request.get<any, DataResponse<CourseOption[]>>('/v1/student-courses/options/courses');
};

/** 新增學生選課 */
export const createStudentCourse = (data: StudentCourseCreate) => {
  return request.post<any, DataResponse<StudentCourseResponse>>('/v1/student-courses', data);
};
