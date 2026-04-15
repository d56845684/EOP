import request from '@/utils/request';
import type { BaseResponse } from './response';

export interface LineBindingStatus {
  is_bound: boolean;
  channel_type?: string | null;
  line_display_name?: string | null;
  line_picture_url?: string | null;
  bound_at?: string | null;
  bind_url?: string | null;
}

export interface LineBindingResponse {
  success: boolean;
  message?: string;
  error_code?: string | null;
  data?: LineBindingStatus | null;
}

export const getLineBindUrlApi = (channel?: string) => {
  return request.post<any, LineBindingResponse>('/v1/auth/line/bind', undefined, {
    params: channel ? { channel } : undefined,
  });
};

export const getLineBindingStatusApi = (channel?: string) => {
  return request.get<any, LineBindingResponse>('/v1/auth/line/status', {
    params: channel ? { channel } : undefined,
  });
};

export const unbindLineApi = (channel?: string) => {
  return request.delete<any, BaseResponse>('/v1/auth/line/unbind', {
    params: channel ? { channel } : undefined,
  });
};
