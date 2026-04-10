import request from '@/utils/request';

export interface StudentTeacherPreferenceCreate {
  student_id: string;
  course_id?: string | null;
  min_teacher_level?: number | null;
  primary_teacher_id?: string | null;
}

export interface StudentTeacherPreferenceUpdate {
  course_id?: string | null;
  min_teacher_level?: number | null;
  primary_teacher_id?: string | null;
}

export interface StudentTeacherPreferenceResponse {
  id: string;
  student_id: string;
  course_id: string | null;
  min_teacher_level: number | null;
  primary_teacher_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  student_name: string | null;
  course_name: string | null;
  primary_teacher_name: string | null;
}

export interface PreferenceTeacherOption {
  id: string;
  name: string;
  teacher_no?: string;
}

export interface PreferenceCourseOption {
  id: string;
  course_name: string;
  course_code?: string;
  duration?: number;
}

export const getStudentTeacherPreferences = (student_id: string) => {
  return request.get<any, { data: StudentTeacherPreferenceResponse[] }>('/v1/student-teacher-preferences/', {
    params: { student_id }
  });
};

export const createStudentTeacherPreference = (data: StudentTeacherPreferenceCreate) => {
  return request.post<any, any>('/v1/student-teacher-preferences/', data);
};

export const updateStudentTeacherPreference = (id: string, data: StudentTeacherPreferenceUpdate) => {
  return request.put<any, any>(`/v1/student-teacher-preferences/${id}`, data);
};

export const deleteStudentTeacherPreference = (id: string) => {
  return request.delete<any, any>(`/v1/student-teacher-preferences/${id}`);
};

export const getPreferenceTeacherOptions = () => {
  return request.get<any, { data: PreferenceTeacherOption[] }>('/v1/student-teacher-preferences/options/teachers');
};

export const getPreferenceCourseOptions = (student_id: string) => {
  return request.get<any, { data: PreferenceCourseOption[] }>('/v1/student-teacher-preferences/options/courses', {
    params: { student_id }
  });
};
