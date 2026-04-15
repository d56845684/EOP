import request from '@/utils/request';
import type { BaseResponse, DataResponse } from './response';

export interface ZoomMeetingLogResponse {
  id: string;
  booking_id: string;
  zoom_account_id?: string | null;
  teacher_id?: string | null;
  zoom_meeting_id: string;
  zoom_meeting_uuid?: string | null;
  join_url: string;
  start_url?: string | null;
  passcode?: string | null;
  meeting_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  meeting_status?: string;
  recording_url?: string | null;
  recording_download_url?: string | null;
  recording_file_type?: string | null;
  recording_file_size_bytes?: number | null;
  recording_duration_seconds?: number | null;
  recording_completed_at?: string | null;
  recording_transfer_status?: string | null;
  drive_file_id?: string | null;
  drive_view_link?: string | null;
  transferred_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  account_name?: string | null;
  teacher_name?: string | null;
}

/** 查詢預約的 Zoom 會議資訊（join_url、passcode 等） */
export function getZoomMeetingByBooking(bookingId: string) {
  return request.get<any, DataResponse<ZoomMeetingLogResponse>>(
    `/v1/zoom/meetings/${bookingId}`
  );
}

/** 手動建立 Zoom 會議 */
export function createZoomMeeting(data: { booking_id: string }) {
  return request.post<any, DataResponse<ZoomMeetingLogResponse>>(
    '/v1/zoom/meetings/create',
    data
  );
}

/** 手動從 Zoom API 取得會議錄影資訊 */
export function fetchZoomRecording(bookingId: string) {
  return request.post<any, DataResponse<ZoomMeetingLogResponse>>(
    `/v1/zoom/meetings/${bookingId}/fetch-recording`
  );
}

/** 取得 Zoom OAuth 授權 URL（教師綁定用） */
export function getZoomOAuthUrl() {
  return request.get<any, { success: boolean; message?: string; error_code?: string | null; authorize_url: string }>('/v1/zoom/oauth/authorize');
}

/** 查詢教師 Zoom 綁定狀態 */
export function getZoomLinkStatus() {
  return request.get<any, { success: boolean; message?: string; error_code?: string | null; linked?: boolean; is_linked?: boolean; account_email?: string | null; zoom_email?: string | null }>(
    '/v1/zoom/oauth/status'
  );
}

/** 解除教師 Zoom 綁定 */
export function unlinkZoom() {
  return request.delete<any, BaseResponse>('/v1/zoom/oauth/unlink');
}

/** 批次查詢多筆預約的 Zoom 會議資訊 */ 
export function batchGetZoomMeetings(bookingIds: string[]) {
  return request.post<any, DataResponse<Record<string, ZoomMeetingLogResponse>>>(
    '/v1/zoom/meetings/batch',
    { booking_ids: bookingIds }
  );
}
