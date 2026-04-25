import request from '@/utils/request';
import type { BaseResponse, DataResponse, ListResponse } from './response';

export interface SubstituteDetailCreate {
  booking_id: string;
  substitute_teacher_id: string;
  substitute_contract_id: string;
  reason?: string | null;
}

export interface SubstituteDetailResponse {
  id: string;
  booking_id: string;
  substitute_teacher_id: string;
  substitute_contract_id: string;
  substitute_hourly_rate?: number | null;
  reason?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  substitute_teacher_name?: string | null;
  booking_no?: string | null;
  original_teacher_name?: string | null;
}

export function createSubstituteDetail(data: SubstituteDetailCreate) {
  return request.post<any, DataResponse<SubstituteDetailResponse>>('/v1/substitute-details', data);
}

export function getSubstituteDetailList(params?: { page?: number; per_page?: number }) {
  return request.get<any, ListResponse<SubstituteDetailResponse>>('/v1/substitute-details', { params });
}

export function deleteSubstituteDetail(substituteDetailId: string) {
  return request.delete<any, BaseResponse>(`/v1/substitute-details/${substituteDetailId}`);
}
